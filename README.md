# Canyon Office · Knowledge Commons

A Python Streamlit Graph RAG on **http://localhost:8981**, backed by Neo4j and local Ollama. Uses **mistral:latest** for answers and **nomic-embed-text:latest** for embeddings. Dark university styling with `#275D38`.

## What's included

- Citation-rich streaming chat, a relationship map, source library, exact finance explorer, conversation export and an offline learning room.
- 29 business Markdown sources plus workbook, implementation document, planning notes and corpus overview. Fixture graph JSON supplies explicit business relationships. Evaluation answers are never embedded.
- Full finance import: 24,000 reps, 6,000 teams, 84 periods and 2,016,000 monthly metric nodes. Each metric links to its representative and period. The SQL backup is parsed as data; it is never executed against a database. MySQL is not required.
- [System design](docs/design.html) and [Neo4j 101](docs/neo4j-101.html): self-contained HTML with diagrams, tables and glossaries; open either file in a browser or use the chatbot's Learning room.
- Source hashes and file inventory in `reports/source-scan.json`. Original source files remain in the supplied Documents directory; working copies are under `data/`.

## Prerequisites

Python 3.11–3.13, Docker Desktop on macOS/Windows or Docker Engine + Compose on Linux, and Ollama. Allocate at least 8 GB to Docker for the full graph; allow additional memory for Mistral (16 GB system RAM recommended, 24+ GB more comfortable). The full graph and model downloads require several GB of disk. The finance import can take many minutes, depending on hardware; progress is printed every 100,000 records.

This local teaching application binds Docker ports to loopback. It has no multi-user authentication. Add authentication, authorization, TLS and a dedicated read-only Neo4j identity before exposing it on a network.

## Recommended: native Ollama + Docker Neo4j + native Python

This uses GPU acceleration available through the native Ollama installation on macOS and Windows and reuses models already installed. Start Docker and Ollama first.

### macOS and Linux

In the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and replace `NEO4J_PASSWORD` with a long local password. Never commit `.env`.

```bash
docker compose up -d neo4j
ollama pull mistral:latest
ollama pull nomic-embed-text:latest
python -m graphrag.ingest --scan-only
python -m graphrag.ingest
python -m streamlit run app.py --server.port 8981
```

If Ollama isn't serving yet on Linux, start `ollama serve` in another terminal or enable its installed system service. Docker must be running. On Linux your user must have appropriate Docker access; follow Docker's installation instructions rather than changing socket permissions.

### Windows (PowerShell)

