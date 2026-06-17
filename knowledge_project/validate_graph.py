"""
validate_graph.py

Runs SHACL validation (pyshacl) against the unified NBA Knowledge Graph
and prints a professional, human-readable compliance report. This is
the script the original project claimed to run but never committed --
it now actually exists and is reproducible.

Usage:
    python validate_graph.py
"""

import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from rdflib import Graph
from rdflib.namespace import Namespace
from pyshacl import validate

DATA_GRAPH_FILE = "NBA_Knowledge_Graph_Complete.ttl"
SHAPES_FILE = "shapes.ttl"
REPORT_FILE = "shacl_validation_report.txt"

SH = Namespace("http://www.w3.org/ns/shacl#")


def main():
    print("=" * 70)
    print(" NBA KNOWLEDGE GRAPH - SHACL COMPLIANCE VALIDATION")
    print("=" * 70)

    data_graph = Graph()
    try:
        data_graph.parse(DATA_GRAPH_FILE, format="turtle")
    except Exception as e:
        print(f"[FATAL] Could not load data graph '{DATA_GRAPH_FILE}': {e}")
        sys.exit(1)

    shapes_graph = Graph()
    try:
        shapes_graph.parse(SHAPES_FILE, format="turtle")
    except Exception as e:
        print(f"[FATAL] Could not load shapes file '{SHAPES_FILE}': {e}")
        sys.exit(1)

    print(f"[INFO] Data graph:   {DATA_GRAPH_FILE}  ({len(data_graph)} triples)")
    print(f"[INFO] Shapes graph: {SHAPES_FILE}  ({len(shapes_graph)} triples)")
    print("-" * 70)
    print("[INFO] Running validation...\n")

    conforms, results_graph, results_text = validate(
        data_graph,
        shacl_graph=shapes_graph,
        data_graph_format="turtle",
        shacl_graph_format="turtle",
        inference="rdfs",      # picks up rdfs:subClassOf (Guard/Forward/Center -> Player, etc.)
        abort_on_first=False,
        allow_infos=True,
        allow_warnings=True,
        meta_shacl=False,
        advanced=True,
        debug=False,
    )

    violations, warnings, infos = [], [], []
    for result in results_graph.subjects(SH.resultSeverity, None):
        severity = results_graph.value(result, SH.resultSeverity)
        message = results_graph.value(result, SH.resultMessage)
        focus = results_graph.value(result, SH.focusNode)
        path = results_graph.value(result, SH.resultPath)

        entry = f"  - [{focus}] path={path} :: {message}"
        if severity == SH.Violation:
            violations.append(entry)
        elif severity == SH.Warning:
            warnings.append(entry)
        else:
            infos.append(entry)

    print(f"CONFORMS: {conforms}\n")
    print(f"Violations : {len(violations)}")
    print(f"Warnings   : {len(warnings)}")
    print(f"Infos      : {len(infos)}")
    print("-" * 70)

    if violations:
        print("\nVIOLATIONS (must fix before submission):")
        for v in violations:
            print(v)

    if warnings:
        print("\nWARNINGS (data completeness, non-blocking):")
        for w in warnings[:25]:
            print(w)
        if len(warnings) > 25:
            print(f"  ... and {len(warnings) - 25} more (see {REPORT_FILE})")

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(f"CONFORMS: {conforms}\n\n")
        f.write(results_text)

    print("\n" + "=" * 70)
    print(f"[DONE] Full report written to {REPORT_FILE}")
    print("=" * 70)

    sys.exit(0 if conforms else 1)


if __name__ == "__main__":
    main()
