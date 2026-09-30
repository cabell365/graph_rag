import re
from neo4j import GraphDatabase
from .config import Settings

def identifier(value):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', value):
        raise ValueError(f'Invalid graph type: {value}')
    return value

class Graph:
    def __init__(self, settings=None):
        self.s = settings or Settings()
        if not self.s.password:
            raise ValueError('Set NEO4J_PASSWORD in .env')
        self.driver = GraphDatabase.driver(self.s.uri, auth=(self.s.user, self.s.password))

    def close(self):
        self.driver.close()

    def query(self, cypher, **params):
        records, _, _ = self.driver.execute_query(cypher, parameters_=params, database_=self.s.database)
        return [r.data() for r in records]

    def schema(self, dimensions):
        for label in ['Entity', 'Chunk', 'MonthlySales', 'Period']:
            self.query(f'CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE')
        self.query('CREATE FULLTEXT INDEX chunk_text IF NOT EXISTS FOR (c:Chunk) ON EACH [c.text]')
        self.query(f'''CREATE VECTOR INDEX chunk_vectors IF NOT EXISTS FOR (c:Chunk) ON (c.embedding)
            OPTIONS {{indexConfig: {{`vector.dimensions`: {int(dimensions)}, `vector.similarity_function`: 'cosine'}}}}''')
        existing = self.query("SHOW VECTOR INDEXES YIELD name, options WHERE name='chunk_vectors' RETURN options")
        if existing[0]['options']['indexConfig']['vector.dimensions'] != dimensions:
            raise ValueError('Embedding dimension changed; use a fresh database/index')
        self.query('CREATE INDEX metric_rep IF NOT EXISTS FOR (m:MonthlySales) ON (m.sales_rep_id)')
        self.query('CREATE INDEX metric_year IF NOT EXISTS FOR (m:MonthlySales) ON (m.year)')
        self.query('CREATE INDEX rep_numeric_id IF NOT EXISTS FOR (r:SalesRep) ON (r.sales_rep_id)')
        self.query('CREATE INDEX team_numeric_id IF NOT EXISTS FOR (t:SalesTeam) ON (t.sales_team_id)')
        self.query('CREATE INDEX rep_id IF NOT EXISTS FOR (r:SalesRep) ON (r.id)')
        self.query('CREATE INDEX team_id IF NOT EXISTS FOR (t:SalesTeam) ON (t.id)')
        self.query('CREATE INDEX document_id IF NOT EXISTS FOR (d:Document) ON (d.id)')

    def stats(self):
        return self.query('''CALL () { MATCH (d:Document) RETURN count(d) AS documents }
            CALL () { MATCH (c:Chunk) RETURN count(c) AS chunks }
            CALL () { MATCH (e:Entity) RETURN count(e) AS entities }
            CALL () { MATCH (m:MonthlySales) RETURN count(m) AS metrics }
            RETURN documents, chunks, entities, metrics''')[0]
