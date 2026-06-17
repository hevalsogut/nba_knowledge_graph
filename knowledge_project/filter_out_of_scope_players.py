"""
filter_out_of_scope_players.py

Project scope decision: this ontology covers NBA teams and NBA roster
players only (the LLM prompt already excludes college/high-school teams
on the playsFor side; this applies the same boundary on the Player side).

A Player individual that was only ever asserted by the LLM extraction
step (a Wikipedia bio mentioning an NBA team) but was NEVER confirmed by
the official nba_api commonteamroster pull in main_pipline.py Step 3 is,
by definition, not on an NBA roster -- typically a two-way/G-League-only
player. These individuals have neither hasHeight nor hasJerseyNumber,
since both are only ever added together when a player IS found on a
roster scan.

This script removes such individuals entirely, rather than leaving them
half-populated and unfixable (no legitimate data source exists for an
out-of-scope individual's height).

Usage:
    python filter_out_of_scope_players.py
"""

from rdflib import Graph, Namespace, RDF

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


def main():
    g = Graph()
    g.bind("nba", NBA)
    g.parse(GRAPH_FILE, format="turtle")
    print(f"[INFO] Loaded {GRAPH_FILE} ({len(g)} triples)")

    out_of_scope = []
    for player in list(g.subjects(RDF.type, NBA.Player)):
        has_height = bool(list(g.objects(player, NBA.hasHeight)))
        has_jersey = bool(list(g.objects(player, NBA.hasJerseyNumber)))
        if not has_height and not has_jersey:
            out_of_scope.append(player)

    print(f"[INFO] Found {len(out_of_scope)} Player individuals never confirmed "
          f"on an official NBA roster (no hasHeight, no hasJerseyNumber):")

    for player in sorted(out_of_scope, key=str):
        local_name = str(player).replace(NBA_URI, "")
        removed = remove_individual(g, player)
        print(f"  [REMOVED] {local_name} ({removed} triples) -- out of scope, "
              f"not an NBA roster player")

    g.serialize(destination=GRAPH_FILE, format="turtle")
    print(f"\n[DONE] Graph re-saved to {GRAPH_FILE} ({len(g)} total triples)")


if __name__ == "__main__":
    main()