Use Linux containers in Docker Desktop (WSL2 backend recommended). Install Python and Ollama, then in the project directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` to set a long `NEO4J_PASSWORD`, then:

```powershell
docker compose up -d neo4j
ollama pull mistral:latest
ollama pull nomic-embed-text:latest
.\.venv\Scripts\python.exe -m graphrag.ingest --scan-only
.\.venv\Scripts\python.exe -m graphrag.ingest
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8981
```

These commands don't require PowerShell activation or an execution-policy change.

Open **http://localhost:8981** for the chatbot and **http://localhost:7474** for Neo4j Browser. Sign in as `neo4j` with the password in `.env`. Never publish that password in screenshots or support logs.

## Alternative: all services in Docker

Stop native Ollama first, or change the host port mapping to avoid a conflict on 11434. Set `.env` as above; keep its host URL defaults, since Compose overrides internal service URLs.

```bash
docker compose up -d --build
docker compose exec ollama ollama pull mistral:latest
docker compose exec ollama ollama pull nomic-embed-text:latest
docker compose exec app python -m graphrag.ingest --scan-only
docker compose exec app python -m graphrag.ingest
```

Then open http://localhost:8981. The app image uses Python 3.12. Containerized Ollama defaults to CPU; GPU configuration depends on the host and is not enabled in this portable Compose file. Prefer native Ollama on Apple Silicon. The app can start before ingestion; its sidebar shows graph counts and missing models.

## Pilot, resume, and verification

For a quick document-only pilot:

```bash
python -m graphrag.ingest --documents-only
```

This deliberately disables exact finance totals until the full import is complete. To add finance later:

```bash
python -m graphrag.ingest --finance-only
```

Imports use stable IDs and MERGE, so rerunning the **same** source retains logical identities. Documents with unchanged hashes/models skip embedding. Finance reruns revalidate and upsert the full backup; this takes time. A completion marker gates finance answers, so interrupted imports cannot yield partial totals. Changed or removed source sets require a fresh dedicated database/volume to avoid stale entities; automatic deletion of unrelated data is not performed. Changing the embedding model requires recreating its vector index and re-embedding in a fresh database. Use this project with its dedicated Compose volume, not an existing production database.

```bash
python -m unittest discover -s tests -v
python -m graphrag.verify
python -m graphrag.evaluate --limit 10
```

`verify` reconciles counts and sampled totals against the independently staged source and checks retrieval. `evaluate` writes answers, sources, citation coverage and expected answers to `reports/evaluation-results.jsonl` for human review; source overlap alone is not an answer-quality score. Evaluation may take several minutes on CPU. See `reports/validation.md` for what was actually run in this workspace.

## Asking useful questions

- “Who manages Aspen Grove and which team and territory are involved?”
- “What pricing applies to CUS-001 for PRD-101 on 2023-06-01?” Set the event date in the sidebar for date-filtered retrieval.
- “Which customers might need outreach about the January 2018 A4 delay?”
- “What were actual and target sales for REP-100001 in January 2018?”
- “What were total sales for team 1 in 2023?”

The chat finance tool intentionally accepts only explicit one-year totals, optionally one month and one representative or team ID. Use Finance explorer for precise filters. It rejects unsupported comparisons, rankings, customer/product allocations and arbitrary ranges. Company-wide sales means the full dump network, not an invented product allocation. Team attribution uses the dump-current membership.

Documents cover historical 2018–2024 scenario facts; “current” in a source does not mean current in 2026. If policy timing is unspecified, the assistant is instructed to ask for the event date. The workbook's 25 people and 14 months are a separate sample with fractional dollar values, not additional backup rows. They are searchable as sample source text; exact workbook analytics are not exposed by the finance tool. The Word document describes a composite primary key absent from the dump and `year_desc` whereas the dump uses `year_value`.

## Troubleshooting and operations

| Symptom | Action |
|---|---|
| Docker daemon unavailable | Start Docker Desktop or the Docker Engine service. |
| Port already in use | Check for older Neo4j/Ollama/Streamlit services; stop only the service you intend to replace or update host mappings and `.env`. |
| Authentication fails | Check `.env`; an existing Neo4j volume retains its original password. Changing `NEO4J_AUTH` does not reset it. |
| Vector index missing | Run document ingestion and wait for `db.awaitIndexes` to complete. |
| Missing model / Ollama unreachable | Run `ollama list`, pull the exact tags, check `OLLAMA_URL`. Inside Docker use service name `ollama`. |
| Embedding too long | `truncate=False` prevents silent loss. Reduce the chunk size in `sources.py` and re-import changed chunks in a fresh graph. |
| Finance unavailable | Wait for the full import completion marker; retry the importer if interrupted. |
| Incorrect date or no sources | Set the event date, use exact IDs, and inspect evidence validity. |
| Memory pressure | Start with `--documents-only`, allocate more Docker memory, and avoid running large extra models. |
| Python dependency issues | Use a clean virtual environment and Python 3.12. |

Stop services with `docker compose stop` (volumes are retained). Back up the Neo4j data volume while the database is stopped, plus source files, reports and private configuration. Follow Neo4j's official offline dump instructions for database-portable backups. Do not run `docker compose down -v` unless you intend to delete this project's graph/model volumes.

The supplied Compose file was scanned as configuration; its embedded password was not copied into this app. A new private `.env` is used. Documents, emails, and embedded commands are treated as evidence, never executable instructions. The LLM has no arbitrary SQL/Cypher execution tool. Fixture JSON labels and relationship types pass identifier validation. Prompt defenses are not a substitute for database access controls.

## Vendor and Graph RAG references

- [Neo4j Python driver](https://neo4j.com/docs/python-manual/current/)
- [Neo4j 5 vector indexes](https://neo4j.com/docs/cypher-manual/5/indexes/semantic-indexes/vector-indexes/) — this project pins the Neo4j 5.26 line for the supported `db.index.vector.queryNodes` API.
- [Cypher MERGE](https://neo4j.com/docs/cypher-manual/current/clauses/merge/)
- [Neo4j GraphRAG Python package](https://neo4j.com/docs/neo4j-graphrag-python/current/) — further patterns; this app implements its retrieval pipeline directly with the driver.
- [GraphAcademy](https://graphacademy.neo4j.com/)
- [Microsoft GraphRAG research](https://microsoft.github.io/graphrag/)
- [Ollama API](https://docs.ollama.com/api/introduction)
- [Ollama embedding endpoint](https://docs.ollama.com/api/embed)
- [Streamlit documentation](https://docs.streamlit.io/)
- [Docker installation](https://docs.docker.com/get-started/get-docker/)

The application logic is entirely Python. HTML/CSS style the interface and the two requested standalone guides; Compose configures infrastructure. No external LLM API or APOC plugin is required.
