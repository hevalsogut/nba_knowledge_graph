"""
merge_and_clean_pipeline.py

Unifies the fragmented NBA Knowledge Graph TTL exports into a single,
deduplicated, typo-corrected graph: NBA_Knowledge_Graph_Complete.ttl

Fixes applied (see audit report for the bugs each one addresses):
  1. Merges NBA_Knowledge_Graph_Final.ttl (Player + LLM/API enrichment)
     and NBA_Ontology_Final_V5.ttl (Team/Coach/Arena/Conference) into
     one graph -- these were never actually combined before.
  2. Renames the predicate typo 'playsPosition' -> 'playPosition'.
  3. Renames the class typo 'EasternConferance'/'WesternConferance'
     -> 'EasternConference'/'WesternConference'.
  4. Purges dangling/empty object URIs (e.g. ':playsFor :').
  5. Deduplicates 'playsFor' so each Player has exactly ONE current
     team, sourced authoritatively from a fresh nba_api roster pull
     (matching the project's own stated design: API data should
     overwrite/override LLM-extracted data, which the original
     pipeline described but never actually implemented).

Run this AFTER your skeleton, wiki.py (LLM extraction), and
v4_ttl.py / v5_ttl.py (API enrichment) stages have produced their
TTL outputs in the current directory.

Usage:
    python merge_and_clean_pipeline.py
"""

import sys
import time

from rdflib import Graph, Namespace, URIRef, RDF, OWL, XSD

try:
    from nba_api.stats.static import teams
    from nba_api.stats.endpoints import commonteamroster
    NBA_API_AVAILABLE = True
except ImportError:
    NBA_API_AVAILABLE = False

NBA_URI = "http://www.semanticweb.org/veliu/ontologies/2026/3/untitled-ontology-10/"
NBA = Namespace(NBA_URI)

# Fragmented source files to merge. Missing files are skipped with a
# warning rather than aborting the whole run.
SOURCE_FILES = [
    "NBA_Knowledge_Graph_Final.ttl",   # Players: playsFor / hasHeight / hasJerseyNumber / playPosition
    "NBA_Ontology_Final_V5.ttl",       # Teams / Coaches / Arenas / Conferences
]

OUTPUT_FILE = "NBA_Knowledge_Graph_Complete.ttl"


# ---------------------------------------------------------------------------
# Step 1: Load and merge all fragments into one graph
# ---------------------------------------------------------------------------
def load_and_merge(paths):
    g = Graph()
    g.bind("nba", NBA)
    g.bind("owl", OWL)
    g.bind("xsd", XSD)

    loaded_any = False
    for path in paths:
        try:
            g.parse(path, format="turtle")
            loaded_any = True
            print(f"[OK]   Loaded {path} -> graph now has {len(g)} triples")
        except FileNotFoundError:
            print(f"[WARN] {path} not found, skipping.")
        except Exception as e:
            print(f"[WARN] Could not parse {path}: {e}")

    if not loaded_any:
        print("[FATAL] No source files could be loaded. Aborting.")
        sys.exit(1)

    return g


# ---------------------------------------------------------------------------
# Step 2: Fix the playsPosition -> playPosition predicate typo
# ---------------------------------------------------------------------------
def fix_predicate_typo(g):
    bad_pred = NBA.playsPosition
    good_pred = NBA.playPosition

    fixed = 0
    for s, p, o in list(g.triples((None, bad_pred, None))):
        g.remove((s, p, o))
        g.add((s, good_pred, o))
        fixed += 1

    print(f"[FIX]  Renamed {fixed} 'playsPosition' triples -> 'playPosition'")
    return g


# ---------------------------------------------------------------------------
# Step 3: Fix EasternConferance / WesternConferance class typo
# ---------------------------------------------------------------------------
def fix_class_typo(g):
    typo_map = {
        NBA.EasternConferance: NBA.EasternConference,
        NBA.WesternConferance: NBA.WesternConference,
    }

    fixed = 0
    for bad_cls, good_cls in typo_map.items():
        # rdf:type assertions pointing at the typo'd class
        for s, p, o in list(g.triples((None, RDF.type, bad_cls))):
            g.remove((s, p, o))
            g.add((s, RDF.type, good_cls))
            fixed += 1
        # any other triples where the typo'd class is subject or object
        for s, p, o in list(g.triples((bad_cls, None, None))):
            g.remove((s, p, o))
            g.add((good_cls, p, o))
        for s, p, o in list(g.triples((None, None, bad_cls))):
            if p != RDF.type:
                g.remove((s, p, o))
                g.add((s, p, good_cls))

    print(f"[FIX]  Corrected {fixed} 'Conferance' -> 'Conference' typo assertions")
    return g


