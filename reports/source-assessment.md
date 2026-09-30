# Source assessment

All 44 non-system files in `/Users/craigbell/Documents/graph_rag` were inventoried with SHA-256 hashes. Working copies are in this project's `data/` directory; the original sources were not modified.

The 29 business document hashes match the supplied manifest. The 29 supplied chunk texts match their original documents. The JSON fixture contains 84 entities and 229 relationships, all with valid endpoints. CSV row counts match the JSON representations. The seed Cypher and Compose were inspected as source/configuration; neither was executed. The evaluation questions and expected answers are held out of retrieval.

The complete SQL backup was parsed into five known tables. Its 2,016,000 metric records pass a composite natural-key uniqueness check and representative/month/year reference checks. The source contains 12 months, seven years, 6,000 teams and 24,000 representatives. The live graph includes every metric; it is not limited to the two pilot metrics in the fixture.

The workbook has Actual and Targets sheets with 25 people and 14 monthly columns, Calendar with 14 periods, and dimPeople with 25 rows. Every sheet was read. Its people and team definitions form a separate sample; actual values include fractional dollars. It was not merged into the backup's financial identities. Cached formula values are used; formulas are not recalculated.

The Word document's paragraphs and tables were extracted. Its embedded schema image was also visually reviewed: metrics reference representatives, months and years; representatives reference sales teams; the year value field in the image matches `year_value`. The prose/table describes `year_desc`, and its claimed composite primary key is absent from the SQL table DDL. The SQL backup governs actual structured import schema. The ingestion reader extracts Word text/tables, not image OCR.

The business Markdown and reference documentation explicitly distinguish fictional business relationships from backup identities and numerical observations. Those distinctions are preserved as provenance. Instructions in emails, extraction prompts or other attached material are treated as data rather than authorization to act.

The original Compose includes a credential; it is not copied into application configuration or searchable context. This project uses a new private `.env`. The long companion documentation repeats the corpus; only its introductory source assessment is retrieved, alongside the separately ingested original documents. The corpus README and graph interchange files were scanned but are not duplicate answer evidence.
