import argparse
import json
import sqlite3
from collections import defaultdict
from .config import Settings
from .graph import Graph, identifier
from .llm import Ollama
from .sources import documents, split_text, digest, scan, CHUNKER_VERSION
from .sql_dump import stage

def properties(item):
    # Neo4j properties cannot contain nested maps or lists of maps.
    return {k: json.dumps(v, sort_keys=True) if isinstance(v, dict) or
            isinstance(v, list) and any(isinstance(x, dict) for x in v) else v
            for k, v in item.items() if v is not None}

def batches(cursor, size=2000):
    while rows := cursor.fetchmany(size):
        yield [dict(r) for r in rows]

def ingest_documents(graph, llm, data):
    probe = llm.embed(['dimension check'])[0]
    graph.schema(len(probe))
    fixtures = json.loads((data / 'corpus/graph/entities.json').read_text())
    for e in fixtures:
        label = identifier(e['kind'])
        # Finance fixture metrics are replaced by the complete structured import.
        if label == 'MonthlySales':
            continue
        graph.query(f'MERGE (e:Entity {{id:$id}}) SET e:{label} SET e += $props', id=e['id'], props=properties(e))
    for d in documents(data):
        graph.query('MERGE (d:Entity:Document {id:$id}) SET d += $props', id=d['id'],
                    props={k: v for k, v in d.items() if k not in {'text', 'entity_ids'}})
        for eid in d['entity_ids']:
            graph.query('MATCH (d:Document {id:$doc}), (e:Entity {id:$id}) MERGE (d)-[:MENTIONS]->(e)', doc=d['id'], id=eid)
        old = graph.query('MATCH (c:Chunk)-[:PART_OF]->(:Document {id:$id}) RETURN c.id AS id, c.sha256 AS hash, c.embedding_model AS model, c.chunker_version AS chunker', id=d['id'])
        if old and all(r['hash'] == d['sha256'] and r['model'] == llm.s.embed_model and r['chunker'] == CHUNKER_VERSION for r in old):
            continue
        pieces = list(split_text(d['text']))
        embeddings = llm.embed(pieces)
        rows = [{'id': f'{d["id"]}#{i+1:03}', 'text': text, 'embedding': vector,
                 'sha256': d['sha256'], 'embedding_model': llm.s.embed_model, 'chunker_version': CHUNKER_VERSION}
                for i, (text, vector) in enumerate(zip(pieces, embeddings))]
        # Replace only this document's old chunks after embeddings succeed.
        graph.query('MATCH (c:Chunk)-[:PART_OF]->(:Document {id:$id}) DETACH DELETE c', id=d['id'])
        graph.query('''MATCH (d:Document {id:$doc}) UNWIND $rows AS row
            MERGE (c:Chunk {id:row.id}) SET c += row MERGE (c)-[:PART_OF]->(d)''', doc=d['id'], rows=rows)
        print(f'Embedded {d["id"]}: {len(rows)} chunks', flush=True)
    relationships = json.loads((data / 'corpus/graph/relationships.json').read_text())
    for r in relationships:
        if r['relationship'] in {'HAS_METRIC', 'FOR_PERIOD'}:
            continue
        rel = identifier(r['relationship'])
        props = properties({k: v for k, v in r.items() if k not in {'source_id', 'target_id', 'relationship'}})
        graph.query(f'''MATCH (a:Entity {{id:$source}}), (b:Entity {{id:$target}})
            MERGE (a)-[r:{rel} {{document_id:$doc}}]->(b) SET r += $props''',
            source=r['source_id'], target=r['target_id'], doc=r.get('document_id', ''), props=props)
    graph.query('CALL db.awaitIndexes(300)')

