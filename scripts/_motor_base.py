#!/usr/bin/env python3
"""Convierte SOLO main.csv a la estructura SQL de Manka, con limpieza integrada.

Requiere Python >=3.9. No requiere paquetes externos ni lee el viejo data.sql.
Uso:
  python convertir_desde_cero_mejorado.py
  python convertir_desde_cero_mejorado.py --limite 10
  python convertir_desde_cero_mejorado.py --csv main.csv --salida data_limpio.sql

Genera el SQL y tres reportes en el directorio de salida.
Conserva las cuatro tablas básicas y añade alias, etiquetas y fuentes de proteína.
NOTA: agrega la categoría 5 = Otros, para no etiquetar erróneamente carne/mixtos
como Vegetariano. Si tu backend fija solo 4 categorías, deberás adaptarlo o
revisar los registros de 'Otros' antes de importarlo.
"""
from __future__ import annotations
import argparse
import ast
import csv
import re
import tempfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
CATEGORIES = ((1,'Pollo'), (2,'Res'), (3,'Pescado'), (4,'Vegetariano'), (5,'Otros'))
MAX_NAME = 110
MAX_DISH = 255

# Solo sustituciones explícitas: no fusionar ingredientes por similitud difusa.
ALIASES = {
    'jitomate':'Tomate', 'jitomates':'Tomate', 'tomates':'Tomate', 'tomate':'Tomate',
    'to mates':'Tomate','to mates roma':'Tomate', 'tomate roma':'Tomate',
    'tomates roma':'Tomate', 'tomates grandes ciruela':'Tomate',
    'jitomate ciruela':'Tomate','tomate ciruela':'Tomate',
    'papa':'Papa', 'papas':'Papa', 'patatas':'Papa', 'patata':'Papa',
    'papas rojas':'Papa', 'papa roja':'Papa', 'papas amarillas':'Papa',
    'taza de aceite vegetal':'Aceite vegetal', 'huevos quebrados en un tazon':'Huevo', 'aguacate grande':'Palta',
    'aguacate':'Palta', 'aguacates':'Palta', 'paltas':'Palta',
    'cilantro':'Culantro', 'cilantros':'Culantro',
    'huevos':'Huevo', 'huevo':'Huevo', 'claras de huevo':'Clara de huevo',
    'ajos':'Ajo','diente de ajo':'Ajo','dientes de ajo':'Ajo',
    'cebollas':'Cebolla','cebolla':'Cebolla', 'cebollas moradas':'Cebolla roja',
    'cebolla morada':'Cebolla roja','cebolla roja':'Cebolla roja',
    'cebollas blancas':'Cebolla blanca',
    'champiñones':'Champiñón','champinones':'Champiñón',
    'guisantes':'Arveja','guisante':'Arveja','arvejas':'Arveja',
    'chayotes':'Chayote', 'nopales':'Nopal',
    'chiles poblanos':'Chile poblano', 'tomate pequeno roma':'Tomate', 'calabazas':'Calabaza',
    'frijoles':'Frijol','frejoles':'Frijol','frijol':'Frijol',
    'frijoles negros':'Frijol negro','frijol negro':'Frijol negro',
    'garbanzos':'Garbanzo','lentejas':'Lenteja','espinacas':'Espinaca',
    'to rtillas de maiz':'Tortilla de maíz', 'tortillas de maiz':'Tortilla de maíz',
    'tortilla de maiz':'Tortilla de maíz','tortillas':'Tortilla',
    'chiles serranos':'Chile serrano','chile serrano':'Chile serrano',
    'chiles jalapenos':'Chile jalapeño','chile jalapeno':'Chile jalapeño',
    'chiles poblanos':'Chile poblano','chile poblano':'Chile poblano',
    'limones':'Limón', 'limon':'Limón', 'zanahorias':'Zanahoria',
    'manzanas':'Manzana', 'leches':'Leche',
    'sal fina':'Sal','sal':'Sal','pimienta negra molida':'Pimienta negra',
    'pimienta':'Pimienta','queso fresco mexicano':'Queso fresco',
    'queso fresco':'Queso fresco','aceite de oliva virgen extra':'Aceite de oliva',
    'aceite de oliva extra virgen':'Aceite de oliva',
    'caldo de pollo':'Caldo de pollo','pechugas de pollo':'Pechuga de pollo',
    'piernas de pollo':'Pierna de pollo',
}

STOP_EXACT = {
    'pero firme','onzas','onzas)','gramos','gramos)','aproximadamente',
    'opcional','opcionales','para decorar','para servir','para acompanar',
    'de preferencia','cantidad necesaria','al gusto','a gusto','algunas',
    'o al gusto', 'ver instrucciones','instrucciones', 'preparacion',
    'ingredientes','guarniciones opcionales', 'guarnicion opcional',
}
TOOLS = re.compile(r'\b(?:palillos? de madera|papel(?: de)? aluminio|papel encerado|servilletas? de papel|molde para|cuchillos? de|recipiente|bolsa de plastico)\b', re.I)
LEADING_NONFOOD = re.compile(r'^(?:para (?:decorar|servir|acompañar)|ingredientes para|guarniciones?|alrededor de|pero\b|que\b|opcional(?:mente)?\b|o bien\b)', re.I)
DESCRIPTOR = re.compile(
    r'\b(?:finamente\s+)?(?:picad[ao]s?|picadit[ao]s?|cortad[ao]s?|trocead[ao]s?|'
    r'rallad[ao]s?|pelad[ao]s?|lavad[ao]s?|limpiad[ao]s?|desmenuzad[ao]s?|'
    r'deshebrad[ao]s?|partid[ao]s?|cocid[ao]s?|hervid[ao]s?|machacad[ao]s?|quebrad[ao]s?|asad[ao]s?|'
    r'molidos?|reci[eé]n\s+molid[ao]s?|previamente|'
    r'para\s+(?:fre[íi]r|servir|decorar|acompa[ñn]ar|preparar|dar)|'
    r'de\s+tama[ñn]o|en\s+(?:cubitos?|cubos?|rodajas?|tiras?|trozos?|rebanadas?)|'
    r'sin\s+(?:semillas?|piel|c[aá]scara)|opcional(?:es)?|al\s+gusto|'
    r'bien\s+(?:limpi[ao]s?|picad[ao]s?))\b', re.I)
# Longitudes de cantidades y unidades separadas sin perder el nombre.
NUM = r'(?:\d+(?:[.,]\d+)?(?:/\d+|\s+(?:\d+/\d+|[¼½¾⅓⅔⅛⅜⅝⅞]))?|[¼½¾⅓⅔⅛⅜⅝⅞]|unos|unas|una|un|medio|media)'
UNIT = (r'(?:kilogramos?|kilos?|kg|gramos?|grs?\.?|g\b|mililitros?|ml|litros?|l\b|'
        r'onzas?|oz\.?|tazas?|cucharadas?|cucharaditas?|cdas?\.?|cdtas?\.?|'
        r'pizcas?|dientes?|ramas?|ramitas?|hojas?|unidad(?:es)?|piezas?|filetes?|'
        r'latas?|vasos?|porciones?|rebanadas?|paquetes?|puñados?|tallos?|manojos?|'
        r'chorros?|cabezas?|sobres?|barras?)')
HEAD_NUMBER = re.compile(rf'^(?P<num>{NUM}(?:\s*(?:-|a|o|ó)\s*{NUM})?)(?=\s|$)\s*', re.I)
HEAD_UNIT = re.compile(rf'^(?P<unit>{UNIT})(?=\s|$|[.,])\s*', re.I)


