"""
reenrich_missing_heights.py

Targeted fix for the last 41 SHACL hasHeight violations. Instead of
re-running the entire main_pipline.py (which would mean re-calling the
LLM for 500+ bios and re-pulling every team roster again), this script:

  1. Queries NBA_Knowledge_Graph_Complete.ttl directly for every
     nba:Player individual that has zero nba:hasHeight triples
     (the actual SHACL-violating set, derived from the graph itself
     rather than copy-pasted from console output, so it stays correct
     even if the graph changes).
  2. Looks each one up individually via nba_api's player search +
     CommonPlayerInfo endpoint (lighter than re-scanning all 30 team
     rosters for 41 names).
  3. Converts the returned HEIGHT field (e.g. "6-9") to meters using
     the same convert_height() logic as main_pipline.py, and adds
     exactly one hasHeight triple per resolved player.
  4. Leaves a clear, honest list of any names that could not be
     resolved (e.g. malformed individuals like 'StephanCurry' --
     a duplicate/typo of Stephen_Curry from old test data -- or
     'AJ_Johnson', the player with the known empty-playsFor bug)
     instead of silently claiming success. These need a manual look,
     not an automated guess-merge.

Usage:
    python reenrich_missing_heights.py
"""

import re
import sys
import time

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from rdflib import Graph, Namespace, Literal, RDF, XSD

from nba_api.stats.static import players as static_players
from nba_api.stats.endpoints import commonplayerinfo

NBA_URI = "http://www.semanticweb.org/veliu/ontologies/2026/3/untitled-ontology-10/"
NBA = Namespace(NBA_URI)

GRAPH_FILE = "NBA_Knowledge_Graph_Complete.ttl"


def convert_height(raw):
    """Same logic as main_pipline.py: '6-9' -> meters."""
    try:
        nums = re.findall(r"\d+", str(raw))
        if len(nums) >= 2:
            total_inches = (int(nums[0]) * 12) + int(nums[1])
            return round(total_inches * 0.0254, 2)
        return None
    except Exception:
        return None


def find_missing_height_players(g):
    missing = []
    for player in g.subjects(RDF.type, NBA.Player):
        if not list(g.objects(player, NBA.hasHeight)):
            missing.append(player)
    return sorted(missing, key=str)


def resolve_player_id(search_name):
    """Looks up a player by name via nba_api's static player list.
    Returns the player_id on an exact (case-insensitive) full-name
    match, or None if no confident match is found."""
    matches = static_players.find_players_by_full_name(search_name)
    if not matches:
        return None
    for m in matches:
        if m["full_name"].lower() == search_name.lower():
            return m["id"]
    # No exact match -- don't guess on an ambiguous/partial match.
    return None


def main():
    g = Graph()
    g.bind("nba", NBA)
    g.parse(GRAPH_FILE, format="turtle")
    print(f"[INFO] Loaded {GRAPH_FILE} ({len(g)} triples)")

    missing = find_missing_height_players(g)
    print(f"[INFO] Found {len(missing)} Player individuals with no hasHeight\n")

    resolved, unresolved = 0, []

    for player_uri in missing:
        local_name = str(player_uri).replace(NBA_URI, "")
        search_name = local_name.replace("_", " ")

        player_id = resolve_player_id(search_name)
        if player_id is None:
            print(f"  [SKIP] {local_name}: no exact nba_api match for '{search_name}'")
            unresolved.append(local_name)
            continue

        try:
            info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
            df = info.get_data_frames()[0]
            raw_height = df.iloc[0]["HEIGHT"]
            h_meters = convert_height(raw_height)

            if h_meters is None:
                print(f"  [SKIP] {local_name}: nba_api returned no usable HEIGHT value")
                unresolved.append(local_name)
            else:
                g.add((player_uri, NBA.hasHeight, Literal(h_meters, datatype=XSD.double)))
                print(f"  [ADDED] {local_name}: {h_meters}m")
                resolved += 1

        except Exception as e:
            print(f"  [ERROR] {local_name}: nba_api lookup failed ({e})")
            unresolved.append(local_name)

        time.sleep(0.6)  # API courtesy throttle

    g.serialize(destination=GRAPH_FILE, format="turtle")

    print("\n" + "=" * 70)
    print(f"[DONE] {resolved}/{len(missing)} players enriched with hasHeight.")
    print(f"Graph re-saved to {GRAPH_FILE} ({len(g)} total triples)")

    if unresolved:
        print(f"\n[REVIEW NEEDED] {len(unresolved)} players could NOT be resolved "
              f"automatically -- these will still show as SHACL violations and "
              f"need a manual look (likely retired/free agent, name mismatch, "
              f"or a malformed individual from earlier test data):")
        for name in unresolved:
            print(f"   - {name}")
    print("=" * 70)


if __name__ == "__main__":
    main()
