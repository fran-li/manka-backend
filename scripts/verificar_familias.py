#!/usr/bin/env python3
"""Valida semilla de familias en SQLite (NO equivale a una prueba PostgreSQL)."""
import importlib.util,sys,sqlite3,csv,re
from pathlib import Path
BASE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('converter',BASE/'convertir_a_familias.py')
m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
seed=Path(sys.argv[1]) if len(sys.argv)>1 else BASE/'manka_seed_familias.sql'
source=Path(sys.argv[2]) if len(sys.argv)>2 else BASE/'main.csv'
con=sqlite3.connect(':memory:')
con.executescript(m.sqlite_schema())
con.execute('ALTER TABLE dishes ADD COLUMN source_ingredients_text TEXT')
con.execute('ALTER TABLE dish_ingredients ADD COLUMN ingredient_detail TEXT')
raw='\n'.join(x for x in seed.read_text(encoding='utf-8').splitlines() if not x.startswith('SELECT setval('))
con.executescript(raw)
issues=con.execute('PRAGMA foreign_key_check').fetchall();assert not issues,issues[:5]
counts=dict((t,con.execute('SELECT COUNT(*) FROM '+t).fetchone()[0]) for t in ['protein_categories','ingredients','dishes','dish_ingredients','ingredient_aliases','protein_sources','dish_protein_sources','tags','dish_tags'])
assert counts['dishes']==20236,counts
rows={int(row['Id']):row for row in csv.DictReader(source.open(encoding='utf-8-sig',newline=''))}
assert len(rows)==20236
not_equal=[]
for sid,name,raw_ingredients in con.execute('SELECT source_id,name,source_ingredients_text FROM dishes'):
 row=rows[sid]
 if row['Nombre']!=name or row['Ingredientes']!=raw_ingredients:not_equal.append(sid)
assert not not_equal, f'Diferencias en nombres/ingredientes: {not_equal[:10]}'
assert con.execute('SELECT COUNT(*) FROM (SELECT dish_id,ingredient_id,COUNT(*) n FROM dish_ingredients GROUP BY dish_id,ingredient_id HAVING n>1)').fetchone()[0]==0
families={n:i for i,n in con.execute('SELECT id,name FROM ingredients')}
for name in ['Papa','Tomate','Tomatillo','Verduras','Cebolla','Ajo','Queso','Zanahoria','Huevo','Salsa de tomate','Jugo de limón']:
 assert name in families,name
# explícitos: equivalencias con misma clave para distintas variedades
mapping={row['nombre_anterior']:row['id_nuevo'] for row in csv.DictReader((BASE/'equivalencias_familias.csv').open(encoding='utf-8-sig',newline=''))}
for n in ['Papa','Papa amarilla','Papa roja','Papa blanca']:
 assert n in mapping,(n,'no encontrada')
 assert int(mapping[n])==families['Papa'],(n,mapping[n],families['Papa'])
assert families['Tomate']!=families['Salsa de tomate']
assert families['Tomate']!=families['Tomatillo']
assert families['Verduras']!=families['Caldo de verduras']
assert con.execute('SELECT COUNT(*) FROM dishes d LEFT JOIN dish_ingredients di ON di.dish_id=d.id WHERE di.id IS NULL').fetchone()[0] >= 1
for n in ('Papa','Tomate','Verduras','Cebolla','Ajo'):
 i=families[n]
 examples=con.execute('SELECT dish_id,quantity_text,ingredient_detail FROM dish_ingredients WHERE ingredient_id=? AND ingredient_detail IS NOT NULL LIMIT 4',(i,)).fetchall()
 assert examples,(n,i)
 print(n,'ID',i,'ejemplos:',examples[:2])
print('Validación integral SQLite OK; categorías y cantidades:',counts)
print('No hay diferencias en nombre e ingredientes originales; ni referencias huérfanas; ni pares duplicados.')
print('IMPORTANTE: No es una validación PostgreSQL real ni garantiza equivalencias semánticas perfectas.')
