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
                seen=set()
                for name,qty,required,alerts,raw,free in entries:
                    key=norm(name)
                    if key not in catalog:
                        iid=len(catalog)+1;catalog[key]=(iid,name)
                        examples[key]=raw
                    iid=catalog[key][0]
                    if iid in seen:
                        counter['duplicate_link_dropped']+=1
                        continue
                    seen.add(iid);usages[key]+=1
                    if alerts: flags.setdefault(key,set()).update(alerts)
                    if free:flags.setdefault(key,set()).add('texto libre (sin lista estructurada)')
                    n_links+=1
                    lbuf.append(f'({n_links}, {n_dishes}, {iid}, {sql_str(qty[:100])}, {str(required).lower()})')
                    if len(lbuf)>=700:emit(lf,'dish_ingredients','id, dish_id, ingredient_id, quantity_text, is_required',lbuf)
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
            f'Relaciones repetidas dentro de una receta: {counter["duplicate_link_dropped"]}\n'
            'Categoría 5 = Otros. REVISAR compatibilidad del backend, no se modifican tablas ni columnas.\n'
            'ATENCIÓN: la limpieza heurística no reemplaza verificación humana.\n'
            'NOTA: el SQL no crea tablas, no se ha probado contra el esquema PostgreSQL de tu backend.\n')
    (root/'RESUMEN_LIMPIEZA.txt').write_text(report,encoding='utf-8')
    print(report)
    print('SQL:',a.salida)

if __name__=='__main__':run()
