"""Parse data INSERTs only. Never execute attached SQL or embedded instructions."""
import re
import sqlite3
from pathlib import Path

TABLES = {
    'months': ('month_id', 'month_desc'),
    'years': ('year_id', 'year_value'),
    'sales_teams': ('sales_team_id', 'sales_team_name'),
    'sales_reps': ('sales_rep_id', 'sales_rep_last_name', 'sales_rep_first_name', 'sales_rep_pic', 'sales_team_id'),
    'sales_reps_sales_data': ('sales_rep_id', 'month_id', 'year_id', 'target_sales', 'actual_sales'),
}

def tuples(text):
    """MySQL tuple lexer supporting escaped quotes, commas and NULL."""
    row, token, quoted, in_quote, escape, active = [], [], False, False, False, False
    def value():
        raw = ''.join(token)
        if quoted:
            return raw.strip()
        raw = raw.strip()
        return None if raw.upper() == 'NULL' else int(raw)
    for ch in text:
        if in_quote:
            if escape:
                token.append({'n': '\n', 'r': '\r', 't': '\t', '0': '\0'}.get(ch, ch))
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == "'":
                in_quote = False
            else:
                token.append(ch)
        elif ch == "'":
            in_quote, quoted = True, True
        elif ch == '(':
            active = True
            row, token, quoted = [], [], False
        elif active and ch in ',)':
            row.append(value())
            token, quoted = [], False
            if ch == ')':
                yield tuple(row)
                active = False
        elif active:
            token.append(ch)
    if active or in_quote:
        raise ValueError('Unterminated SQL tuple')

def records(path):
    with Path(path).open(encoding='utf-8-sig') as source:
        for line in source:
            match = re.match(r'INSERT INTO `([a-z_]+)` VALUES (.*);\s*$', line)
            if match:
                table = match[1]
                if table not in TABLES:
                    raise ValueError(f'Unexpected source table: {table}')
                for row in tuples(match[2]):
                    if len(row) != len(TABLES[table]):
                        raise ValueError(f'Unexpected column count for {table}')
                    yield table, row

def stage(path, destination):
    """Atomic staging with natural key and FK checks; duplicate metrics fail."""
    destination = Path(destination)
    temporary = destination.with_suffix('.building.sqlite')
    if temporary.exists():
        temporary.unlink()
    conn = sqlite3.connect(temporary)
    conn.executescript('''
        CREATE TABLE months(month_id INTEGER PRIMARY KEY, month_desc TEXT);
        CREATE TABLE years(year_id INTEGER PRIMARY KEY, year_value INTEGER);
        CREATE TABLE sales_teams(sales_team_id INTEGER PRIMARY KEY, sales_team_name TEXT);
        CREATE TABLE sales_reps(sales_rep_id INTEGER PRIMARY KEY, sales_rep_last_name TEXT,
            sales_rep_first_name TEXT, sales_rep_pic TEXT, sales_team_id INTEGER);
        CREATE TABLE sales_reps_sales_data(sales_rep_id INTEGER NOT NULL, month_id INTEGER NOT NULL,
            year_id INTEGER NOT NULL, target_sales INTEGER NOT NULL, actual_sales INTEGER NOT NULL,
            PRIMARY KEY(sales_rep_id, month_id, year_id));
    ''')
    buffers = {table: [] for table in TABLES}
    counts = {table: 0 for table in TABLES}
    def flush(table):
        if buffers[table]:
            conn.executemany(f'INSERT INTO {table} VALUES ({",".join("?" for _ in TABLES[table])})', buffers[table])
            buffers[table].clear()
    try:
        for table, row in records(path):
            buffers[table].append(row)
            counts[table] += 1
            if len(buffers[table]) >= 10000:
                flush(table)
        for table in TABLES:
            flush(table)
        for query in [
            'SELECT count(*) FROM sales_reps r LEFT JOIN sales_teams t USING(sales_team_id) WHERE t.sales_team_id IS NULL',
            'SELECT count(*) FROM sales_reps_sales_data s LEFT JOIN sales_reps r USING(sales_rep_id) LEFT JOIN months m USING(month_id) LEFT JOIN years y USING(year_id) WHERE r.sales_rep_id IS NULL OR m.month_id IS NULL OR y.year_id IS NULL',
            'SELECT count(*) FROM months WHERE month_id NOT BETWEEN 1 AND 12']:
            if conn.execute(query).fetchone()[0]:
                raise ValueError('Finance source failed reference validation')
        conn.commit()
    finally:
        conn.close()
    temporary.replace(destination)
    return counts
