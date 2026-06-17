"""
fix_duplicate_entities.py

Resolves two leftover entity-duplication bugs from old hand-written test
data that got merged into Knowledge_Project_Skeleton.ttl:

  1. nba:LebronJames -- a bare duplicate of the already-complete
     nba:LeBron_James (which has hasHeight/hasJerseyNumber/playsFor).
     Carries no information LeBron_James doesn't already have, so it's
     deleted outright rather than merged.

  2. nba:StephanCurry -- NOT a duplicate (nba:Stephen_Curry does not
     exist anywhere in the graph), so it can't be deleted without
     silently erasing Stephen Curry from the knowledge graph entirely.
     Instead it is renamed to the canonical nba:Stephen_Curry URI, and
     its nba:playsFor target is repointed from the non-canonical
     nba:GoldenState individual to the real nba:Golden_State_Warriors
     (the one declared in the skeleton with belongsTo/hasHomeArena).

  3. nba:GoldenState / nba:ChaseCenter -- once nothing else points at
     them, these become orphaned duplicates of
     nba:Golden_State_Warriors / its real arena and are removed.

Run this BEFORE reenrich_missing_heights.py picks up Stephen_Curry's
height, since 'StephanCurry' (no underscore) won't match an nba_api
full-name search.

Usage:
    python fix_duplicate_entities.py
"""

from rdflib import Graph, Namespace, URIRef, RDF

NBA_URI = "http://www.semanticweb.org/veliu/ontologies/2026/3/untitled-ontology-10/"
NBA = Namespace(NBA_URI)

GRAPH_FILE = "NBA_Knowledge_Graph_Complete.ttl"


def remove_individual(g, uri):
    removed = 0
    for s, p, o in list(g.triples((uri, None, None))):
        g.remove((s, p, o))
        removed += 1
    for s, p, o in list(g.triples((None, None, uri))):
        g.remove((s, p, o))
        removed += 1
    return removed


def rename_individual(g, old_uri, new_uri):
    moved = 0
    for s, p, o in list(g.triples((old_uri, None, None))):
        g.remove((s, p, o))
        g.add((new_uri, p, o))
        moved += 1
    for s, p, o in list(g.triples((None, None, old_uri))):
        g.remove((s, p, o))
        g.add((s, p, new_uri))
        moved += 1
    return moved


def main():
    g = Graph()
    g.bind("nba", NBA)
    g.parse(GRAPH_FILE, format="turtle")
    print(f"[INFO] Loaded {GRAPH_FILE} ({len(g)} triples)")

    # 1. Delete the pure duplicate LebronJames
    removed = remove_individual(g, NBA.LebronJames)
    print(f"[FIX] Removed {removed} triples for duplicate individual 'LebronJames' "
          f"(LeBron_James already has complete data)")

    # 2. Rename StephanCurry -> Stephen_Curry
    moved = rename_individual(g, NBA.StephanCurry, NBA.Stephen_Curry)
    print(f"[FIX] Renamed 'StephanCurry' -> 'Stephen_Curry' ({moved} triples moved)")

    # Repoint playsFor from the non-canonical GoldenState to the real team
    if (NBA.Stephen_Curry, NBA.playsFor, NBA.GoldenState) in g:
        g.remove((NBA.Stephen_Curry, NBA.playsFor, NBA.GoldenState))
        g.add((NBA.Stephen_Curry, NBA.playsFor, NBA.Golden_State_Warriors))
        print("[FIX] Repointed Stephen_Curry's playsFor: GoldenState -> Golden_State_Warriors")

    # 3. Remove the now-orphaned duplicate Team/Arena individuals
    for orphan in (NBA.GoldenState, NBA.ChaseCenter):
        if list(g.triples((orphan, None, None))) or list(g.triples((None, None, orphan))):
            removed = remove_individual(g, orphan)
            local = str(orphan).replace(NBA_URI, "")
            print(f"[FIX] Removed {removed} triples for orphaned duplicate '{local}'")

    g.serialize(destination=GRAPH_FILE, format="turtle")
    print(f"\n[DONE] Graph re-saved to {GRAPH_FILE} ({len(g)} total triples)")


if __name__ == "__main__":
    main()
