#!/usr/bin/env python3
"""Manka: agrupa variantes de ingredientes bajo IDs familiares y conserva detalle
por receta. Usa la semilla revisada anterior como entrada más main.csv como fuente de
verdad del texto original (sin reutilizar las 212 recetas legadas).
Sin dependencias externas; NO realiza inferencias GPT ni garantiza semántica perfecta.
"""
import argparse,csv,sqlite3,re,unicodedata,collections,sys
from pathlib import Path

def key(v):
    t=unicodedata.normalize('NFKD',str(v or '').casefold())
    t=''.join(c for c in t if not unicodedata.combining(c))
    t=re.sub(r'[_‐‑–—-]+',' ',t)
    t=re.sub(r'[^a-z0-9ñ ]',' ',t)
    return re.sub(r'\s+',' ',t).strip()

# Familia común, sin confundir elaboraciones con alimentos frescos.
# Orden: las expresiones específicas se examinan antes que la palabra genérica.
SPECIFIC=[
 ('Manteca de cerdo',r'\bmanteca\s+de\s+(?:cerdo|puerco)\b'),
 ('Agua de coco',r'\bagua\s+de\s+coco\b'),
 ('Pimienta de cayena',r'\bpimienta\s+de\s+cayena\b'),
 ('Sal de ajo',r'\bsal\s+de\s+ajo\b'),
 ('Pasta de ajo',r'\bpasta\s+de\s+ajo\b'),
 ('Leche',r'\bleche\s+de\s+vaca\b'),
 ('Salsa de tomate',r'\b(?:salsas?\s+de\s+tomate|salsas?\s+de\s+jitomate|tomate\s+frito)\b'),
 ('Pasta de tomate',r'\b(?:pasta|concentrado)\s+de\s+(?:tomates?|jitomates?)\b'),
 ('Puré de tomate',r'\b(?:pure|triturado)\s+de\s+(?:tomates?|jitomates?)\b'),
 ('Salsa de soya',r'\b(?:salsa\s+de\s+(?:soya|soja)|sillao)\b'),
 ('Leche de coco',r'\bleche\s+de\s+coco\b'),
 ('Leche de almendra',r'\bleche\s+de\s+almendras?\b'),
 ('Leche de soya',r'\bleche\s+de\s+(?:soya|soja)\b'),
 ('Leche condensada',r'\bleche\s+condensada\b'),
 ('Leche evaporada',r'\bleche\s+evaporada\b'),
 ('Leche en polvo',r'\bleche\s+en\s+polvo\b'),
 ('Crema de leche',r'\b(?:crema\s+de\s+leche|nata\s+(?:para\s+cocinar|liquida))\b'),
 ('Caldo de pollo',r'\b(?:caldo|consome)\s+de\s+pollo\b'),
 ('Caldo de res',r'\b(?:caldo|consome)\s+de\s+(?:res|carne|ternera)\b'),
 ('Caldo de pescado',r'\b(?:caldo|fumet)\s+de\s+pescado\b'),
 ('Caldo de verduras',r'\bcaldo\s+de\s+verduras?\b'),
 ('Jugo de limón',r'\b(?:jugo|zumo)\s+de\s+limones?\b'),
 ('Jugo de naranja',r'\b(?:jugo|zumo)\s+de\s+naranjas?\b'),
 ('Jugo de lima',r'\b(?:jugo|zumo)\s+de\s+limas?\b'),
 ('Harina de maíz',r'\b(?:harina|masa)\s+de\s+maiz\b'),
 ('Harina de almendra',r'\bharina\s+de\s+almendras?\b'),
 ('Harina de arroz',r'\bharina\s+de\s+arroz\b'),
 ('Harina de trigo',r'\bharina\s+de\s+trigo\b'),
 ('Harina de avena',r'\bharina\s+de\s+avena\b'),
 ('Pan rallado',r'\b(?:pan\s+rallado|pan\s+molido)\b'),
 ('Ajo en polvo',r'\b(?:ajo\s+en\s+polvo|polvo\s+de\s+ajo)\b'),
 ('Cebolla en polvo',r'\b(?:cebolla\s+en\s+polvo|polvo\s+de\s+cebolla)\b'),
 ('Chile en polvo',r'\b(?:chile\s+en\s+polvo|polvo\s+de\s+chile)\b'),
 ('Puré de papa',r'\b(?:pure\s+de\s+(?:papa|patata)|papa\s+en\s+pure)\b'),
 ('Papa frita',r'\b(?:papas?\s+fritas?|patatas?\s+fritas?|papas?\s+chips|patatas?\s+chips)\b'),
 ('Almidón de papa',r'\b(?:almidon|fecula)\s+de\s+(?:papa|patata)\b'),
 ('Fécula de maíz',r'\b(?:fecula\s+de\s+maiz|maicena)\b'),
 ('Tortilla de maíz',r'\b(?:tortillas?\s+de\s+maiz|tortillas?\s+de\s+corn)\b'),
 ('Tortilla de trigo',r'\btortillas?\s+de\s+trigo\b'),
 ('Aceite de oliva',r'\baceite\s+(?:de\s+)?olivas?\b'),
 ('Aceite de coco',r'\baceite\s+(?:de\s+)?coco\b'),
 ('Aceite de girasol',r'\baceite\s+(?:de\s+)?girasol\b'),
 ('Aceite de maíz',r'\baceite\s+(?:de\s+)?maiz\b'),
 ('Vinagre de manzana',r'\bvinagre\s+(?:de\s+)?manzana\b'),
 ('Vinagre balsámico',r'\bvinagre\s+balsamico\b'),
 ('Vinagre de vino',r'\bvinagre\s+(?:de\s+)?vino\b'),
 ('Crema de cacahuate',r'\b(?:mantequilla|crema)\s+de\s+(?:mani|cacahuete|cacahuate)\b'),
 ('Mantequilla de almendra',r'\bmantequilla\s+de\s+almendras?\b'),
 ('Cacao en polvo',r'\b(?:cacao|chocolate)\s+en\s+polvo\b'),
 ('Salsa',r'^salsas?\b'),
 ('Caldo',r'^(?:caldo|consome)s?\b'),
 ('Sopa',r'^sopas?\b'),
]
# Familia base: todas las variedades del mismo alimento comparten ID. Los productos
# procesados ya protegidos arriba conservan otra identidad.
FAMILIES=[
 ('Papa',r'\b(?:papas?|patatas?)\b'), ('Tomate',r'\b(?:tomates?|jitomates?)\b'),
 ('Cebolla',r'\b(?:cebollas?|cebollino|cebollin|cebolletas?|cebollas?\s+chinas?|cebollas?\s+de\s+verdeo)\b'),
 ('Ajo',r'\b(?:ajos?|ajitos?)\b'),('Zanahoria',r'\bzanahorias?\b'),
 ('Huevo',r'\b(?:huevos?|yemas?\s+de\s+huevo|claras?\s+de\s+huevo)\b'),('Alcaparra',r'\balcaparras?\b'),('Aceituna',r'\baceitunas?\b'),('Haba',r'\bhabas?\b'),('Pasa',r'\bpasas?\b'),
 ('Palta',r'\b(?:paltas?|aguacates?)\b'),('Culantro',r'\b(?:culantro|cilantro)\b'),
 ('Arveja',r'\b(?:arvejas?|alverjas?|guisantes?|chicharos?)\b'),
 ('Frijol',r'\b(?:frijol(?:es)?|frejol(?:es)?|porotos?|alubias?|judias?\s+secas?)\b'),
 ('Lechuga',r'\blechugas?\b'),('Espinaca',r'\bespinacas?\b'),
 ('Repollo',r'\b(?:repollos?|col\s+blanca|col\s+morada)\b'),
 ('Apio',r'\b(?:apios?|celery)\b'),('Perejil',r'\bperejil\b'),
 ('Tomillo',r'\btomillo\b'),('Orégano',r'\boregano\b'),
 ('Romero',r'\bromero\b'),('Albahaca',r'\balbahaca\b'),
 ('Laurel',r'\blaurel\b'),('Hierbabuena',r'\bhierbabuena\b'),
 ('Menta',r'\bmenta\b'),('Epazote',r'\bepazote\b'),
 ('Pimiento',r'\b(?:pimientos?|pimentones?\s+morrones?|morrones?)\b'),
 ('Ají',r'\b(?:chiles?|chilis?|chilies?|aji(?:es)?|ajies)\b'),
 ('Calabaza',r'\b(?:calabazas?|zapallos?)\b'),('Calabacín',r'\b(?:calabacines?|calabacin|zucchinis?|calabacitas?)\b'),
 ('Berenjena',r'\bberenjenas?\b'),('Pepino',r'\bpepinos?\b'),
 ('Brócoli',r'\bbrocolis?\b'),('Coliflor',r'\bcoliflores?\b'),
 ('Chayote',r'\bchayotes?\b'),('Espárrago',r'\besparragos?\b'),
 ('Vainita',r'\b(?:vainitas?|ejotes?)\b'),('Acelga',r'\bacelgas?\b'),
 ('Rábano',r'\brabanos?\b'),('Nabo',r'\bnabos?\b'),
 ('Nopal',r'\bnopales?\b'),('Champiñón',r'\bchampi(?:non|nones)\b'),
 ('Seta',r'\bsetas?\b'),('Hongo',r'\bhongos?\b'),('Gelatina',r'\bgelatinas?\b'),('Maicena',r'\bmaicena\b'),
 ('Maíz',r'\b(?:maiz|elotes?|choclos?)\b'),('Arroz',r'\barroz\b'),
 ('Quinoa',r'\b(?:quinua|quinoa)\b'),('Avena',r'\bavena\b'),
 ('Lenteja',r'\blentejas?\b'),('Garbanzo',r'\bgarbanzos?\b'),
 ('Trigo',r'\btrigo\b'),('Harina',r'\bharinas?\b'),
 ('Pan',r'\bpan\b'),('Tallarín',r'\b(?:tallarines?|espaguetis?|espagueti|macarrones?|fideos?|coditos?)\b'),('Pasta',r'\bpastas?\b'),
 ('Tortilla',r'\btortillas?\b'),('Queso',r'\b(?:quesos?|quesitos?)\b'),
 ('Leche',r'\bleche\b'),('Yogur',r'\b(?:yogur(?:t|es|ts)?|yoghurt)\b'),
 ('Mantequilla',r'\bmantequillas?\b'),('Margarina',r'\bmargarina\b'),
 ('Aceite',r'\baceites?\b'),('Vinagre',r'\bvinagres?\b'),
 ('Sal',r'\bsal\b'),('Agua',r'\bagua\b'),
 ('Chocolate',r'\bchocolates?\b'),('Azúcar',r'\bazucar(?:es)?\b'),('Pimienta',r'\b(?:pimientas?|pepper)\b'),
 ('Comino',r'\bcomino\b'),('Canela',r'\bcanela\b'),
 ('Clavo de olor',r'\bclavos?\s+de\s+olor\b'),('Jengibre',r'\bjengibre\b'),
 ('Cúrcuma',r'\bcurcuma\b'),('Pimentón',r'\bpimenton\b'),
 ('Mostaza',r'\bmostaza\b'),('Mayonesa',r'\bmayonesa\b'),
 ('Ketchup',r'\b(?:ketchup|catsup|catsun)\b'),
 ('Limón',r'\blimon(?:es)?\b'),('Lima',r'\blimas?\b'),
 ('Naranja',r'\bnaranjas?\b'),('Mandarina',r'\bmandarinas?\b'),
 ('Manzana',r'\bmanzanas?\b'),('Plátano',r'\b(?:platanos?|bananas?|bananos?)\b'),
 ('Fresa',r'\b(?:fresas?|frutillas?)\b'),('Frambuesa',r'\bframbuesas?\b'),
 ('Arándano',r'\barandanos?\b'),('Mora',r'\bmoras?\b'),
 ('Piña',r'\b(?:pinas?|anan[aá]s)\b'),('Mango',r'\bmangos?\b'),
 ('Papaya',r'\bpapayas?\b'),('Sandía',r'\bsandias?\b'),
 ('Melón',r'\bmelones?\b'),('Pera',r'\bperas?\b'),
 ('Durazno',r'\b(?:duraznos?|melocotones?)\b'),('Uva',r'\buvas?\b'),
 ('Coco',r'\bcocos?\b'),('Almendra',r'\balmendras?\b'),
 ('Nuez',r'\b(?:nueces?|nuez)\b'),('Avellana',r'\bavellanas?\b'),
 ('Maní',r'\b(?:mani|cacahuates?|cacahuetes?)\b'),
 ('Castaña',r'\bcastanas?\b'),('Pistacho',r'\bpistachos?\b'),
 ('Pollo',r'\b(?:pollo|pollos|pechugas?\s+de\s+pollo|muslos?\s+de\s+pollo|piernas?\s+de\s+pollo)\b'),
 ('Carne de res',r'\b(?:res|ternera|vacuno|buey|carne\s+de\s+vaca|carne\s+de\s+res)\b'),
 ('Cerdo',r'\b(?:cerdo|puerco|cochino)\b'),('Pavo',r'\bpavos?\b'),
 ('Pescado',r'\bpescados?\b'),('Atún',r'\batun\b'),('Salmón',r'\bsalmon\b'),
 ('Tilapia',r'\btilapias?\b'),('Merluza',r'\bmerluza\b'),
 ('Bacalao',r'\bbacalao\b'),('Camarón',r'\b(?:camaron(?:es)?|gambas?)\b'),
 ('Langostino',r'\blangostinos?\b'),('Calamar',r'\bcalamares?\b'),
 ('Pulpo',r'\bpulpos?\b'),('Mejillón',r'\bmejillones?\b'),
 ('Almeja',r'\balmejas?\b'),('Sardina',r'\bsardinas?\b'),
 ('Jamón',r'\bjamones?\b'),('Tocino',r'\b(?:tocino|bacon|panceta)\b'),
 ('Chorizo',r'\bchorizos?\b'),('Salchicha',r'\bsalchichas?\b'),
 ('Miel',r'\bmiel\b'),('Levadura',r'\blevadura\b'),
 ('Polvo para hornear',r'\b(?:polvo\s+(?:para|de)\s+hornear|levadura\s+quimica)\b'),('Chorizo',r'\bchorizos?\b'),
]
COMPILED=[(label,re.compile(pattern)) for label,pattern in FAMILIES]
COMPILED_SPEC=[(label,re.compile(pattern)) for label,pattern in SPECIFIC]