def ingest_finance(graph, data):
    database = data / 'finance.sqlite'
    source_hash = digest(data / 'finance_backup.sql')
    counts = stage(data / 'finance_backup.sql', database)
    print('Validated SQL rows:', counts, flush=True)
    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    try:
        for rows in batches(conn.execute('SELECT * FROM sales_teams')):
            graph.query('''UNWIND $rows AS r MERGE (t:Entity:SalesTeam {id:'TEAM-'+toString(r.sales_team_id)})
                SET t.name=trim(r.sales_team_name), t.sales_team_id=r.sales_team_id, t.origin='mysql_backup' ''', rows=rows)
        for rows in batches(conn.execute('SELECT * FROM sales_reps')):
            graph.query('''UNWIND $rows AS row
                MERGE (r:Entity:SalesRep {id:'REP-'+toString(row.sales_rep_id)})
                SET r.sales_rep_id=row.sales_rep_id, r.name=trim(row.sales_rep_first_name)+' '+trim(row.sales_rep_last_name), r.origin='mysql_backup'
                WITH row,r MATCH (t:SalesTeam {id:'TEAM-'+toString(row.sales_team_id)})
                MERGE (r)-[edge:MEMBER_OF {scope:'current_dump_membership'}]->(t)
                SET edge.origin='mysql_backup' ''', rows=rows)
        periods = conn.execute('SELECT y.year_id,y.year_value,m.month_id,m.month_desc FROM years y CROSS JOIN months m').fetchall()
        graph.query('''UNWIND $rows AS r MERGE (p:Entity:Period {id:'PERIOD-'+toString(r.year_value)+'-'+right('0'+toString(r.month_id),2)})
            SET p.year=r.year_value,p.month=r.month_id,p.name=trim(r.month_desc)+' '+toString(r.year_value)''', rows=[dict(r) for r in periods])
        total = 0
        for rows in batches(conn.execute('''SELECT s.*,y.year_value AS year FROM sales_reps_sales_data s JOIN years y USING(year_id)'''), 5000):
            graph.query('''UNWIND $rows AS row
                MATCH (r:SalesRep {id:'REP-'+toString(row.sales_rep_id)})
                MATCH (p:Period {id:'PERIOD-'+toString(row.year)+'-'+right('0'+toString(row.month_id),2)})
                MERGE (m:MonthlySales {id:'METRIC-'+toString(row.sales_rep_id)+'-'+toString(row.year)+'-'+right('0'+toString(row.month_id),2)})
                SET m += row, m.origin='mysql_backup', m.source='finance_backup.sql', m.source_sha256=$hash
                MERGE (r)-[:HAS_METRIC]->(m) MERGE (m)-[:FOR_PERIOD]->(p)''', rows=rows, hash=source_hash)
            total += len(rows)
            if total % 100000 == 0:
                print(f'Imported {total:,} / {counts["sales_reps_sales_data"]:,} metrics', flush=True)
        actual = graph.stats()['metrics']
        if actual != counts['sales_reps_sales_data']:
            raise ValueError(f'Metric count mismatch: source {counts}, graph {actual}; use a fresh database')
        graph.query('MERGE (i:Import {id:"finance"}) SET i.status="complete", i.rows=$rows, i.source_sha256=$hash',
                    rows=total, hash=source_hash)
        return counts
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--documents-only', action='store_true', help='Pilot only; finance answers remain disabled')
    parser.add_argument('--finance-only', action='store_true')
    parser.add_argument('--scan-only', action='store_true')
    parser.add_argument('--source', type=str, default='data')
    args = parser.parse_args()
    s = Settings()
    if args.scan_only:
        from pathlib import Path
        result = scan(Path(args.source), s.data, Path('reports/source-scan.json'))
        counts = stage(s.data / 'finance_backup.sql', s.data / 'finance.sqlite')
        result['finance_counts'] = counts
        Path('reports/source-scan.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(counts, indent=2))
        return
    graph = Graph(s)
    try:
        if not args.finance_only:
            ingest_documents(graph, Ollama(s), s.data)
        else:
            graph.schema(len(Ollama(s).embed(['dimension check'])[0]))
        if not args.documents_only:
            graph.query('MERGE (i:Import {id:"finance"}) SET i.status="running"')
            ingest_finance(graph, s.data)
        print(json.dumps(graph.stats(), indent=2))
    finally:
        graph.close()

if __name__ == '__main__':
    main()