# ---------------------------------------------------------------------------
# Step 4: Purge dangling / empty object URIs (e.g. ':playsFor :')
# ---------------------------------------------------------------------------
def purge_empty_uris(g):
    empty_node = URIRef(NBA_URI)
    empty_node_no_slash = URIRef(NBA_URI.rstrip("/"))

    purged = 0
    for s, p, o in list(g):
        if isinstance(o, URIRef) and o in (empty_node, empty_node_no_slash):
            g.remove((s, p, o))
            purged += 1
        elif isinstance(o, URIRef) and str(o).startswith(NBA_URI):
            local_name = str(o)[len(NBA_URI):]
            if local_name.strip() == "":
                g.remove((s, p, o))
                purged += 1

    print(f"[FIX]  Purged {purged} dangling/empty object-URI triples")
    return g


# ---------------------------------------------------------------------------
# Step 5: Deduplicate playsFor -- exactly one CURRENT team per player
#
# Re-queries the official nba_api roster (the same authoritative source
# the original v4/v5 enrichment scripts used) to determine each player's
# single current team. Existing playsFor triples are removed and replaced
# with the authoritative one. Players not found on a current roster
# (retired / free agent / G-League-only in the text corpus) keep their
# single existing triple if unambiguous; if multiple exist with no
# authoritative source, the first (sorted) is kept and the rest dropped,
# with a console note so a human can review the list.
# ---------------------------------------------------------------------------
def build_current_roster_map():
    """Returns dict: player_local_name -> team_local_name"""
    mapping = {}
    all_teams = teams.get_teams()
    print(f"[INFO] Querying {len(all_teams)} team rosters from nba_api for current playsFor...")

    for team in all_teams:
        team_local = team["full_name"].replace(" ", "_")
        try:
            roster = commonteamroster.CommonTeamRoster(team_id=team["id"])
            df = roster.get_data_frames()[0]
            for _, row in df.iterrows():
                player_local = row["PLAYER"].replace(" ", "_")
                mapping[player_local] = team_local
        except Exception as e:
            print(f"[WARN] Could not fetch roster for {team['full_name']}: {e}")
        time.sleep(0.5)  # API courtesy throttle

    print(f"[INFO] Built authoritative current-team map for {len(mapping)} players")
    return mapping


def dedupe_plays_for(g, roster_map):
    overwritten, kept_single, dropped_ambiguous = 0, 0, 0

    players = set(g.subjects(RDF.type, NBA.Player))
    for player in players:
        existing = list(g.objects(player, NBA.playsFor))
        for o in existing:
            g.remove((player, NBA.playsFor, o))

        player_local = str(player).replace(NBA_URI, "")

        if player_local in roster_map:
            team_uri = NBA[roster_map[player_local]]
            g.add((player, NBA.playsFor, team_uri))
            g.add((team_uri, RDF.type, NBA.Team))
            overwritten += 1
        elif len(existing) == 1:
            g.add((player, NBA.playsFor, existing[0]))
            kept_single += 1
        elif len(existing) > 1:
            chosen = sorted(existing, key=str)[0]
            g.add((player, NBA.playsFor, chosen))
            dropped_ambiguous += 1
            print(f"  [REVIEW] {player_local}: no current roster match, "
                  f"{len(existing)} historical teams found, kept {chosen}")

    print(f"[FIX]  playsFor dedup: {overwritten} set from live roster, "
          f"{kept_single} unambiguous kept as-is, "
          f"{dropped_ambiguous} ambiguous historical sets resolved by fallback")
    return g


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    g = load_and_merge(SOURCE_FILES)

    g = fix_predicate_typo(g)
    g = fix_class_typo(g)
    g = purge_empty_uris(g)

    if NBA_API_AVAILABLE:
        try:
            roster_map = build_current_roster_map()
        except Exception as e:
            print(f"[WARN] nba_api call failed ({e}); falling back to "
                  f"existing-triple-only deduplication.")
            roster_map = {}
    else:
        print("[WARN] nba_api not installed; falling back to "
              "existing-triple-only deduplication. Install nba_api for "
              "authoritative current-team resolution.")
        roster_map = {}

    g = dedupe_plays_for(g, roster_map)

    g.serialize(destination=OUTPUT_FILE, format="turtle")
    print(f"\n[DONE] Unified graph written to {OUTPUT_FILE} ({len(g)} total triples)")


if __name__ == "__main__":
    main()
