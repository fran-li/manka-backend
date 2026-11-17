#!/usr/bin/env python3
"""Valida SQL de Manka en SQLite temporal sin tocar PostgreSQL. Solo DML; no prueba PostgreSQL.
Uso: python scripts/validar_semilla.py database/seed/manka_seed.sql
"""
from pathlib import Path
import sqlite3
import sys

if len(sys.argv) != 2:
    raise SystemExit('Uso: python scripts/validar_semilla.py database/seed/manka_seed.sql')
path=Path(sys.argv[1]);assert path.is_file(), f'No existe {path}'
db=sqlite3.connect(':memory:')
db.execute('PRAGMA foreign_keys=ON')
db.executescript('''
CREATE TABLE protein_categories(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE ingredients(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, parent_id INT REFERENCES ingredients(id));
CREATE TABLE dishes(id INTEGER PRIMARY KEY, name TEXT NOT NULL, preparation_minutes INT, difficulty TEXT,
 popularity_score INT NOT NULL, preparation TEXT NOT NULL, protein_category_id INT REFERENCES protein_categories(id),
 source_id INT UNIQUE, source_url TEXT, country TEXT, servings INT, meal_type TEXT, rating_average REAL,
 rating_votes INT, duration_estimated INT NOT NULL, difficulty_estimated INT NOT NULL);
CREATE TABLE dish_ingredients(id INTEGER PRIMARY KEY,dish_id INT NOT NULL REFERENCES dishes(id),
 ingredient_id INT NOT NULL REFERENCES ingredients(id), quantity_text TEXT, is_required INT NOT NULL,
 UNIQUE(dish_id,ingredient_id));
CREATE TABLE ingredient_aliases(id INTEGER PRIMARY KEY,alias TEXT,alias_key TEXT UNIQUE NOT NULL,
 ingredient_id INT NOT NULL REFERENCES ingredients(id));
CREATE TABLE protein_sources(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL);
CREATE TABLE dish_protein_sources(dish_id INT NOT NULL REFERENCES dishes(id),
 protein_source_id INT NOT NULL REFERENCES protein_sources(id),PRIMARY KEY(dish_id,protein_source_id));
CREATE TABLE tags(id INTEGER PRIMARY KEY,name TEXT NOT NULL,type TEXT NOT NULL,UNIQUE(name,type));
CREATE TABLE dish_tags(dish_id INT NOT NULL REFERENCES dishes(id),tag_id INT NOT NULL REFERENCES tags(id),
 PRIMARY KEY(dish_id,tag_id));
''')
sql='\n'.join(line for line in path.read_text(encoding='utf-8').splitlines()
              if not line.startswith('SELECT setval('))
db.executescript(sql)
counts={table:db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in (
    'protein_categories','ingredients','dishes','dish_ingredients','ingredient_aliases',
    'protein_sources','dish_protein_sources','tags','dish_tags')}
errors=db.execute('PRAGMA foreign_key_check').fetchall()
assert not errors, f'Claves foráneas inválidas: {errors[:5]}'
assert all(counts[t]>0 for t in ['dishes','ingredients','dish_ingredients'])
print('SQL y claves foráneas: correctos en SQLite (NO en PostgreSQL)')
for k,v in counts.items():print(f'{k}: {v:,}')
print('Sin ingredientes:',db.execute('SELECT COUNT(*) FROM dishes d WHERE NOT EXISTS (SELECT 1 FROM dish_ingredients x WHERE x.dish_id=d.id)').fetchone()[0])