# Cuando el texto es claramente un encabezado/instrucción y no contiene alimento, se
# mantiene en la auditoría y nunca se transforma en una categoría falsa.
NO_FOOD=re.compile(r'^(?:para\s+(?:las?|los?)\s+.*|(?:ingredientes?|preparaci[oó]n|decoraci[oó]n|guarnici[oó]n)\s*:?.*|'
                   r'(?:aparte\s+debes\s+tener|opcional|al\s+gusto|reservar))$',re.I)
PROCESSED_HEADS=('salsa ','salsas ','sopa ','sopas ','caldo ','consome ','crema ','pure ', 'pasta de ',
                 'jugo de ','zumo de ','extracto de ','esencia de ', 'concentrado de ','mermelada de ',
                 'jarabe de ','almidon de ','fecula de ','harina de ','leche de ','vino de ',
                 'vinagre de ','aceite de ', 'galletas de ', 'torta de ', 'pan de ', 'yogur de ',
                 'pate de ','cereal de ','hojuelas de ','semillas de ')
NOT_FOOD_HINTS=('bolsas de plastico','palillos de madera','papel film','servilletas','cuchillo','licuadora','termomix','horno ','pinchos de madera')

# Capas genéricas: una lista de compuestos seguros que, por ser un alimento elaborado,
# no debe agruparse con su materia prima.
def family_of(name):
    k=key(name)
    if not k:return None,'vacio',False
    if NO_FOOD.fullmatch(k) or any(x in k for x in NOT_FOOD_HINTS):return None,'texto no alimentario',False
    # Fragmentos con dos o más alimentos distintos: no se asigna un único ID.
    hits=[]
    for label,p in COMPILED:
        if p.search(k):hits.append(label)
    for label,p in COMPILED_SPEC:
        if p.search(k):
            if label in ('Salsa','Caldo','Sopa'):
                # Tipo de producto elaborado no genérico; mantener si carece de tipo claro
                return name,'producto elaborado (especificidad conservada)',False
            return label,'producto elaborado protegido',True
    if k.startswith(PROCESSED_HEADS) or re.search(r'\b(?:salsa|sopa|crema|pure|caldo|mermelada|harina|leche|aceite|pasta|almidon|fecula|jugo|zumo)\s+de\s+',k):
        return name,'elaboración específica conservada',False
    # Prevenir coincidencias simples como 'sal' dentro de una frase con dos ingredientes
    strong=[h for h in hits if h not in ('Sal','Agua','Aceite','Azúcar','Pimienta')]
    distinct=set(strong)
    # Pluralidades reales de una misma familia se agrupan.
    if len(distinct)==1:
        return next(iter(distinct)),'familia identificada',True
    if not strong and len(set(hits))==1:
        return hits[0],'ingrediente básico identificado',True
    if len(distinct)>1:
        return name,'combinación de alimentos: revisión',False
    # Evitar introducir como nombre canónico textos de medidas/instrucciones.
    if re.match(r'^(?:\d|/\d|una?\s+|cucharadita|taza|puñado|pellizco|pizca|libra|ml\b|kg\b)',k):
        return name,'fragmento/medida residual: revisión',False
    if len(k.split())>7:return name,'descripción extensa: revisión',False
    return name,'sin familia verificable',False

