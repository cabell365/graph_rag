# Validation record

Validated locally on macOS with Python 3.13.13, Neo4j Community 5.26.31, Streamlit 1.64.0, and the installed Ollama `mistral:latest` and `nomic-embed-text:latest` models.

## Source and import checks

- Scanned 44 supplied files; verified all 29 business-document manifest hashes.
- Verified 29 supplied chunk texts against originals, 84 fixture entity identities, 229 relationship endpoints, and matching CSV/JSON row counts.
- Parsed the full backup; validated natural-key uniqueness and representative/team/month/year references.
- Loaded 33 document sources into 41 Nomic-embedded passages.
- Loaded 24,000 representatives, 6,000 teams, 84 periods, and 2,016,000 monthly metrics into Neo4j. The finance completion marker is `complete`.
- Full metric count and rep/team counts reconcile with the source.

## Executed checks

- Six unit tests passed: SQL escaping, duplicate-key rejection, missing-reference rejection, finance-scope parsing, chunk coverage, and graph identifier validation.
- `python -m graphrag.verify` passed six source-versus-graph financial reconciliations: three representative periods, two team/year totals, and one full-network/year total; retrieval and historical date-filter checks also passed.
- Streamlit was started on port 8981 and inspected in the browser. Sidebar connectivity, chat input, streaming answers, evidence controls, and the finance workspace were exercised.
- The live 2023 network calculation matched independent staging: actual $15,859,255,561, target $15,841,627,454, 288,000 monthly source rows, 100.11% attainment.
- Both HTML guides parse successfully. Each has 12 sections, six tables, three accessible SVG diagrams, a glossary and vendor references. All internal navigation anchors resolve. Standalone browser visual inspection was blocked by the browser's local-file URL policy; their HTML structure was checked, and the Streamlit interface was visually inspected.
- Python source compilation passed. Tested dependency versions are recorded in `requirements-tested.txt`; portable version ranges remain in `requirements.txt`.
- Final focused checks confirmed MANAGES, MEMBER_OF, LOCATED_IN and the incident/product/customer/representative path. The five-question sample report includes the latest ownership and outreach answers; expected source recall is 100%, 100%, 100%, 50% and 100%, respectively, with no citation IDs outside retrieved sources. These are retrieval/citation checks, not proof of complete semantic correctness.

## Answer quality and limits

The supplied questions were used only for evaluation. Five questions were evaluated end to end, then role and outreach questions were checked again after targeted improvements. Reports retain generated text, expected answers, retrieved/cited sources, and citation diagnostics. An early answer confused a procurement contact with an account owner; graph-first context and explicit role summaries address that failure. A two-hop expansion initially missed the full incident-to-owner outreach chain; the final retriever includes a bounded, typed three-hop path for those questions.

Do not interpret source recall as a correctness score. A response can cite a retrieved source while misreading its contents. Mistral still needs human review for policy timing, relationship wording, and unsupported causal conclusions. The evidence desk deliberately exposes the passages and query provenance needed for that review. The complete supplied evaluation suite has not been run; no production answer-accuracy claim is made.

Native macOS execution was tested. Windows/Linux setup commands and the portable Compose configuration are documented, but those operating systems and the all-container app/Ollama mode were not executed in this session. DOCX text/tables and every workbook sheet were extracted; workbook formulas were not recalculated. The embedded Word schema diagram was reviewed manually. See `source-assessment.md` for source distinctions.

Application and Neo4j services are left running locally. The original source directory remains unchanged.
