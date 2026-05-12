# NBA Knowledge Graph: A Neurosymbolic Integration Framework

This project presents a structured knowledge engineering solution designed to model the NBA domain through an OWL-based ontology and a hybrid knowledge graph construction pipeline. By combining Large Language Models (LLMs) with structured data from official APIs, the system addresses the challenge of unifying fragmented and unstructured sports data into a reliable, queryable, and explainable knowledge base.

## Project Description

The core objective is to model the professional basketball ecosystem—including players, coaches, teams, conferences, and arenas—as a semantic network. The system employs a neurosymbolic approach to bridge the gap between unstructured natural language biographies and formal ontological structures, significantly reducing LLM-induced hallucinations by grounding information in a validated knowledge graph.

## System Architecture and Methodology

The implementation follows a multi-stage data acquisition and population pipeline:

- **Structural Skeleton Construction:** Establishing the primary TBox hierarchy (Teams, Conferences, and Arenas) using official NBA metadata.
- **LLM-Based Relationship Extraction:** Utilizing the Llama-3-8B-Instruct model to extract triples from unstructured Wikipedia biographies through targeted prompt engineering.
- **API-Driven Data Enrichment:** Validating and updating numerical attributes (e.g., height, jersey numbers) and administrative relationships (e.g., coaching assignments) using official NBA API records to ensure maximum data integrity.

## Ontology Design

The ontology is developed in OWL (Web Ontology Language) and managed via Protégé.

- **TBox (Schema):** Defines classes such as `Player`, `Coach`, `Team`, `Arena`, and `Conference`, along with object properties like `playsFor`, `playPosition`, and `coaches`.
- **ABox (Instances):** Contains individual-level data for over 500 professional players and current head coaches.
- **Data Properties:** Includes precisely typed attributes such as `hasHeight` (`xsd:double`) and `hasJerseyNumber` (`xsd:int`).

## Competency Questions

The knowledge graph is designed to resolve specific competency questions through SPARQL queries:

1. Determine the current professional team and position of a specific player.
2. Identify the head coach responsible for a specific organization.
3. Retrieve aggregated statistics, such as the average height of players within the Western Conference.
4. Locate the home arena of a team and verify its seating capacity.

## Technical Implementation

| Component | Technology |
|---|---|
| Modeling | Protégé |
| Programming Framework | RDFlib (Python) |
| Data Sources | Wikipedia (unstructured text) and `nba_api` (structured JSON) |
| LLM Integration | Meta-Llama-3-8B via Hugging Face Inference endpoints |
| Validation | Automated SHACL constraints |

## Documentation and Deployment

The ontology documentation is generated using Widoco, providing a comprehensive, human-readable overview of the extended ontology version. The full graph is available for deployment in RDF-compliant triple stores like GraphDB.

## References

All methodologies and technical decisions are grounded in academic knowledge engineering principles and semantic technology standards as specified in the course curriculum.
