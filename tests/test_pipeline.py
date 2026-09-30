import tempfile
import unittest
from pathlib import Path
from graphrag.sql_dump import tuples,stage
from graphrag.retrieval import finance_filters
from graphrag.sources import split_text
from graphrag.graph import identifier

class PipelineTests(unittest.TestCase):
    def test_escaped_mysql_strings(self):
        self.assertEqual(list(tuples("(1,'O\\'Neil, Pat\\r',NULL),(2,'a\\\\b',3)")),
                         [(1,"O'Neil, Pat",None),(2,'a\\b',3)])

    def test_duplicate_finance_key_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'source.sql'
            source.write_text("INSERT INTO `sales_reps_sales_data` VALUES (1,1,1,2,3),(1,1,1,4,5);\n")
            import sqlite3
            with self.assertRaises(sqlite3.IntegrityError):
                stage(source,Path(temp)/'out.sqlite')
            self.assertFalse((Path(temp)/'out.sqlite').exists())

    def test_foreign_key_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'source.sql'
            source.write_text("INSERT INTO `sales_reps_sales_data` VALUES (1,1,1,2,3);\n")
            with self.assertRaises(ValueError):
                stage(source,Path(temp)/'out.sqlite')

    def test_finance_scope(self):
        self.assertEqual(finance_filters('actual sales REP-100001 January 2018'),
                         {'year':2018,'month':1,'rep':100001,'team':None})
        self.assertEqual(finance_filters('total sales team 1 in 2023')['team'],1)
        for q in ['sales in 2023 and 2024','customer sales total in 2023','sales for Elyse in 2023',
                  'compare sales REP-100001 2023','total sales Q1 2023',
                  'total sales for Elyse in 2023','total sales on 2023-01-15']:
            self.assertIn('clarification',finance_filters(q))
        self.assertEqual(finance_filters('total sales in Jan 2023')['month'],1)
        self.assertEqual(finance_filters('actual sales REP-100001 2023-01')['month'],1)

    def test_chunk_coverage(self):
        text='abc def\n'*2000
        chunks=list(split_text(text))
        self.assertTrue(all(len(c)<=2400 for c in chunks))
        self.assertTrue(chunks[0].startswith(text[:20]))
        self.assertTrue(chunks[-1].endswith(text[-20:]))

    def test_identifier_injection(self):
        with self.assertRaises(ValueError):
            identifier('Entity`) DELETE n //')

if __name__=='__main__':
    unittest.main()