# Priorizamos el nombre y los ingredientes, no el texto narrativo de los pasos.
PROTEINS = {
    1: {'pollo','gallina','pavo','pechuga de pollo','ala de pollo','pierna de pollo','muslo de pollo'},
    2: {'res','ternera','vaca','bistec','carne de res','carne molida de res','higado de res'},
    3: {'pescado','atun','salmon','merluza','bacalao','sardina','trucha','tilapia',
        'calamar','camaron','camarones','langostinos','langostino','marisco','mariscos','pulpo','gamba','gambas','almeja','mejillon'},
    5: {'cerdo','puerco','cochino','jamon','tocino','chorizo','panceta','cordero',
        'salchicha','salchichon','jamon serrano','longaniza','carne de cerdo','carne de cordero'},
}


def norm(s: str) -> str:
    s = unicodedata.normalize('NFKD', (s or '').casefold())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]+', ' ', s)).strip()


def clean(s: str) -> str:
    s = unicodedata.normalize('NFC', (s or '').replace('\xa0',' ').replace('\x00',' '))
    s = re.sub(r'\s+', ' ', s)
    return s.strip(' \t\n,;:.-*')


def sql_str(s: str) -> str:
    return "'" + (s or '').replace('\x00',' ').replace("'", "''") + "'"


def parsed_list(s: str):
    s = (s or '').strip()
    if s.startswith('[') and s.endswith(']'):
        try:
            value = ast.literal_eval(s)
            if isinstance(value, (list, tuple)):
                return [str(x) for x in value]
        except (ValueError, SyntaxError):
            pass
    return None


def split_ingredients(raw: str):
    items = parsed_list(raw)
    if items is not None:
        return [(clean(s),False) for s in items if clean(s)]
    # Divide solo fuera de paréntesis; evita 'tomate (aprox. 3,5 onzas)' roto.
    pieces, buffer, depth = [], [], 0
    for c in raw or '':
        if c in '([': depth += 1
        elif c in ')]': depth = max(0, depth-1)
        if c in ',;\n' and depth == 0:
            part = clean(''.join(buffer)); buffer=[]
            if part: pieces.append(part)
        else: buffer.append(c)
    part = clean(''.join(buffer))
    if part: pieces.append(part)
    # Continuaciones frecuentes, por ejemplo 'aguacate maduro, pero firme'.
    merged=[]
    for piece in pieces:
        if merged and re.match(r'^(?:pero\b|que\b|si\b|sin\b|opcional\b|o bien\b|de tamaño\b|para (?:decorar|servir|acompañar)\b)', piece, re.I):
            merged[-1] += ', ' + piece
        else: merged.append(piece)
    return [(s,True) for s in merged]


def normal_ingredient(raw: str):
    """Return list[(name, quantity, required, flags)] or None for explicit noise."""
    part = clean(raw).replace('to rtillas','tortillas').replace('To rtillas','Tortillas').replace('to mates','tomates').replace('To mates','Tomates')
    part = part.replace(' y/o ', ' o ')
    if not part or norm(part) in STOP_EXACT or LEADING_NONFOOD.search(part) or TOOLS.search(part):
        return None
    flags=[]
    optional = bool(re.search(r'\bopcional(?:es)?\b|\ba elecci[oó]n\b', part, re.I))
    quantity='no especificada'
    if re.search(r'\bal gusto\b', part, re.I): quantity='al gusto'
    m = HEAD_NUMBER.match(part)
    if m:
        qty_num=clean(m.group('num'))
        rest=part[m.end():].strip()
        # "⅔ de taza", "½ taza" y "1 ½ taza".
        rest_without_de = re.sub(r'^de\s+', '', rest, flags=re.I)
        unit_match=HEAD_UNIT.match(rest_without_de)
        if unit_match:
            unit=clean(unit_match.group('unit'))
            rest=rest_without_de[unit_match.end():].strip()
            if re.match(r'^soper[oa]s?\b',rest,re.I):
                u=re.match(r'^soper[oa]s?\b',rest,re.I)
                unit+=' '+u.group(0);rest=rest[u.end():].strip()
            quantity=clean(qty_num+' '+unit)
        else:
            quantity=qty_num+' unidades'
            rest=rest_without_de
        # El complemento de la unidad puede empezar por "de/del".
        rest=re.sub(r'^(?:de|del)\s+', '',rest, flags=re.I)
        # Algunas filas indican doble medida: "8 oz. ½ paquete de espagueti".
        # Elegimos la segunda que describe el alimento y registramos el cambio.
        second=HEAD_NUMBER.match(rest)
        if second:
            maybe=rest[second.end():].strip()
            mu=HEAD_UNIT.match(maybe)
            if mu:
                flags.append('dos cantidades; usar la segunda y revisar')
                quantity=clean(second.group('num')+' '+mu.group('unit'))
                rest=re.sub(r'^(?:de|del)\s+','',maybe[mu.end():].strip(),flags=re.I)
        # Cantidades como '⅓ de una cebolla': la segunda palabra no es el ingrediente.
        part=re.sub(r'^(?:una|un)\s+', '', rest, flags=re.I) if qty_num in '¼½¾⅓⅔⅛⅜⅝⅞' else rest
    part=re.sub(r'(?i)al gusto\s*guarniciones.*$', 'al gusto', part)
    part=re.sub(r',?\s*pero\s+firme\b.*$', '', part,flags=re.I)
    part = re.sub(r'\([^)]*\)', ' ', part)
    part = re.sub(r'[\*~]+\s*\d*(?:[.,]\d+)?\s*(?:g|gr|ml)?\.?', ' ', part)
    part = clean(part)
    if not part: return None
    # Dividir solo expresiones inequívocas de DOS ingredientes.
    if norm(part) in ('sal y pimienta al gusto','sal y pimienta','pimienta y sal','pimienta y sal al gusto'):
        return [(name, 'al gusto' if quantity=='no especificada' else quantity, not optional, []) for name in ('Sal','Pimienta')]
    # Alternativas distintas son ambiguas: se usa primera y se reporta.
    split_alt = re.split(r'\s+(?:o|ó)\s+', part, maxsplit=1, flags=re.I)
    if len(split_alt)==2:
        part=split_alt[0]
        flags.append('alternativa omitida: '+split_alt[1][:90])
    # Extraer modos de preparación sin quitar tipos: "aceite de oliva" permanece.
    part = DESCRIPTOR.split(part, maxsplit=1)[0]
    part = re.sub(r'\b(?:aproximadamente|alrededor de)\b.*$', '', part,flags=re.I)
    part = re.sub(r'\b(?:grandes?|pequeñ[oa]s?|median[oa]s?|frescos?|frescas?|enteros?|enteras?|calientes?|fr[ií]os?|maduros?|maduras?)\s*$', '', part,flags=re.I)
    part = re.sub(r'\b(?:grande|mediano|pequeño)\s+(?:maduro|firme)\s*$', '', part,flags=re.I)
    part = re.sub(r'\s+\d+(?:[.,]\d+)?\s*(?:oz|onzas?|grs?|gramos?|g|ml|kilogramos?)\.?\s*$', '',part,flags=re.I)
    part = re.sub(r'^(?:de|del|los|las|el|la)\s+','',part,flags=re.I)
    part = re.sub(r'(?i)\b(?:sal y pimienta)\s*al gusto.*$', 'sal y pimienta al gusto', part)
    part = clean(part)
    if not part or norm(part) in STOP_EXACT or len(part)<2: return None
    # Palabras evidentes de instrucción no deben convertirse en ingredientes.
    if norm(part).startswith(('ver instrucciones', 'consulte la receta', 'agregue ', 'sazonar ', 'para decorar')):
        return None
    # Evitar nombres rotos/segmentos narrativos en el catálogo SQL.
    if len(part)>MAX_NAME or len(part.split())>11 or any(ch in part for ch in '[]{}'):
        return ('REVISAR', quantity, not optional, ['fragmento largo o mal formado: '+raw[:130]])
    key = norm(part)
    alias = ALIASES.get(key)
    if alias:
        return [(alias,quantity,not optional,flags)]
    # Variantes generales inequívocas: singulariza sustantivos frecuentes.
    first_word_map = {'tomates':'Tomate','jitomates':'Tomate', 'papas':'Papa','patatas':'Papa',
        'huevos':'Huevo','chiles':'Chile','cebollas':'Cebolla','limones':'Limón',
        'zanahorias':'Zanahoria', 'dientes':'Diente','ramitas':'Ramita', 'pepinos':'Pepino',
        'pimientos':'Pimiento', 'tortillas':'Tortilla', 'platanos':'Plátano',
        'champiñones':'Champiñón','setas':'Seta','naranjas':'Naranja',
        'manzanas':'Manzana','frijoles':'Frijol','garbanzos':'Garbanzo',
        'guisantes':'Arveja','chayotes':'Chayote', 'nopales':'Nopal',
    'chiles poblanos':'Chile poblano', 'tomate pequeno roma':'Tomate', 'calabazas':'Calabaza', 'camarones':'Camarón', 'langostinos':'Langostino'}
    words=part.split()
    if words:
        rep=first_word_map.get(norm(words[0]))
        if rep: part=' '.join([rep] + words[1:])
    # Eliminar palabras que no designan ingrediente al final.
    part=clean(part)
    if not part: return None
    if re.search(r'\b(?: y | o )\b',part,re.I):flags.append('posible combinación de ingredientes')
    if len(part.split())>=6:flags.append('nombre largo; revisar')
    if quantity=='no especificada': flags.append('cantidad no indicada')
    # normalizar capitalización y acentos de los nombres conocidos por clave.
    key=norm(part)
    name=ALIASES.get(key,part[:1].upper()+part[1:])
    return [(name,quantity,not optional,flags)]


