"""
clean_existing_graph.py

One-off patch for the already-generated NBA_Knowledge_Graph_Complete.ttl,
so you don't have to re-run main_pipline.py (which would mean re-calling
the LLM for 500+ bios and re-pulling nba_api rosters) just to apply the
ontology fixes.

Fixes applied:
  1. Removes the stray 'owl:topObjectProperty rdfs:domain nba:Player ;
     rdfs:range nba:Team' declaration -- this was causing every Team and
     Coach individual to be RDFS-inferred as nba:Player (since every real
     object property is rdfs:subPropertyOf owl:topObjectProperty).
  2. Removes 'nba:playerName rdfs:domain nba:Player' -- same misclassification
     bug, independent cause, since playerName is reused as a generic label
     for Teams and Coaches too.
  3. Renames EasternConferance/WesternConferance -> EasternConference/
     WesternConference (class declarations and individual type assertions).
  4. Purges dangling/empty object URIs (e.g. ':playsFor :').
  5. Deduplicates playsFor and playPosition so each Player has at most one
     of each (matches shapes.ttl's maxCount 1 constraints). Since this
     script doesn't call nba_api, it keeps the alphabetically-first value
     and logs the rest for manual review rather than guessing which is
     "current".

Usage:
    python clean_existing_graph.py
"""

import re

from rdflib import Graph, Namespace, URIRef, RDF, OWL

NBA_URI = "http://www.semanticweb.org/veliu/ontologies/2026/3/untitled-ontology-10/"
NBA = Namespace(NBA_URI)

VALID_POSITIONS = {"Guard", "Forward", "Center"}


def normalize_position(raw_local_name):
    """Maps a (possibly garbage) playPosition local name like
    'Small_forward/Shooting_guard' or 'center' to exactly one of
    Guard/Forward/Center, taking the first recognized position word
    in reading order. Returns None if nothing recognizable is found."""
    tokens = re.split(r"[\s/\-_,&]+", raw_local_name.lower())
    for token in tokens:
        if "guard" in token:
            return "Guard"
        if "forward" in token:
            return "Forward"
        if "center" in token:
            return "Center"
    return None

INPUT_FILE = "NBA_Knowledge_Graph_Complete.ttl"
OUTPUT_FILE = "NBA_Knowledge_Graph_Complete.ttl"  # overwrite in place


def remove_top_object_property_restriction(g):
    top = OWL.topObjectProperty
    removed = 0
    for s, p, o in list(g.triples((top, None, None))):
        g.remove((s, p, o))
        removed += 1
    print(f"[FIX] Removed {removed} stray owl:topObjectProperty domain/range triples")
    return g


def remove_playername_domain_restriction(g):
    from rdflib.namespace import RDFS
    removed = 0
    for s, p, o in list(g.triples((NBA.playerName, RDFS.domain, None))):
        g.remove((s, p, o))
        removed += 1
    print(f"[FIX] Removed {removed} nba:playerName rdfs:domain restriction(s)")
    return g


def fix_class_typo(g):
    typo_map = {
        NBA.EasternConferance: NBA.EasternConference,
        NBA.WesternConferance: NBA.WesternConference,
    }
    fixed = 0
    for bad_cls, good_cls in typo_map.items():
        for s, p, o in list(g.triples((None, RDF.type, bad_cls))):
            g.remove((s, p, o))
            g.add((s, RDF.type, good_cls))
            fixed += 1
        for s, p, o in list(g.triples((bad_cls, None, None))):
            g.remove((s, p, o))
            g.add((good_cls, p, o))
        for s, p, o in list(g.triples((None, None, bad_cls))):
            if p != RDF.type:
                g.remove((s, p, o))
                g.add((s, p, good_cls))
    print(f"[FIX] Corrected {fixed} 'Conferance' -> 'Conference' typo assertions")
    return g


def purge_empty_uris(g):
    empty_node = URIRef(NBA_URI)
    empty_node_no_slash = URIRef(NBA_URI.rstrip("/"))
    purged = 0
    for s, p, o in list(g):
        if isinstance(o, URIRef) and o in (empty_node, empty_node_no_slash):
            g.remove((s, p, o))
            purged += 1
        elif isinstance(o, URIRef) and str(o).startswith(NBA_URI):
            if str(o)[len(NBA_URI):].strip() == "":
                g.remove((s, p, o))
                purged += 1
    print(f"[FIX] Purged {purged} dangling/empty object-URI triples")
    return g


def normalize_play_positions(g):
    fixed, dropped = 0, 0
    for s, p, o in list(g.triples((None, NBA.playPosition, None))):
        local_name = str(o).replace(NBA_URI, "")
        if local_name in VALID_POSITIONS:
            continue
        g.remove((s, p, o))
        normalized = normalize_position(local_name)
        if normalized is not None:
            g.add((s, p, NBA[normalized]))
            fixed += 1
        else:
            dropped += 1
    print(f"[FIX] playPosition normalization: {fixed} garbage values mapped to "
          f"Guard/Forward/Center, {dropped} unrecognizable values dropped")
    return g


def dedupe_single_valued(g, predicate, label):
    kept, dropped = 0, 0
    players = set(g.subjects(RDF.type, NBA.Player))
    for player in players:
        values = list(g.objects(player, predicate))
        if len(values) <= 1:
            continue
        chosen = sorted(values, key=str)[0]
        for v in values:
            g.remove((player, predicate, v))
        g.add((player, predicate, chosen))
        kept += 1
        dropped += len(values) - 1
        player_local = str(player).replace(NBA_URI, "")
        print(f"  [REVIEW] {player_local}: {len(values)} {label} values found, "
              f"kept {chosen}, dropped {len(values) - 1}")
    print(f"[FIX] {label} dedup: {kept} players reduced to a single value "
          f"({dropped} duplicate triples removed)")
    return g


def main():
    g = Graph()
    g.bind("nba", NBA)
    g.parse(INPUT_FILE, format="turtle")
    print(f"[INFO] Loaded {INPUT_FILE} ({len(g)} triples)")

    g = remove_top_object_property_restriction(g)
    g = remove_playername_domain_restriction(g)
    g = fix_class_typo(g)
    g = purge_empty_uris(g)
    g = normalize_play_positions(g)
    g = dedupe_single_valued(g, NBA.playsFor, "playsFor")
    g = dedupe_single_valued(g, NBA.playPosition, "playPosition")

    g.serialize(destination=OUTPUT_FILE, format="turtle")
    print(f"\n[DONE] Cleaned graph written to {OUTPUT_FILE} ({len(g)} total triples)")


if __name__ == "__main__":
    main()