# Extensión: sustantivo principal y equivalencias generales para todo el catálogo.
from normalizador_head import normalize_extra, NOUNS
_family_of_v1 = family_of

def family_of(name):
    return normalize_extra(name, _family_of_v1, key, COMPILED)

def sqlite_schema():
 return '''
 PRAGMA foreign_keys=ON;
 CREATE TABLE protein_categories(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE);
 CREATE TABLE ingredients(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE,parent_id INTEGER REFERENCES ingredients(id));
 CREATE TABLE dishes(id INTEGER PRIMARY KEY,name TEXT NOT NULL,preparation_minutes INT,difficulty TEXT,popularity_score INT NOT NULL,preparation TEXT NOT NULL,protein_category_id INT REFERENCES protein_categories(id),source_id INT UNIQUE,source_url TEXT,country TEXT,servings INT,meal_type TEXT,rating_average REAL,rating_votes INT,duration_estimated INT NOT NULL,difficulty_estimated INT NOT NULL);
 CREATE TABLE dish_ingredients(id INTEGER PRIMARY KEY,dish_id INT NOT NULL REFERENCES dishes(id),ingredient_id INT NOT NULL REFERENCES ingredients(id),quantity_text TEXT,is_required INT NOT NULL,UNIQUE(dish_id,ingredient_id));
 CREATE TABLE ingredient_aliases(id INTEGER PRIMARY KEY,alias TEXT,alias_key TEXT UNIQUE NOT NULL,ingredient_id INT NOT NULL REFERENCES ingredients(id));
 CREATE TABLE protein_sources(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE);
 CREATE TABLE dish_protein_sources(dish_id INT NOT NULL REFERENCES dishes(id),protein_source_id INT NOT NULL REFERENCES protein_sources(id),PRIMARY KEY(dish_id,protein_source_id));
 CREATE TABLE tags(id INTEGER PRIMARY KEY,name TEXT NOT NULL,type TEXT NOT NULL,UNIQUE(name,type));
 CREATE TABLE dish_tags(dish_id INT NOT NULL REFERENCES dishes(id),tag_id INT NOT NULL REFERENCES tags(id),PRIMARY KEY(dish_id,tag_id));
 '''