def parse_minutes(raw: str):
    s=clean(raw)
    if not s: return 45,True
    parts=s.split(':')
    if len(parts)==2 and all(p.isdigit() for p in parts): return max(1,int(parts[0])*60+int(parts[1])),False
    if len(parts)==3 and all(p.isdigit() for p in parts): return max(1,int(parts[0])*60+int(parts[1])+int(parts[2])//60),False
    x=re.search(r'\d+',s)
    return (int(x.group()),False) if x else (45,True)


def parse_difficulty(raw: str):
    n=norm(raw)
    if 'muy alta' in n or 'alta' in n or 'dificil' in n: return 'DIFICIL',False
    if 'media' in n: return 'MEDIA',False
    if 'baja' in n or 'facil' in n: return 'FACIL',False
    return 'FACIL',True


def parse_popularity(raw: str):
    m=re.search(r'valoraci[oó]n\s*:\s*(\d+(?:[.,]\d+)?)', raw or '',re.I)
    if not m: return 80,True
    return min(100,max(0,round(float(m.group(1).replace(',','.'))*20))),False


def category_of(row: dict, ingredients: list[str]):
    title=norm(row.get('Nombre','')); cat=norm(row.get('Categoria',''))
    ingredient_words=' '.join(norm(v) for v in ingredients)
    def hits(text, terms):
        return any(re.search(r'(?<![a-z])'+re.escape(t)+r'(?![a-z])',text) for t in terms)
    for typ in (1,2,3,5):
        if hits(title, PROTEINS[typ]):return typ, 'identificada por nombre'
    # En ingredientes, "caldo de pollo" no basta para decidir si plato es pollo.
    name_ingredients = ' '.join(' '+norm(x)+' ' for x in ingredients if not norm(x).startswith('caldo de '))
    matching = [c for c in (1,2,3,5) if hits(name_ingredients,PROTEINS[c])]
    if len(matching)==1:return matching[0], 'identificada por ingredientes'
    if len(matching)>1:return 5, 'REVISAR: proteínas mixtas'
    if hits(ingredient_words,{'caldo de pollo','caldo de res','caldo de pescado'}):
        return 5,'REVISAR: contiene caldo de origen animal'
    if 'recomendada para vegetarianos' in cat or 'recomendada para veganos' in cat or 'vegetarianos' in cat or 'veganos' in cat:
        return 4,'etiqueta vegetariana/vegana del CSV'
    return 5,'REVISAR: categoría no determinable'


def prep_text(raw: str):
    steps=parsed_list(raw)
    if steps is not None:return '\n'.join(clean(x) for x in steps if clean(x))
    return (raw or '').replace('\x00',' ').strip()


def emit(file, table, columns, buffer):
    if not buffer: return
    file.write('INSERT INTO '+table+' ('+columns+') VALUES\n')
    file.write(',\n'.join(buffer))
    file.write(';\n\n')
    buffer.clear()


# Padres explícitos: no agrupar por similitud; solo variedades inequívocas.
PARENT_MAP = {
    'pechuga de pollo': 'Pollo', 'pierna de pollo': 'Pollo',
    'muslo de pollo': 'Pollo', 'ala de pollo': 'Pollo',
    'cebolla roja': 'Cebolla', 'cebolla blanca': 'Cebolla',
    'clara de huevo': 'Huevo', 'yema de huevo': 'Huevo',
    'chile poblano': 'Chile', 'chile serrano': 'Chile',
    'chile jalapeno': 'Chile', 'chile guajillo': 'Chile',
    'frijol negro': 'Frijol',
    'aceite vegetal': 'Aceite', 'aceite de oliva': 'Aceite',
}
SOURCE_NAMES = ('Pollo', 'Res', 'Pescado/Mariscos', 'Cerdo', 'Otras carnes')
# Estas fuentes son informativas, no etiquetas médicas ni certificación vegetariana.
PROTEIN_SOURCE_TERMS = {
    'Pollo': PROTEINS[1],
    'Res': PROTEINS[2],
    'Pescado/Mariscos': PROTEINS[3],
    'Cerdo': {'cerdo','puerco','cochino','jamon','tocino','chorizo','panceta','longaniza'},
    'Otras carnes': {'cordero','conejo','pato'},
}


def detect_sources(title: str, ingredients: list[str]):
    words = [norm(x) for x in ingredients if not norm(x).startswith(('caldo de ','sabor a '))]
    searchable = ' ' + norm(title) + ' ' + ' '.join(words) + ' '
    result = []
    for label, terms in PROTEIN_SOURCE_TERMS.items():
        if any(re.search(r'(?<![a-z])' + re.escape(term) + r'(?![a-z])', searchable)
               for term in terms):
            result.append(label)
    return result


def csv_meta(row):
    country = clean(row.get('Pais',''))[:100]
    meal_type = clean(row.get('Tiempo',''))[:120]
    url = clean(row.get('URL',''))[:1000]
    servings = re.search(r'\d+', row.get('Comensales','') or '')
    servings = int(servings.group()) if servings and 0<int(servings.group())<1000 else None
    rating = re.search(r'valoraci[oó]n\s*:\s*(\d+(?:[.,]\d+)?)',row.get('Valoracion y Votos',''),re.I)
    votes = re.search(r'votos?\s*:\s*(\d+)',row.get('Valoracion y Votos',''),re.I)
    average = float(rating.group(1).replace(',','.')) if rating else None
    count = int(votes.group(1)) if votes else None
    if average is not None and not (0 <= average <= 5): average=None
    return country,meal_type,url,servings,average,count


def sql_nullable(value):
    if value is None: return 'NULL'
    if isinstance(value,(int,float)): return str(value)
    return sql_str(str(value))


def run():
    ap=argparse.ArgumentParser(description='Genera SQL desde main.csv con limpieza automática y auditoría.')
    ap.add_argument('--csv',type=Path,default=BASE/'main.csv')
    ap.add_argument('--salida',type=Path,default=BASE/'data_desde_cero_limpio.sql')
    ap.add_argument('--limite',type=int)
    a=ap.parse_args()
    if not a.csv.exists():ap.error('Falta main.csv: '+str(a.csv))
    a.salida.parent.mkdir(parents=True,exist_ok=True)
    catalog={}; examples={}; usages=Counter(); flags={}; recipes=[]; dropped=[]
    tag_ids={}; tag_links=[]; source_links=[]; seen_tags=set()
    categories=Counter(); fallbacks=Counter(); counter=Counter(); seen_ids=set(); n_dishes=0;n_links=0
    temp=a.salida.parent
    with tempfile.TemporaryDirectory() as td:
        dishes_tmp=Path(td)/'dishes.sql'; links_tmp=Path(td)/'links.sql'
        with a.csv.open(encoding='utf-8-sig',newline='') as fin, dishes_tmp.open('w',encoding='utf-8') as df,links_tmp.open('w',encoding='utf-8') as lf:
            reader=csv.DictReader(fin)
            fields={'Id','Nombre','Ingredientes','Pasos','Duracion','Categoria','Dificultad','Valoracion y Votos'}
            missing=fields-set(reader.fieldnames or [])
            if missing:ap.error('CSV sin columnas requeridas: '+', '.join(sorted(missing)))
            dbuf=[]; lbuf=[]
            for csv_line,row in enumerate(reader,2):
                source_id=clean(row.get('Id',''));title=clean(row.get('Nombre',''))
                if not title or not source_id or source_id in seen_ids:raise ValueError(f'CSV línea {csv_line}: Id duplicado/vacío o título vacío')
                seen_ids.add(source_id);n_dishes+=1
                minute,est_min=parse_minutes(row['Duracion']); diff,est_diff=parse_difficulty(row['Dificultad']);score,est_score=parse_popularity(row['Valoracion y Votos'])
                # No inventar duración, dificultad ni valoración cuando el CSV no las proporciona.
                if est_min: minute=None
                if est_diff: diff=None
                if est_score: score=50
                country,meal_type,url,servings,rating_average,rating_votes=csv_meta(row)
                parsed=[]; entries=[]
                for raw,free in split_ingredients(row['Ingredientes']):
                    value=normal_ingredient(raw)
                    if value is None:
                        dropped.append((source_id,n_dishes,title,raw,'ruido/utensilio o fragmento vacío'))
                        counter['dropped_noise']+=1
                        continue
                    if isinstance(value,tuple) and value[0]=='REVISAR':
                        dropped.append((source_id,n_dishes,title,raw,value[3][0]))
                        counter['dropped_ambiguous']+=1
                        continue
                    for name,qty,required,alerts in value:
                        entries.append((name,qty,required,alerts,raw,free))
                        parsed.append(name)
                cat,cat_reason=category_of(row,parsed)
                categories[cat]+=1
                if est_min:fallbacks['duracion']+=1
                if est_diff:fallbacks['dificultad']+=1
                if est_score:fallbacks['popularidad']+=1
                if cat==5:fallbacks['categoria_otros']+=1
                preparation=prep_text(row.get('Pasos','')) or 'Preparación no disponible en el CSV'
                protein_sources=detect_sources(title,parsed)
                for source in protein_sources:
                    source_links.append((n_dishes, SOURCE_NAMES.index(source)+1))
                # Etiquetas del CSV son informativas: no se interpretan como dieta certificada.
                for tag_type, tag_name in [('SOURCE_CATEGORY', row.get('Categoria','')),
                                           ('MEAL', row.get('Tiempo',''))]:
                    tag_name=clean(tag_name)[:120]
                    if not tag_name: continue
                    key=(tag_type,norm(tag_name))
                    if key not in tag_ids: tag_ids[key]=(len(tag_ids)+1,tag_type,tag_name)
                    tag_links.append((n_dishes,tag_ids[key][0]))
                for raw_tag in (row.get('Valor nutricional','') or '').split(','):
                    tag_name=clean(raw_tag)[:120]
                    if not tag_name: continue
                    key=('NUTRITION_SOURCE',norm(tag_name))
                    if key not in tag_ids: tag_ids[key]=(len(tag_ids)+1,'NUTRITION_SOURCE',tag_name)
                    tag_links.append((n_dishes,tag_ids[key][0]))
                dbuf.append('('+', '.join(map(str,[n_dishes,sql_str(title[:MAX_DISH]),
                    sql_nullable(minute),sql_nullable(diff),str(score),sql_str(preparation),str(cat),
                    sql_nullable(int(source_id)),sql_nullable(url),sql_nullable(country),sql_nullable(servings),
                    sql_nullable(meal_type),sql_nullable(rating_average),sql_nullable(rating_votes),
                    'false','false']))+')')
                if len(dbuf)>=150:emit(df,'dishes','id, name, preparation_minutes, difficulty, popularity_score, preparation, protein_category_id, source_id, source_url, country, servings, meal_type, rating_average, rating_votes, duration_estimated, difficulty_estimated',dbuf)
                # Un ingrediente canónico ocupa una sola fila por receta.
                # Si figura varias veces (por ejemplo salsa y relleno), NO
                # perdemos la segunda cantidad: se conserva en quantity_text.
                merged={}
                for name,qty,required,alerts,raw,free in entries:
                    key=norm(name)
                    if key not in catalog:
                        iid=len(catalog)+1; catalog[key]=(iid,name)
                        examples[key]=raw
                    iid=catalog[key][0]
                    if alerts: flags.setdefault(key,set()).update(alerts)
                    if free: flags.setdefault(key,set()).add('texto libre (sin lista estructurada)')
                    if iid not in merged:
                        merged[iid]={'key':key,'qty':[],'required':bool(required)}
                    else:
                        counter['duplicate_link_merged']+=1
                    merged[iid]['required'] |= bool(required)
                    if qty and qty!='no especificada' and qty not in merged[iid]['qty']:
                        merged[iid]['qty'].append(qty)
                for iid,record in merged.items():
                    usages[record['key']]+=1
                    quantity=' + '.join(record['qty']) or 'no especificada'
                    if len(quantity)>100:
                        flags.setdefault(record['key'],set()).add('cantidad combinada truncada; revisar')
                    n_links+=1
                    lbuf.append(f"({n_links}, {n_dishes}, {iid}, {sql_str(quantity[:100])}, {str(record['required']).lower()})")
                    if len(lbuf)>=700:emit(lf,'dish_ingredients','id, dish_id, ingredient_id, quantity_text, is_required',lbuf)
                seen=set(merged)
                recipes.append((source_id,n_dishes,title,cat,cat_reason,int(est_min),int(est_diff),int(est_score),len(entries),len(seen)))
                if a.limite is not None and n_dishes>=a.limite:break
            emit(df,'dishes','id, name, preparation_minutes, difficulty, popularity_score, preparation, protein_category_id, source_id, source_url, country, servings, meal_type, rating_average, rating_votes, duration_estimated, difficulty_estimated',dbuf)
            emit(lf,'dish_ingredients','id, dish_id, ingredient_id, quantity_text, is_required',lbuf)
        with a.salida.open('w',encoding='utf-8',newline='\n') as out:
            out.write('-- MANKA: seed generado SOLO desde main.csv; sin copiar el data.sql anterior.\n')
            out.write('-- Limpieza automatizada: normaliza nombres, cantidades y duplicados exactos/alias seguros.\n')
            out.write('-- La categoría 5=Otros evita clasificar carne desconocida como vegetariana.\n')
            out.write('-- ATENCIÓN: comprobar compatibilidad de Otros con el backend y el esquema real.\n')
            out.write('-- SQL de datos: exige tablas ya creadas y base de prueba vacía.\n'
                      '-- IMPORTACIÓN ÚNICA: los errores deben detener el script; no se usa ON CONFLICT DO NOTHING.\n\n')
            emit(out,'protein_categories','id, name',[f'({i}, {sql_str(n)})' for i,n in CATEGORIES])
            buf=[]
            parent_updates=[]
            # Los padres ausentes se agregan al catálogo para conservar las relaciones.
            for old_key, parent_name in PARENT_MAP.items():
                if old_key in catalog and norm(parent_name) not in catalog:
                    catalog[norm(parent_name)] = (len(catalog)+1,parent_name)
            for key,(iid,name) in sorted(catalog.items(), key=lambda kv:kv[1][0]):
                parent_name=PARENT_MAP.get(key)
                parent_id=catalog[norm(parent_name)][0] if parent_name else None
                buf.append(f'({iid}, {sql_str(name)}, NULL)')
                if parent_id is not None: parent_updates.append((iid,parent_id))
                if len(buf)>=400:emit(out,'ingredients','id, name, parent_id',buf)
            emit(out,'ingredients','id, name, parent_id',buf)
            # Actualizar parent_id cuando TODOS los ingredientes ya existen: respeta FK incluso por lotes.
            for child_id,parent_id in parent_updates:
                out.write(f'UPDATE ingredients SET parent_id = {parent_id} WHERE id = {child_id};\n')
            out.write('\n')
            # Tabla de alias, vinculando variantes explícitas al ID canónico.
            aliases=[]; alias_seen={}
            for raw_alias,canonical in sorted(ALIASES.items()):
                key=norm(raw_alias); canonical_key=norm(canonical)
                if canonical_key not in catalog or key == canonical_key: continue
                if key in catalog and key != canonical_key: continue
                if key in alias_seen: continue
                alias_seen[key]=canonical_key
                aliases.append((len(aliases)+1,raw_alias,key,catalog[canonical_key][0]))
            buf=[]
            for id_,raw,key,canonical_id in aliases:
                buf.append(f'({id_}, {sql_str(raw)}, {sql_str(key)}, {canonical_id})')
                if len(buf)>=300: emit(out,'ingredient_aliases','id, alias, alias_key, ingredient_id',buf)
            emit(out,'ingredient_aliases','id, alias, alias_key, ingredient_id',buf)
            emit(out,'protein_sources','id, name', [f'({i+1}, {sql_str(v)})' for i,v in enumerate(SOURCE_NAMES)])
            buf=[]
            for _,(tid,typ,name) in sorted(tag_ids.items(),key=lambda kv:kv[1][0]):
                buf.append(f'({tid}, {sql_str(name)}, {sql_str(typ)})')
                if len(buf)>=300:emit(out,'tags','id, name, type',buf)
            emit(out,'tags','id, name, type',buf)
            for p in (dishes_tmp,links_tmp):
                with p.open('r',encoding='utf-8') as fh:
                    for line in fh:out.write(line)
            buf=[]
            for dish_id,source_id_ in source_links:
                buf.append(f'({dish_id}, {source_id_})')
                if len(buf)>=700:emit(out,'dish_protein_sources','dish_id, protein_source_id',buf)
            emit(out,'dish_protein_sources','dish_id, protein_source_id',buf)
            buf=[]
            for dish_id,tag_id in dict.fromkeys(tag_links):
                buf.append(f'({dish_id}, {tag_id})')
                if len(buf)>=700:emit(out,'dish_tags','dish_id, tag_id',buf)
            emit(out,'dish_tags','dish_id, tag_id',buf)
            for tbl in ('ingredient_aliases','protein_sources','tags'):
                out.write(f"SELECT setval(pg_get_serial_sequence('{tbl}', 'id'), COALESCE((SELECT MAX(id) FROM {tbl}), 1), true);\n")
            for tbl in ('protein_categories','ingredients','dishes','dish_ingredients'):
                out.write(f"SELECT setval(pg_get_serial_sequence('{tbl}', 'id'), COALESCE((SELECT MAX(id) FROM {tbl}), 1), true);\n")
    root=a.salida.parent
    with (root/'auditoria_ingredientes.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['ingredient_id','nombre_normalizado','recetas','ejemplo_original','observaciones'])
        for key,(id_,name) in sorted(catalog.items(),key=lambda kv:kv[1][0]):
            w.writerow((id_,name,usages[key],examples.get(key,"(padre añadido automáticamente)"),'; '.join(sorted(flags.get(key,set())))))
    with (root/'fragmentos_descartados.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['csv_id','dish_id','receta','fragmento_original','motivo']);w.writerows(dropped)
    with (root/'auditoria_recetas.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['csv_id','dish_id','nombre','protein_category_id','motivo_categoria','duracion_estimada','dificultad_estimada','popularidad_estimada','fragmentos_detectados','ingredientes_conservados']);w.writerows(recipes)
    report=(f'ORIGEN: {a.csv.name} (ningún data.sql antiguo)\n'
            f'Recetas exportadas: {n_dishes}\nIngredientes normalizados distintos: {len(catalog)}\n'
            f'Relaciones: {n_links}; Alias: {len(aliases)}; tags: {len(tag_ids)}; relaciones de proteína: {len(source_links)}\nFragmentos excluidos para no contaminar la tabla: {len(dropped)}\n'
            f'Categorías: {dict(sorted(categories.items()))}\nValores inferidos: {dict(fallbacks)}\n'
            f'Relaciones del mismo ingrediente combinadas dentro de una receta: {counter["duplicate_link_merged"]}\n'
            'Categoría 5 = Otros. REVISAR compatibilidad del backend, no se modifican tablas ni columnas.\n'
            'ATENCIÓN: la limpieza heurística no reemplaza verificación humana.\n'
            'NOTA: el SQL no crea tablas, no se ha probado contra el esquema PostgreSQL de tu backend.\n')
    (root/'RESUMEN_LIMPIEZA.txt').write_text(report,encoding='utf-8')
    print(report)
    print('SQL:',a.salida)



# SEGUNDA CAPA: canonización por ID. No colapsar derivados (salsa, puré,
# concentrado), formatos (en polvo), ni variedades culinarias distintas.
# La identidad es el nombre canónico, NO el texto de la receta.
_NORMAL_ANTERIOR = normal_ingredient

# Nombres de alimentos confirmados y variantes sin pérdida semántica.
CANONICAL_EXACT = {
    'tomate rojo': 'Tomate', 'tomates rojos':'Tomate',
    'tomate roma': 'Tomate', 'tomate saladet':'Tomate',
    'jitomate rojo':'Tomate', 'jitomates rojos':'Tomate',
    'tomate guaje':'Tomate', 'tomate guajes':'Tomate',
    'tomate saladette':'Tomate',
    'tomates cherry':'Tomate cherry', 'jitomates cherry':'Tomate cherry',
    'tomate cereza':'Tomate cherry', 'tomates cereza':'Tomate cherry',
    'tomates verdes': 'Tomate verde', 'tomate verdes':'Tomate verde',
    'tomatillos':'Tomatillo', 'tomatillo':'Tomatillo',
    'cebollas blancas':'Cebolla blanca', 'cebolla blanca':'Cebolla blanca',
    'cebolla morada':'Cebolla roja', 'cebollas moradas':'Cebolla roja',
    'cebolla roja':'Cebolla roja', 'cebollas rojas':'Cebolla roja',
    'cebolla en polvo':'Cebolla en polvo', 'polvo de cebolla':'Cebolla en polvo',
    'ajo en polvo':'Ajo en polvo', 'polvo de ajo':'Ajo en polvo',
    'ajo triturado':'Ajo', 'ajos triturados':'Ajo',
    'ajo chancado':'Ajo', 'ajos chancados':'Ajo',
    'ajo machacado':'Ajo', 'ajos machacados':'Ajo',
    'ajo rallado':'Ajo', 'ajo finamente picado':'Ajo',
    'agua suficiente':'Agua', 'agua':'Agua',
    'tomates':'Tomate','tomate':'Tomate', 'jitomate':'Tomate', 'jitomates':'Tomate',
    'papa':'Papa', 'papas':'Papa', 'patata':'Papa', 'patatas':'Papa',
    'papa blanca':'Papa blanca', 'papas blancas':'Papa blanca',
    'papa amarilla':'Papa amarilla', 'papas amarillas':'Papa amarilla',
    'papa seca':'Papa seca', 'papas secas':'Papa seca',
    'cebolla':'Cebolla', 'cebollas':'Cebolla',
    'pimienta negra molida':'Pimienta negra',
    'aceite de oliva virgen':'Aceite de oliva',
    'aceite de oliva suave':'Aceite de oliva',
    'aceite de oliva virgen extra':'Aceite de oliva',
    'aceite de oliva extra virgen':'Aceite de oliva',
    'aceite vegetal':'Aceite vegetal',
    'pechugas de pollo':'Pechuga de pollo',
    'pechuga de pollo':'Pechuga de pollo',
    'muslos de pollo':'Muslo de pollo',
    'piernas de pollo':'Pierna de pollo',
    'champiñones':'Champiñón', 'champinon':'Champiñón',
    'cilantro':'Culantro', 'culantro':'Culantro',
    'aguacate':'Palta', 'palta':'Palta',
}

# Expresiones que indican solamente forma, cortes o modo de preparación.
CUT_PREFIX = re.compile(
    r'^(?:rodajas?|rebanadas?|trozos?|cubos?|dados?|tiritas?|tiras?|gajos?|'
    r'pedazos?|láminas?|laminas?|ralladura|ramitas?|dientes?|manojitos?|'
    r'cucharadas?|cucharaditas?|tazas?)'
    r'(?:\s+(?:finas?|gruesas?|pequeñas?|pequenos?|grandes?))?\s+de\s+', re.I)
EXTRA_ENDING = re.compile(
    r'\s+(?:grandes?|pequeñ[oa]s?|medianos?|medianas?|frescos?|frescas?|'
    r'maduros?|maduras?|enteros?|enteras?|sin piel|sin semillas|'
    r'pelados?|peladas?|picados?|picadas?|rallados?|ralladas?|'
    r'triturados?|trituradas?|cortados?|cortadas?|limpios?|limpias?|'
    r'en cubos?|en rodajas?|en trozos?|finamente|para cocinar|para freir)\b.*$', re.I)

# Orden de especificidad: antes de 'Tomate' verificar tipos diferentes.
FOOD_PATTERNS = [
    (re.compile(r'^(?:tomatillos?|miltomates?)\b',re.I),'Tomatillo'),
    (re.compile(r'^(?:tomates?|jitomates?)\s+(?:cherry|cereza)\b',re.I),'Tomate cherry'),
    (re.compile(r'^(?:tomates?|jitomates?)\s+verdes?\b',re.I),'Tomate verde'),
    (re.compile(r'^(?:tomates?|jitomates?)\s+(?:rojos?|roma|saladet|saladette|guajes?|ciruela)\b',re.I),'Tomate'),
    (re.compile(r'^(?:tomates?|jitomates?)\b(?!(?:\s+de\s+arbol))',re.I),'Tomate'),
    (re.compile(r'^(?:cebollas?)\s+(?:blancas?)\b',re.I),'Cebolla blanca'),
    (re.compile(r'^(?:cebollas?)\s+(?:rojas?|moradas?)\b',re.I),'Cebolla roja'),
    (re.compile(r'^(?:cebollas?)\b',re.I),'Cebolla'),
    (re.compile(r'^(?:ajos?)\s+en\s+polvo\b',re.I),'Ajo en polvo'),
    (re.compile(r'^(?:ajos?)\b',re.I),'Ajo'),
    (re.compile(r'^pechugas?\s+de\s+pollo\b',re.I),'Pechuga de pollo'),
    (re.compile(r'^muslos?\s+de\s+pollo\b',re.I),'Muslo de pollo'),
    (re.compile(r'^piernas?\s+de\s+pollo\b',re.I),'Pierna de pollo'),
    (re.compile(r'^(?:aceite\s+de\s+oliva)(?:\s+(?:virgen|extra|suave))?\b',re.I),'Aceite de oliva'),
    (re.compile(r'^(?:aceite\s+vegetal)\b',re.I),'Aceite vegetal'),
]

# Sólo aplicar las reglas para nombres culinarios claramente identificables.
# Los nombres ambiguos se conservan y aparecen en auditoria_ingredientes.csv.
def canonicalize_name(name: str, raw: str) -> str:
    before = clean(name)
    s = before
    for _ in range(2):
        changed = CUT_PREFIX.sub('',s).strip()
        if changed==s:break
        s=changed
    s = re.sub(r'^\s*(?:unos?|unas?|algunas?)\s+', '', s, flags=re.I)
    s = re.sub(r'^(?:los|las|el|la|de|del)\s+', '',s,flags=re.I)
    # Importante: 'salsa de tomate', 'pasta de tomate', 'tomate en conserva' y
    # 'cebolla en polvo' NO deben reducirse a sus ingredientes frescos.
    protected = re.match(r'^(?:salsa|pasta|pure|puré|concentrado|jugo|zumo|'
                         r'caldo|consome|consomé|sopa|crema|harina|polvo|semillas|'
                         r'aceite|vinagre|mermelada|dulce)\s+de\b',s,re.I)
    if protected and not norm(s).startswith(('aceite de oliva','aceite de girasol','aceite de maiz')):
        return before
    key=norm(s)
    exact=CANONICAL_EXACT.get(key)
    if exact:return exact
    short=EXTRA_ENDING.sub('',s).strip()
    if short and norm(short) in CANONICAL_EXACT:return CANONICAL_EXACT[norm(short)]
    for pattern,canonical in FOOD_PATTERNS:
        match=pattern.match(s)
        if match:
            tail=s[match.end():].strip(' ,-')
            # Solo colapsar si no hay un sustantivo u otra preparación en la cola.
            if not tail or (not re.search(r'\b(?:con|en|para|de|y|o|salsa|pasta|pur[eé]|concentrado|'
                                       r'seco|secos|secas|deshidratado|deshidratada|granulado|granulada|'
                                       r'caramelizado|caramelizada|frito|frita|triturado|triturada|conserva|'
                                       r'polvo|aceite|chile|cereza|cherry|verde)\b',tail,re.I)
                             and len(tail.split())<=5):
                return canonical
    return before


def normal_ingredient(raw: str):
    # Convertir fracciones pegadas a enteros: 1½ -> 1 ½.
    corrected=re.sub(r'^(\d+)([¼½¾⅓⅔⅛⅜⅝⅞])',r'\1 \2',raw.strip())
    if norm(corrected) in {'para el vaso','para el relleno','para la salsa','para decorar','para 4 personas'}:
        return None
    parsed=_NORMAL_ANTERIOR(corrected)
    if parsed is None or isinstance(parsed,tuple):return parsed
    result=[]
    for name,qty,required,alerts in parsed:
        new_name=canonicalize_name(name,raw)
        if norm(new_name)!=norm(name):alerts=[*alerts,'ID canónico: '+name+' -> '+new_name]
        result.append((new_name,qty,required,alerts))
    return result

# Algunas variedades se mantienen diferentes pero comparten padre.
PARENT_MAP.update({'tomate cherry':'Tomate', 'papa blanca':'Papa', 'papa amarilla':'Papa',
                   'pimienta negra':'Pimienta'})
# Los alias textuales se registran para consultas del backend.
for _alias,_canon in CANONICAL_EXACT.items():
    if norm(_alias)!=norm(_canon):ALIASES.setdefault(_alias,_canon)



# ===== TERCERA CAPA: normalización GLOBAL de todo el vocabulario =====
# Se aplica a CADA ingrediente, no a una lista corta de alimentos.
# Sólo se fusionan equivalencias de alta confianza. Se guardan las variantes
# como ingredient_aliases para búsquedas, y se auditan las no resueltas.
import sys

VOCABULARIO = Counter()
CAMBIOS_GLOBALES = Counter()
EJEMPLOS_CAMBIOS = {}
REVISIONES = Counter()

# Sinónimos de identidad culinaria habitual. Los derivados siguen separados.
SINONIMOS_SEGUROS = {
    'frutilla':'Fresa', 'frutillas':'Fresa',
    'fresas':'Fresa', 'fresa':'Fresa',
    'patatas':'Papa','patata':'Papa','papas':'Papa','papa':'Papa',
    'aguacates':'Palta','aguacate':'Palta',
    'cilantro fresco':'Culantro','cilantro':'Culantro',
    'perejiles':'Perejil', 'perejil fresco':'Perejil',
    'cebollines':'Cebollín','cebollino':'Cebollín',
    'ejote':'Vainita','ejotes':'Vainita','judia verde':'Vainita',
    'judias verdes':'Vainita','vainitas':'Vainita',
    'tomate rojo':'Tomate','jitomate':'Tomate',
    'pimientos morrones rojos':'Pimiento rojo',
    'pimiento morron rojo':'Pimiento rojo',
    'pimientos morrones verdes':'Pimiento verde',
    'pimiento morron verde':'Pimiento verde',
    'limas':'Lima', 'limones':'Limón',
    'huevos de gallina':'Huevo',
    'yemas de huevo':'Yema de huevo','claras de huevo':'Clara de huevo',
    'alubia blanca':'Frijol blanco','alubias blancas':'Frijol blanco',
    'alubia roja':'Frijol rojo','alubias rojas':'Frijol rojo',
    'habichuelas negras':'Frijol negro',
    'guisantes':'Arveja','chícharos':'Arveja','chicharos':'Arveja',
    'brocoli':'Brócoli','brócolis':'Brócoli',
    'espaguetis':'Espagueti','espaguetis secos':'Espagueti',
    'nata para cocinar':'Crema de leche','nata liquida':'Crema de leche',
}
# NO fusionamos sinónimos ambiguos: chiles de variedades distintas, chile seco
# frente a fresco, pescado genérico frente a especies, leche frente a
# leche condensada; jugo de limón frente a limón, etc.

MEDIDAS_RESIDUALES = re.compile(
    r'^(?:(?:un(?:a|os|as)?|la|el|los|las|medio|media)\s+)?'
    r'(?:cuchar[oó]n(?:es)?|cucharaditas?|cucharadas?|tazas?|vasos?|latas?|'
    r'paquetes?|envases?|botellas?|bolsas?|potes?|botes?|tarros?|'
    r'ramitos?|ramas?|manojos?|dientecitos?|dientes?|pedazos?|pizcas?|'
    r'chorritos?|chorros?|gotas?|trozos?|cu[nñ]as?|puñados?|rebanadas?|'
    r'filetes?|láminas?|laminas?|cubitos?|cubos?|granos?|porciones?|'
    r'kilogramos?|gramos?|onzas?|litros?|ml|kg|g)\s+(?:de|del)\s+', re.I)
ADJETIVOS_FIN = re.compile(
    r'(?:\s+(?:bien\s+)?(?:picad[ao]s?|finamente\s+picad[ao]s?|'
    r'pelad[ao]s?|rallad[ao]s?|limpi[ao]s?|lavad[ao]s?|'
    r'desmenuzad[ao]s?|deshebrad[ao]s?|machacad[ao]s?|'
    r'triturad[ao]s?|cortad[ao]s?|fresc[ao]s?|maduros?|maduras?|'
    r'grandes?|pequeñ[ao]s?|median[ao]s?|enter[ao]s?|'
    r'crudos?|crudas?|sin\s+(?:semilla|piel|c[aá]scara)s?|'
    r'en\s+(?:rodajas?|cubos?|tiras?|trozos?)))+$', re.I)
# Nombres procesados o variedades que NO deben colapsarse por un adjetivo.
PROTEGIDOS = ('leche ', 'queso ', 'crema ', 'mantequilla de ', 'harina ',
              'pasta ', 'salsa ', 'concentrado ', 'puré ', 'pure ',
              'caldo ', 'vinagre ', 'aceite ', 'chocolate ', 'azúcar ',
              'azucar ', 'pimiento ', 'chile ', 'ají ', 'aji ', 'frijol ',
              'tomate verde', 'tomate cherry', 'tomate cereza', 'huevo de ',
              'carne ', 'carne de ', 'jamón ', 'jamon ', 'patata ', 'papa blanca',
              'papa amarilla', 'papa seca', 'pollo ', 'pescado ', 'vino ',
              'mostaza ', 'agua de ', 'yogur ', 'sal ', 'pan ',
              'pimienta ', 'vainilla ', 'semilla ')


def claves_singularizacion(palabra: str):
    """Propuestas morfológicas españolas: se aceptan sólo si existen en el corpus."""
    w=norm(palabra)
    propuestas=[]
    if len(w) < 5: return propuestas
    if w.endswith('ces') and len(w)>5: propuestas.append(w[:-3]+'z')
    if w.endswith('iones') and len(w)>6: propuestas.append(w[:-5]+'ion')
    if w.endswith('es') and len(w)>5:
        propuestas.extend([w[:-2],w[:-1]])
    if w.endswith('s') and len(w)>4:
        propuestas.append(w[:-1])
    return list(dict.fromkeys(x for x in propuestas if x!=w))


def crear_vocabulario(ruta: Path):
    """Muestrea TODO el CSV y construye vocabulario de referencia estable."""
    with ruta.open('r',encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        for row in reader:
            for raw, _free in split_ingredients(row.get('Ingredientes') or ''):
                val=_NORMAL_GLOBAL_BASE(raw)
                if not val or isinstance(val,tuple):continue
                for nombre, *_ in val:
                    VOCABULARIO[norm(nombre)]+=1


def canonico_global(name: str):
    original=clean(name)
    n=norm(original)
    if n in SINONIMOS_SEGUROS:
        return SINONIMOS_SEGUROS[n], 'sinonimo_seguro'
    # 1) Eliminar unidades que ya deberían estar en quantity_text.
    text=original
    for _ in range(2):
        v=MEDIDAS_RESIDUALES.sub('',text).strip()
        if v==text:break
        text=v
    text=re.sub(r'^(?:una?|unas?|unos?|varios?|varias?|algunas?)\s+', '',text,flags=re.I)
    text=re.sub(r'\s+(?:al gusto|a gusto|cantidad necesaria|c/n)\s*$', '',text, flags=re.I)
    text=clean(text)
    k=norm(text)
    if k in SINONIMOS_SEGUROS:
        return SINONIMOS_SEGUROS[k], 'sinonimo_seguro'
    if k in CANONICAL_EXACT:return CANONICAL_EXACT[k], 'diccionario_existente'
    if k in ALIASES:return ALIASES[k], 'alias_existente'
    # 2) Quitar sólo descriptores finales que no constituyen variedades
    # culinarias o cambios de presentación relevantes.
    if not k.startswith(PROTEGIDOS):
        minimal=clean(ADJETIVOS_FIN.sub('',text))
        if minimal and minimal!=text and VOCABULARIO.get(norm(minimal),0)>=2:
            text=minimal
            k=norm(text)
            if k in SINONIMOS_SEGUROS:return SINONIMOS_SEGUROS[k],'sinonimo_seguro'
            if k in CANONICAL_EXACT:return CANONICAL_EXACT[k],'diccionario_existente'
    # 3) Singularizar nombres de manera genérica SOLO con testigo real:
    # la forma singular existe en otro lugar del catálogo original.
    words=text.split()
    if not words:return original,'sin_cambio'
    opciones=[]
    for x in claves_singularizacion(words[0]):
        opcion=' '.join([x,*words[1:]])
        if VOCABULARIO.get(norm(opcion),0)>=2:opciones.append((VOCABULARIO[norm(opcion)],opcion))
    # También se contempla nombre + adjetivo plural: “aceitunas verdes”
    # -> “aceituna verde” cuando realmente aparece.
    if len(words)>=2:
        for x in claves_singularizacion(words[0]):
            for y in claves_singularizacion(words[1]):
                opcion=' '.join([x,y,*words[2:]])
                if VOCABULARIO.get(norm(opcion),0)>=2:opciones.append((VOCABULARIO[norm(opcion)],opcion))
    if opciones:
        _f, cand=max(opciones,key=lambda x:(x[0],-len(x[1])))
        ckey=norm(cand)
        # Nombre de catálogo existente preferido para no crear duplicados.
        for m in (SINONIMOS_SEGUROS,CANONICAL_EXACT,ALIASES):
            if ckey in m:return m[ckey],'plural_a_singular'
        return cand[:1].upper()+cand[1:],'plural_a_singular'
    return text[:1].upper()+text[1:],'sin_cambio' if norm(original)==norm(text) else 'medida_o_descriptor'


_NORMAL_GLOBAL_BASE = normal_ingredient

def normal_ingredient(raw: str):
    val=_NORMAL_GLOBAL_BASE(raw)
    if not val or isinstance(val,tuple):return val
    salida=[]
    for nombre,qty,required,alerts in val:
        canon,regla=canonico_global(nombre)
        if not canon: canon=nombre
        if norm(nombre)!=norm(canon):
            CAMBIOS_GLOBALES[(nombre,canon,regla)]+=1
            EJEMPLOS_CAMBIOS.setdefault((nombre,canon,regla),raw)
            # Así ingredient_aliases contiene también todas las variantes
            # realmente fusionadas, no sólo un pequeño vocabulario inicial.
            alias_key=norm(nombre)
            ALIASES.setdefault(alias_key,canon)
            alerts=[*alerts,f'Normalización global: {nombre} -> {canon} ({regla})']
        salida.append((canon,qty,required,alerts))
    return salida


_BASE_RUN_GLOBAL = run

def run():
    ap=argparse.ArgumentParser(add_help=False)
    ap.add_argument('--csv',type=Path,default=BASE/'main.csv')
    a,_unknown=ap.parse_known_args()
    if not a.csv.exists():
        raise SystemExit('No se encuentra '+str(a.csv)+'; usa --csv main.csv')
    print('Paso 1/3: leyendo vocabulario completo para unificar variantes de TODOS los ingredientes...',flush=True)
    crear_vocabulario(a.csv)
    print(f'  {len(VOCABULARIO):,} nombres de entrada para análisis; ejecutando conversión...',flush=True)
    _BASE_RUN_GLOBAL()
    # Archivos auxiliares: todas las fusiones aplicadas y los casos sospechosos.
    salida=Path(sys.argv[sys.argv.index('--salida')+1]) if '--salida' in sys.argv else BASE/'data_desde_cero_limpio.sql'
    out=salida.parent
    with (out/'equivalencias_aplicadas.csv').open('w',encoding='utf-8-sig',newline='') as fp:
        w=csv.writer(fp);w.writerow(['variante_origen','nombre_canonico','regla','apariciones','ejemplo_csv'])
        for (v,c,r),freq in sorted(CAMBIOS_GLOBALES.items(),key=lambda x:(-x[1],x[0][0])):
            w.writerow([v,c,r,freq,EJEMPLOS_CAMBIOS[(v,c,r)]])
    revisiones=[]
    with (out/'auditoria_ingredientes.csv').open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            nombre=row['nombre_normalizado'];cantidad=int(row['recetas']);k=norm(nombre)
            # Criterios reproducibles de sospecha: largo, unidades residuales,
            # restos de instrucciones, errores de codificación, singularidad.
            motivos=[]
            if cantidad==1:motivos.append('aparece en una receta')
            if len(nombre.split())>=5:motivos.append('nombre largo')
            if re.search(r'(?:Ã|ð|Â|�)',nombre):motivos.append('posible codificación dañada')
            if re.search(r'\b(?:para el|para la|debes|hay que|a gusto|al gusto|cuchar[óo]n|onzas?|gramos|kilogramos|\d+)\b',k):motivos.append('restos de cantidad o instrucción')
            if motivos:revisiones.append((row['ingredient_id'],nombre,cantidad,'; '.join(motivos)))
    with (out/'ingredientes_para_revisar.csv').open('w',encoding='utf-8-sig',newline='') as fp:
        w=csv.writer(fp);w.writerow(['ingredient_id','nombre','recetas','motivos']);w.writerows(revisiones)
    with (out/'INFORME_GLOBAL.txt').open('w',encoding='utf-8') as fp:
        fp.write('NORMALIZACIÓN DE TODOS LOS INGREDIENTES DE main.csv\n')
        fp.write('Reglas aplicadas a todas las filas, no sólo al tomate.\n')
        fp.write(f'Variantes distintas unificadas: {len(CAMBIOS_GLOBALES)}\n')
        fp.write(f'Usos de variantes unificados: {sum(CAMBIOS_GLOBALES.values())}\n')
        fp.write(f'Ingredientes que requieren revisión por criterios automáticos: {len(revisiones)}\n')
        fp.write('IMPORTANTE: los de una sola receta no son necesariamente errores.\n')
        fp.write('No se aplican fusiones por parecido difuso sin corroboración.\n')
    print('Paso 3/3: generado equivalencias_aplicadas.csv y reporte de revisión.',flush=True)

# Conservar variedades distintas cuando el CSV especifica el tipo.
ALIASES.update({'papas amarillas':'Papa amarilla', 'papas rojas':'Papa roja', 'papa roja':'Papa roja'})
PARENT_MAP.update({'papa roja':'Papa'})

if __name__ == '__main__':
    run()