def q(v):
 if v is None:return 'NULL'
 if isinstance(v,bool):return 'true' if v else 'false'
 if isinstance(v,int) or isinstance(v,float):return str(v)
 return "'"+str(v).replace("'","''")+"'"

def insert_many(out,table,cols,rows,chunk=350):
 vals=[]
 for row in rows:
  vals.append('('+', '.join(q(x) for x in row)+')')
  if len(vals)>=chunk:
   out.write(f'INSERT INTO {table} ({", ".join(cols)}) VALUES\n'+',\n'.join(vals)+';\n');vals.clear()
 if vals:out.write(f'INSERT INTO {table} ({", ".join(cols)}) VALUES\n'+',\n'.join(vals)+';\n')
 out.write('\n')

def run(inp,source,outdir):
 outdir.mkdir(parents=True,exist_ok=True)
 db=sqlite3.connect(':memory:')
 db.executescript(sqlite_schema())
 sql='\n'.join(line for line in inp.read_text(encoding='utf-8').splitlines() if not line.startswith('SELECT setval('))
 db.executescript(sql)
 if db.execute('PRAGMA foreign_key_check').fetchall():raise RuntimeError('SQL origen con claves foráneas inválidas')
 recipe_source={int(row['Id']):row for row in csv.DictReader(source.open(encoding='utf-8-sig',newline=''))}
 original_ing=list(db.execute('SELECT id,name,parent_id FROM ingredients ORDER BY id'))
 parents={id_:parent for id_,_,parent in original_ing}
 oldname={id_:name for id_,name,_ in original_ing}
 family_by_old={};candidate_status={};audit=[]
 # 1. Familias / padres: cada variante conocida remite al genérico.
 for iid,name,parent in original_ing:
  family,why,safe=family_of(name)
  # Los parentescos explícitos existentes solo aplican cuando no se trata de un
  # producto elaborado diferente (e.g. aceites diferentes, ajo en polvo).
  if parent and parent in oldname:
   ancestor=parent
   seen=set()
   while ancestor in parents and parents[ancestor] and ancestor not in seen:
    seen.add(ancestor);ancestor=parents[ancestor]
   old_parent=oldname.get(ancestor)
   if old_parent and family not in ('Ajo en polvo','Cebolla en polvo','Leche condensada'):
    pf,pwhy,psafe=family_of(old_parent)
    if pf and psafe and (safe or key(name) in (key(old_parent),)):
     # Aceite de oliva es distinto de aceite de girasol como producto, no forzar
     # una equivalencia cuando son aceites de distinto origen.
     if not (pf=='Aceite' and family in ('Aceite de oliva','Aceite de coco','Aceite de girasol','Aceite de maíz')):
      family=pf;why='pariente explícito del catálogo';safe=True
  # Las entradas que NO son ingredientes se eliminan como ID; quedan en el
  # texto bruto source_ingredients_text, auditable y recuperable.
  if family is None:
   family_by_old[iid]=None
   candidate_status[iid]=(why,False)
   audit.append([iid,name,'(descartado)',why,'revisión'])
   continue
  family_by_old[iid]=family
  candidate_status[iid]=(why,safe)
  if key(family)!=key(name) or not safe:
   audit.append([iid,name,family,why,'automático' if safe else 'revisión'])
 # Generar nombres canónicos. Evitar colisiones textuales al normalizar tildes.
 bykey={}
 for iid,name,_ in original_ing:
  family=family_by_old[iid]
  if family is not None:bykey.setdefault(key(family),family)
 canon=list(bykey.values())
 family_id={key(name):i for i,name in enumerate(canon,1)}
 old_to_new={iid:(family_id[key(family_by_old[iid])] if family_by_old[iid] is not None else None) for iid,_,_ in original_ing}
 # 2. Alias que conservan la forma original. No se duplica alias_key.
 alias_candidates=collections.defaultdict(set)
 name_by_aliaskey={key(name):name for iid,name,_ in original_ing}
 for iid,name,_ in original_ing:
  
  if old_to_new[iid] is not None:alias_candidates[key(name)].add(old_to_new[iid])
 for _id,alias,alias_key,oldid in db.execute('SELECT id,alias,alias_key,ingredient_id FROM ingredient_aliases'):
  
  if old_to_new[oldid] is not None:alias_candidates[key(alias)].add(old_to_new[oldid])
 aliases=[];alias_collisions=[]
 for k,ids in alias_candidates.items():
  if not k:continue
  if len(ids)==1:
   v=next(iter(ids));chosen=name_by_aliaskey.get(k,k)
   if key(chosen)!=key(canon[v-1]):aliases.append((len(aliases)+1,chosen,k,v))
  else:alias_collisions.append([k,' | '.join(str(x) for x in sorted(ids))])
 # 3. Conservar variante/origen y cantidad por plato; agrupar pares iguales
 # sin perder variedades diferentes cuando comparten la familia.
 groups=collections.OrderedDict()
 for did,oldid,qty,required in db.execute('SELECT dish_id,ingredient_id,quantity_text,is_required FROM dish_ingredients ORDER BY id'):
  fid=old_to_new[oldid];label=oldname[oldid]
  if fid is None:continue
  compound=(qty or 'no especificada').strip()
  gkey=(did,fid)
  g=groups.setdefault(gkey,{'quantities':[],'variants':[],'pairs':[],'required':0,'count':0})
  g['count']+=1
  if compound not in g['quantities']:g['quantities'].append(compound)
  if key(label)!=key(canon[fid-1]) and label not in g['variants']:g['variants'].append(label)
  pair=(label,compound)
  if pair not in g['pairs']:g['pairs'].append(pair)
  g['required']=max(int(bool(required)),g['required'])
 dish_rows=[];aggregated=0
 for (did,fid),data in groups.items():
  if data['count']>1:aggregated+=data['count']-1
  qs=[x for x in data['quantities'] if x!='no especificada']
  v=data['variants']
  # Conservar asociación precisa entre variedad y cantidad para las recetas
  # donde dos variedades comparten una sola familia.
  if len(data['pairs'])>1:
   detalle=' | '.join(f'{label}: {amount}' for label,amount in data['pairs'])
  else:
   detalle=' | '.join(v) or None
  dish_rows.append((len(dish_rows)+1,did,fid, ' / '.join(qs)[:255] if qs else 'no especificada',data['required'], detalle[:2000] if detalle else None))
 # 4. Incorporar el texto bruto del CSV de origen para recuperar cada detalle
 dishes=list(db.execute('SELECT id,name,preparation_minutes,difficulty,popularity_score,preparation,protein_category_id,source_id,source_url,country,servings,meal_type,rating_average,rating_votes,duration_estimated,difficulty_estimated FROM dishes ORDER BY id'))
 updated_dishes=[(r[0],recipe_source[r[7]]['Nombre'],*r[2:],recipe_source[r[7]]['Ingredientes']) for r in dishes]
 # 5. Escribir nueva semilla en orden de dependencias. NO incluye CREATE TABLE.
 with (outdir/'manka_seed_familias.sql').open('w',encoding='utf-8') as f:
  f.write('-- Manka: agrupación genérica de ingredientes, NO es un import incremental.\n')
  f.write('-- Base PostgreSQL nueva de prueba; ejecutar después de schema_familias.sql.\nBEGIN;\n\n')
  insert_many(f,'protein_categories',['id','name'],db.execute('SELECT * FROM protein_categories ORDER BY id'))
  insert_many(f,'ingredients',['id','name','parent_id'],((i,name,None) for i,name in enumerate(canon,1)))
  insert_many(f,'dishes',['id','name','preparation_minutes','difficulty','popularity_score','preparation','protein_category_id','source_id','source_url','country','servings','meal_type','rating_average','rating_votes','duration_estimated','difficulty_estimated','source_ingredients_text'],updated_dishes)
  insert_many(f,'dish_ingredients',['id','dish_id','ingredient_id','quantity_text','is_required','ingredient_detail'],dish_rows)
  insert_many(f,'ingredient_aliases',['id','alias','alias_key','ingredient_id'],aliases)
  insert_many(f,'protein_sources',['id','name'],db.execute('SELECT * FROM protein_sources ORDER BY id'))
  insert_many(f,'dish_protein_sources',['dish_id','protein_source_id'],db.execute('SELECT * FROM dish_protein_sources'))
  insert_many(f,'tags',['id','name','type'],db.execute('SELECT * FROM tags ORDER BY id'))
  insert_many(f,'dish_tags',['dish_id','tag_id'],db.execute('SELECT * FROM dish_tags'))
  for table in ['protein_categories','ingredients','dishes','dish_ingredients','ingredient_aliases','protein_sources','tags']:
   f.write(f"SELECT setval(pg_get_serial_sequence('{table}','id'), COALESCE((SELECT MAX(id) FROM {table}),1), true);\n")
  f.write('COMMIT;\n')
 with (outdir/'equivalencias_familias.csv').open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.writer(f);w.writerow(['id_anterior','nombre_anterior','id_nuevo','nombre_generico','motivo','decision']);
  for iid,name,_ in original_ing:
   why,safe=candidate_status[iid]
   w.writerow([iid,name,old_to_new[iid] or '',family_by_old[iid] or '(descartado)',why,'automático' if safe else 'revisión'])
 with (outdir/'ambiguedades.csv').open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.writer(f);w.writerow(['id_anterior','nombre_original','nombre_provisional','motivo']);
  w.writerows([x[:4] for x in audit if x[4]=='revisión'])
 with (outdir/'alias_ambiguos.csv').open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.writer(f);w.writerow(['alias_key','ids_conflictivos']);w.writerows(alias_collisions)
 with (outdir/'catalogo_generico.csv').open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.writer(f);w.writerow(['ingredient_id','nombre_generico','recetas_que_lo_utilizan'])
  frequency=collections.Counter(fid for _,fid in groups)
  w.writerows([(i,name,frequency[i]) for i,name in enumerate(canon,1)])
 with (outdir/'ejemplos_agrupacion.csv').open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.writer(f);w.writerow(['ingrediente','id','variante_original','recetas'])
  for label in ('Papa','Tomate','Cebolla','Ajo','Queso','Pollo','Zanahoria','Sal','Huevo'):
   row=[(i,name) for i,name in enumerate(canon,1) if key(name)==key(label)]
   if not row:continue
   fid=row[0][0]
   variants=collections.Counter(oldname[oldid] for did,oldid,*_ in db.execute('SELECT dish_id,ingredient_id,quantity_text,is_required FROM dish_ingredients') if old_to_new[oldid]==fid)
   for v,n in variants.most_common(30):w.writerow([label,fid,v,n])
 print('Recetas:',len(dishes),'originales',len(recipe_source))
 print('Familias/IDs nuevas:',len(canon),'frente a',len(original_ing))
 print('Relaciones:',len(dish_rows),'agregaciones dentro de receta:',aggregated)
 print('Alias seguros:',len(aliases),'colisiones:',len(alias_collisions),'Pendientes de revisión:',len([x for x in audit if x[4]=='revisión']))
 return len(canon)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--semilla',type=Path,default=Path('manka_seed_normalizado.sql'));p.add_argument('--csv',type=Path,default=Path('main.csv'));p.add_argument('--salida',type=Path,default=Path('.'));a=p.parse_args();run(a.semilla,a.csv,a.salida)
