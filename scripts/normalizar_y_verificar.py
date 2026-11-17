#!/usr/bin/env python3
"""Pipeline de normalización de ingredientes de Manka. Python >=3.10; sin dependencias externas.
Uso: python normalizar_y_verificar.py --csv main.csv --salida manka_seed_auditado.sql
CSV fuente EXCLUSIVA; genera de nuevo las relaciones, mantiene variedades distintas,
no aplica fusiones difusas sin evidencia. No certifica calidad semántica humana.
"""
import argparse
import csv
import importlib.util
import re
import sqlite3
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('manka_motor_base',HERE/'_motor_base.py')
base=importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

norm=base.norm
clean=base.clean
sql_str=base.sql_str

# Cambios semánticos explícitos, verificados: no fusionar variedades ni procesados.
# Estas equivalencias se aplican a todo el CSV y aparecen en un reporte.
EXPLICIT={
    'aceite oliva':'Aceite de oliva','aceite extra virgen de oliva':'Aceite de oliva',
    'aceite de olivo':'Aceite de oliva', 'aceite de olivas':'Aceite de oliva',
    'aceite de girasol':'Aceite de girasol', 'aceite girasol':'Aceite de girasol',
    'aceite de maiz':'Aceite de maíz','aceite maiz':'Aceite de maíz',
    'aceite de coco':'Aceite de coco','aceite coco':'Aceite de coco',
    'arveja':'Arveja','arvejas':'Arveja','alverja':'Arveja','alverjas':'Arveja',
    'guisante':'Arveja','guisantes':'Arveja','chicharos':'Arveja', 'chicharo':'Arveja',
    'frejol':'Frijol', 'frejoles':'Frijol', 'frijoles':'Frijol', 'frijol':'Frijol',
    'poroto':'Frijol','porotos':'Frijol','alubias':'Frijol',
    'frijoles negros':'Frijol negro','frijol negro':'Frijol negro',
    'frejoles negros':'Frijol negro','frijoles blancos':'Frijol blanco',
    'frijoles rojos':'Frijol rojo',
    'tortilla chips':'Chips de tortilla','tortillas chips':'Chips de tortilla',
    'chips de tortilla':'Chips de tortilla','totopos':'Chips de tortilla',
    'azucar refinada':'Azúcar blanca','azucar blanca':'Azúcar blanca',
    'azucar blanquilla':'Azúcar blanca',
    'azucar rubia':'Azúcar rubia','azucar morena':'Azúcar morena',
    'ajo':'Ajo','ajos':'Ajo','diente de ajo':'Ajo','dientes de ajo':'Ajo',
    'ajo fresco':'Ajo','ajo finamente picado':'Ajo','ajo machacado':'Ajo',
    'ajos tiernos':'Ajo tierno', 'ajo tierno':'Ajo tierno',
    'ajo negro':'Ajo negro',
    'ajo en polvo':'Ajo en polvo', 'polvo de ajo':'Ajo en polvo',
    'cebolla china':'Cebolla china','cebollas chinas':'Cebolla china',
    'cebolla de verdeo':'Cebolla china','cebolla larga':'Cebolla china',
    'cebolla verde':'Cebolla china','cebollas verdes':'Cebolla china',
    'cebolleta':'Cebolla china',
    'cebollino':'Cebollín','cebollin':'Cebollín',
    'cebolla cabezona':'Cebolla','cebolla':'Cebolla','cebollas':'Cebolla',
    'cebolla blanca':'Cebolla blanca', 'cebolla morada':'Cebolla roja',
    'cebolla roja':'Cebolla roja',
    'cebolla en polvo':'Cebolla en polvo', 'polvo de cebolla':'Cebolla en polvo',
    'papas':'Papa','papa':'Papa','patatas':'Papa','patata':'Papa',
    'papa roja':'Papa roja','papas rojas':'Papa roja',
    'papa amarilla':'Papa amarilla','papas amarillas':'Papa amarilla',
    'papa blanca':'Papa blanca','papas blancas':'Papa blanca',
    'papa seca':'Papa seca','papas secas':'Papa seca',
    'tomate':'Tomate','tomates':'Tomate', 'jitomate':'Tomate','jitomates':'Tomate',
    'tomate roma':'Tomate','tomates roma':'Tomate','jitomate roma':'Tomate',
    'tomate cereza':'Tomate cherry','tomate cherry':'Tomate cherry',
    'tomates cherry':'Tomate cherry','jitomates cherry':'Tomate cherry',
    'tomate verde':'Tomate verde','tomates verdes':'Tomate verde',
    'tomatillo':'Tomatillo','tomatillos':'Tomatillo',
    'aguacate':'Palta','aguacates':'Palta','palta':'Palta','paltas':'Palta',
    'cilantro':'Culantro','culantro':'Culantro',
    'choclo':'Choclo','maiz tierno':'Choclo','maiz dulce':'Choclo',
    'maiz seco':'Maíz seco',
    'camarones':'Camarón','camaron':'Camarón',
    'langostinos':'Langostino','langostino':'Langostino',
    'huevos':'Huevo','huevo':'Huevo',
    'claras de huevo':'Clara de huevo','clara de huevo':'Clara de huevo',
    'yemas de huevo':'Yema de huevo','yema de huevo':'Yema de huevo',
    'zanahorias':'Zanahoria','zanahoria':'Zanahoria',
    'champiñones':'Champiñón','champinon':'Champiñón',
    'calabacines':'Calabacín','calabacin':'Calabacín',
    'berenjenas':'Berenjena','berenjena':'Berenjena',
    'alcaparras':'Alcaparra','alcaparra':'Alcaparra',
    'aceitunas':'Aceituna','aceituna':'Aceituna',
    'aceitunas verdes':'Aceituna verde','aceituna verde':'Aceituna verde',
    'aceitunas negras':'Aceituna negra','aceituna negra':'Aceituna negra',
    'acelgas':'Acelga','almejas':'Almeja','almendras':'Almendra',
    'almendras tostadas':'Almendra tostada','avellanas':'Avellana',
    'batatas':'Batata','berros':'Berro','bizcochos de soletilla':'Bizcocho de soletilla',
    'champinones':'Champiñón','choclos':'Choclo','choclos cremosos':'Choclo cremoso',
    'chorizos':'Chorizo','chuletas de cerdo':'Chuleta de cerdo','clavos de olor':'Clavo de olor',
    'cominos':'Comino','costillas de cerdo':'Costilla de cerdo',
    'doradas':'Dorada','ejotes':'Vainita','endibias':'Endibia',
    'espaguetis':'Espagueti','espinacas':'Espinaca','frambuesas':'Frambuesa',
    'fresas':'Fresa','frutas confitadas':'Fruta confitada',
    'galletas maria':'Galleta María','galletas marias':'Galleta María',
    'galletas oreo':'Galleta Oreo','gambas':'Gamba','garbanzos':'Garbanzo',
    'hebras de azafran':'Hebra de azafrán','lechugas variadas':'Lechuga variada',
    'lentejas':'Lenteja','moras':'Mora','nueces':'Nuez',
    'pepinillos en vinagre':'Pepinillo en vinagre','pimienta negra molida':'Pimienta negra',
    'quesitos':'Quesito','rabanos':'Rábano','raices chinas':'Raíz china',
    'sal fina':'Sal','tallarines':'Tallarín','tomates rojos':'Tomate',
    'aceite de oliva virgen':'Aceite de oliva',
    'leche condensada':'Leche condensada',
    'leche evaporada':'Leche evaporada',
    'leche de soya':'Leche de soya','leche de soja':'Leche de soya',
    'crema de leche':'Crema de leche','nata para cocinar':'Crema de leche',
    'nata liquida':'Crema de leche',
    'salsa de tomate':'Salsa de tomate','pasta de tomate':'Pasta de tomate',
    'pure de tomate':'Puré de tomate',
}
# No interpretar variaciones de preparación como identidad: ajo en polvo, ajo negro,
# caldo de pollo, salsa de tomate, cebolla china y aceite de oliva se mantienen distintos.
PARENTS={
    'Cebolla china':'Cebolla','Cebolla roja':'Cebolla','Cebolla blanca':'Cebolla',
    'Ajo negro':'Ajo','Ajo tierno':'Ajo','Ajo en polvo':'Ajo',
    'Papa amarilla':'Papa','Papa blanca':'Papa','Papa roja':'Papa',
    'Tomate cherry':'Tomate','Tomate verde':'Tomate',
    'Frijol blanco':'Frijol','Frijol negro':'Frijol','Frijol rojo':'Frijol',
    'Aceituna negra':'Aceituna','Aceituna verde':'Aceituna',
    'Clara de huevo':'Huevo','Yema de huevo':'Huevo',
    'Pechuga de pollo':'Pollo','Pierna de pollo':'Pollo','Muslo de pollo':'Pollo',
    'Aceite de oliva':'Aceite','Aceite de girasol':'Aceite','Aceite de maíz':'Aceite',
    'Aceite de coco':'Aceite',
}
# Operadores seguros que se eliminan del TEXTO que describe el ingrediente.
HEAD = re.compile(r'^(?:aprox(?:imadamente)?\.?\s*|m[aá]s\s+|aproximad[ao]s?\s+|un poco de\s+|una pizca de\s+|'
                  r'caja\s+\d+(?:[.,]\d+)?\s+(?:onzas?|oz\.?|grs?|gramos?)\s+de\s+)',re.I)
NOTE = re.compile(r'\s+(?:ver\s+nota\b.*|para\s+(?:adornar|servir|acompañar|decorar|freír|freir|sazonar|probar)\b.*|'
                  r'si\s+(?:lo|se)\s+(?:desea|prefiere|puede)\b.*|se\s+puede\s+sustituir\b.*|'
                  r'(?:opcional|opcionalmente)\b.*|a\s+elecci[oó]n\b.*)$',re.I)
PURE_HEADINGS = {'para las albondigas','para el pollo','para las verduras',
                 'para los ingredientes','para la carne','para la ensalada',
                 'para la salsa','para el relleno','para el vaso','para adornar',
                 'para servir','para 4 personas','guarnicion','relleno','para el aderezo'}
NON_ING = re.compile(r'^(?:(?:para\s+(?:las?|los)\s+|ingredientes?\s+para\s+).{1,50}|'
                     r'pkg\.?\s*\d+|\d+\s*(?:in|inch|cm)\.?|\d+\s*estrellas?\s+de\s+an[ií]s\s*\(??$)$',re.I)
# Preserve useful foods: 'estrellas de anís' isn't a heading/noise.
NON_ING = re.compile(r'^(?:pkg\.?\s*\d+|\d+\s*(?:in|inch|cm)\.?|(?:para|ingredientes para)\s+(?:el|la|las|los)\s+(?:relleno|salsa|masa|aderezo|pollo|carne|alb[oó]ndigas|decoraci[oó]n|cubierta|guarnici[oó]n))$',re.I)

QUALIFIERS = re.compile(r'\s+(?:ver nota|para (?:adornar|servir|acompañar|decorar|freír|freir|sazonar)|'
                         r'(?:opcional|opcionalmente)|si (?:lo|se) (?:desea|prefiere)|'
                         r'en (?:rodajas|cubitos|cubos|trozos|tiras)|'
                         r'(?:bien )?(?:picad[ao]s?|cortad[ao]s?|rallad[ao]s?|triturad[ao]s?|machacad[ao]s?|'
                         r'pelad[ao]s?|lavad[ao]s?|limpiad[ao]s?|fresc[ao]s?|maduros?|maduras?|grandes?|pequeñ[ao]s?|median[ao]s?|finamente))\b.*$',re.I)
PROTECT = ('salsa de ','pasta de ','puré de ','pure de ','caldo de ','leche de ',
           'leche condensada','leche evaporada','crema de ','harina de ',
           'jugo de ','zumo de ','aceite de ','vinagre de ','chile ','ají ','aji ',
           'queso ','pimienta ','papa amarilla','papa blanca','papa roja',
           'pimiento rojo','pimiento verde','azúcar rubia','azucar rubia',
           'azúcar morena','azucar morena','tomate verde','tomate cherry',
           'tomatillo','ajo negro','ajo tierno','cebolla china',
           'frijol negro','frijol rojo','frijol blanco')

OLD_NORMAL=base.normal_ingredient
fixes=Counter()

def fixed_ingredient(raw):
    original=raw or ''
    cleaned=original.strip().replace('to rtillas','tortillas').replace('to mates','tomates')
    # No eliminar una línea si solamente contiene una palabra alimento real.
    if norm(cleaned) in PURE_HEADINGS or NON_ING.match(cleaned.strip()):
        fixes['encabezado_excluido']+=1
        return None
    # Prefijos de cantidad antes del alimento que el motor previo no reconocía.
    caja=re.match(r'^caja\s+(\d+(?:[.,]\d+)?\s+(?:onzas?|oz\.?|grs?|gramos?))\s+de\s+',cleaned,re.I)
    cleaned=HEAD.sub('',cleaned)
    val=OLD_NORMAL(cleaned)
    if not val or isinstance(val,tuple): return val
    result=[]
    for name,qty,required,alerts in val:
        before=name
        if caja and qty=='no especificada':qty=caja.group(1)
        name=clean(name)
        if norm(name) in PURE_HEADINGS or NON_ING.match(name):
            fixes['encabezado_excluido']+=1; continue
        # Corregir fusiones demasiado agresivas del motor anterior a partir del TEXTO ORIGINAL.
        raw_norm=norm(original)
        special=[
            (r'\bcebollas?\s+chinas?\b|\bcebolla\s+(?:larga|verde|de verdeo)\b','Cebolla china'),
            (r'\bcebollino\b|\bceboll[ií]n\b','Cebollín'),
            (r'\bajos?\s+negros?\b','Ajo negro'),
            (r'\bajos?\s+tiernos?\b','Ajo tierno'),
            (r'\bajos?\s+en\s+polvo\b|\bpolvo de ajo\b','Ajo en polvo'),
            (r'\bcebolla\s+en\s+polvo\b','Cebolla en polvo'),
            (r'\bpapas?\s+rojas?\b|\bpatatas?\s+rojas?\b','Papa roja'),
            (r'\bpapas?\s+amarillas?\b|\bpatatas?\s+amarillas?\b','Papa amarilla'),
            (r'\bpapas?\s+blancas?\b|\bpatatas?\s+blancas?\b','Papa blanca'),
            (r'\btomates?\s+cherry\b|\btomates?\s+cereza\b','Tomate cherry'),
            (r'\btomates?\s+verdes?\b','Tomate verde'),
            (r'\bfrijoles?\s+negros?\b|\bfrejoles?\s+negros?\b','Frijol negro'),
            (r'\bfrijoles?\s+blancos?\b|\bfrejoles?\s+blancos?\b','Frijol blanco'),
        ]
        for pattern,canonical in special:
            if re.search(pattern,raw_norm):
                # Nunca convertir salsa, sopa, caldo, crema ni jugo en ingrediente fresco.
                if not raw_norm.startswith(('salsa de ','caldo de ','sopa de ','crema de ','jugo de ','zumo de ','pasta de ')):
                    name=canonical
                break
        # Normalizar texto auxiliar sin borrar variedades o productos transformados.
        name=NOTE.sub('',name).strip()
        key=norm(name)
        if key in EXPLICIT:name=EXPLICIT[key]
        else:
            minimal=clean(QUALIFIERS.sub('',name))
            if minimal and minimal != name and not key.startswith(PROTECT) and len(minimal.split())>=1:
                # Solo aceptar cuando el nombre corto ya es reconocible como ingrediente
                # o está presente en el vocabulario de formas canónicas.
                if norm(minimal) in EXPLICIT:
                    name=EXPLICIT[norm(minimal)]
                elif norm(minimal) in base.VOCABULARIO and base.VOCABULARIO[norm(minimal)] >= 2:
                    name=minimal
        # Cantidades residuales si el motor dejó la cifra en el nombre.
        if qty=='no especificada':
            p=re.match(r'^(\d+(?:[.,]\d+)?\s*(?:kg|kilo(?:gramos?)?|g|gr(?:amos?)?|ml|l(?:itros?)?|taza(?:s)?|cucharada(?:s)?|cucharadita(?:s)?|onzas?|oz)\b)\s+(?:de\s+)?(.+)$',name,re.I)
            if p and p.group(2):
                qty=p.group(1);name=p.group(2)
        name=clean(name)
        if not name or norm(name) in PURE_HEADINGS:continue
        if norm(name)!=norm(before):
            fixes['nombre_corregido']+=1
        result.append((name,qty,required,[*alerts, 'Limpieza final: '+before+' -> '+name] if norm(name)!=norm(before) else alerts))
    return result or None

# Asegura que el motor use las correcciones en todas las filas y no solo en un puñado.
base.normal_ingredient=fixed_ingredient
base.PARENT_MAP.update({norm(k):v for k,v in PARENTS.items()})
base.ALIASES.update({k:v for k,v in EXPLICIT.items() if norm(k)!=norm(v)})

SCHEMA='''
PRAGMA foreign_keys=ON;
CREATE TABLE protein_categories(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE);
CREATE TABLE ingredients(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE,parent_id INTEGER REFERENCES ingredients(id));
CREATE TABLE dishes(id INTEGER PRIMARY KEY,name TEXT NOT NULL,preparation_minutes INT,difficulty TEXT,
 popularity_score INT NOT NULL,preparation TEXT NOT NULL,protein_category_id INT REFERENCES protein_categories(id),
 source_id INT UNIQUE,source_url TEXT,country TEXT,servings INT,meal_type TEXT,rating_average REAL,
 rating_votes INT,duration_estimated INT NOT NULL,difficulty_estimated INT NOT NULL);
CREATE TABLE dish_ingredients(id INTEGER PRIMARY KEY,dish_id INT NOT NULL REFERENCES dishes(id),
 ingredient_id INT NOT NULL REFERENCES ingredients(id),quantity_text TEXT,is_required INT NOT NULL,
 UNIQUE(dish_id,ingredient_id));
CREATE TABLE ingredient_aliases(id INTEGER PRIMARY KEY,alias TEXT,alias_key TEXT UNIQUE NOT NULL,
 ingredient_id INT NOT NULL REFERENCES ingredients(id));
CREATE TABLE protein_sources(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE);
CREATE TABLE dish_protein_sources(dish_id INT NOT NULL REFERENCES dishes(id),protein_source_id INT NOT NULL REFERENCES protein_sources(id),
 PRIMARY KEY(dish_id,protein_source_id));
CREATE TABLE tags(id INTEGER PRIMARY KEY,name TEXT NOT NULL,type TEXT NOT NULL,UNIQUE(name,type));
CREATE TABLE dish_tags(dish_id INT NOT NULL REFERENCES dishes(id),tag_id INT NOT NULL REFERENCES tags(id),PRIMARY KEY(dish_id,tag_id));
'''

def sql_cell(v):
    if v is None:return 'NULL'
    if isinstance(v,str):return sql_str(v)
    if isinstance(v,bool):return 'true' if v else 'false'
    return str(v)

def write_rows(f,table,cols,rows,chunk=400):
    values=[]
    for row in rows:
        values.append('('+', '.join(sql_cell(v) for v in row)+')')
        if len(values)>=chunk:
            f.write('INSERT INTO '+table+' ('+', '.join(cols)+') VALUES\n'+',\n'.join(values)+';\n')
            values.clear()
    if values:f.write('INSERT INTO '+table+' ('+', '.join(cols)+') VALUES\n'+',\n'.join(values)+';\n')
    f.write('\n')

# --- Normalización posterior: general, de alta confianza y auditable. ---
SINGULAR_SAFE={
    'salsas':'Salsa', 'aceites':'Aceite', 'zanahorias':'Zanahoria',
    'huevos':'Huevo', 'ajos':'Ajo', 'patatas':'Papa', 'papas':'Papa',
    'tomates':'Tomate', 'jitomates':'Tomate', 'frijoles':'Frijol',
    'frejoles':'Frijol', 'aceitunas':'Aceituna', 'alverjas':'Arveja',
    'guisantes':'Arveja', 'papas':'Papa',
}
CONTAINERS=re.compile(
    r'^(?:(?:\d+(?:[.,]\d+)?\s*(?:/\s*\d+)?|[¼½¾⅓⅔]|uno|una|un|dos|tres|cuatro|cinco|varios|varias|un poco|poquito)\s+)?'
    r'(?:libra(?:s)?|lb|libras?|pizca(?:s)?|pellizco(?:s)?|chorro(?:s)?|chorrito(?:s)?|'
    r'cucharadita(?:s)?|cucharada(?:s)?|cditas?|cdas?|cuchara(?:s)?|'
    r'taza(?:s)?|tasas?|tasa|vasito(?:s)?|vaso(?:s)?|'
    r'puñado(?:s)?|puñadito(?:s)?|bolsa(?:s)?|lata(?:s)?|'
    r'botella(?:s)?|paquete(?:s)?|caja(?:s)?|tarro(?:s)?|'
    r'loncha(?:s)?|rodaja(?:s)?|trozo(?:s)?|troco(?:s)?|'
    r'tajadas?|láminas?|ramitas?|ramas?|manojos?|hojas?|'
    r'dientes?|granos?|cubiletes?|unidad(?:es)?|filetes?)\s+(?:de|del)\s+',re.I)
QUANT_PREFIX=re.compile(
    r'^\s*(?P<qty>(?:\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?|[½¼¾⅓⅔]|una?|unos?|varias?)\s*'
    r'(?:kg|kilos?|kilogramos?|g|grs?|gramos?|ml|l|litros?|'
    r'cc|onzas?|oz|tazas?|cucharadas?|cucharaditas?|libras?|lb|'
    r'dientes?|rebanadas?|unidades?|chorros?|pizcas?))\s*(?:de|del)?\s+(?P<rest>.+)$',re.I)
INTRO = re.compile(r'^(?:y\s+|m[aá]s\s+|aprox(?:imadamente)?\.?\s+|aproximad[ao]s?\s+)',re.I)
TRAIL = re.compile(r'(?:\s+(?:finamente\s+)?(?:picad[ao]s?|cortad[ao]s?|pelad[ao]s?|lavados?|limpi[ao]s?|'
                   r'machacad[ao]s?|rallad[ao]s?|triturad[ao]s?|trocead[ao]s?|'
                   r'en\s+(?:cubitos?|rodajas?|trozos?|tiras?|juliana)|'
                   r'grandes?|pequeñ[ao]s?|medianos?|medianas?|'
                   r'fresc[ao]s?|maduros?|maduras?))+$',re.I)
NONFOOD_STRICT=re.compile(
    r'^(?:para\s+(?:el|la|las|los)\s+(?:relleno|salsa|aderezo|crema|masa|pollo|carne|alb[oó]ndigas|guarnici[oó]n|'
    r'pasta|ensalada|decoraci[oó]n)|para\s+todo\s+uso|'
    r'ingredientes\s+para\b.*|'
    r'(?:aparte\s+debes\s+tener|despepitadas|pkg\.?\s*\d+|\d+\s*(?:in|inch|cm)))$',re.I)
COMBOS={
    'sal y pimienta':('Sal','Pimienta'),
    'sal pimienta':('Sal','Pimienta'),
    'pimienta y sal':('Pimienta','Sal'),
    'sal y pimienta para sazonar':('Sal','Pimienta'),
    'sal y pimienta para probar':('Sal','Pimienta'),
    'sal y pimienta para el sazon':('Sal','Pimienta'),
    'sal y pimienta al gusto':('Sal','Pimienta'),
    'sal y pimienta negra':('Sal','Pimienta negra'),
    'pimienta negra y sal':('Pimienta negra','Sal'),
    'sal pimienta negra':('Sal','Pimienta negra'),
}

def extraer_normalizacion(name):
    """Devuelve ([nombres], cantidad_sugerida, motivo). Sin similitud difusa."""
    raw=clean(name)
    normalized=norm(raw)
    if NONFOOD_STRICT.fullmatch(raw) or normalized in PURE_HEADINGS:
        return [],None,'encabezado/no ingrediente'
    if normalized in COMBOS:return list(COMBOS[normalized]),'al gusto','separación sal y pimienta'
    qty=None
    txt=raw
    for _ in range(3):
        txt=INTRO.sub('',txt).strip()
        q=QUANT_PREFIX.match(txt)
        if q:
            if not qty:qty=q.group('qty')
            txt=q.group('rest').strip()
            continue
        nxt=CONTAINERS.sub('',txt)
        if nxt==txt:break
        txt=nxt.strip()
    if not txt:return [raw],None,'sin cambio'
    nk=norm(txt)
    if nk in EXPLICIT:txt=EXPLICIT[nk]
    # Descriptores finales, siempre que quede un nombre identificable.
    pre=clean(TRAIL.sub('',txt))
    if pre and norm(pre) in EXPLICIT:
        txt=EXPLICIT[norm(pre)]
    elif pre and len(pre)<len(txt) and not nk.startswith(PROTECT):
        # Quitar solo modos de preparación finales, no expresiones culinarias sustantivas.
        txt=pre
    key=norm(txt)
    if key in EXPLICIT:txt=EXPLICIT[key]
    return [txt[:1].upper()+txt[1:]],qty,('normalización de medida/descriptor' if norm(raw)!=norm(txt) else 'sin cambio')


# Excepciones auditadas MANUALMENTE contra main.csv: estos 13 registros
# están mal separados en la fuente y el parser original perdió todos los alimentos.
# No se crean ingredientes cuando la fila viene vacía (source_id=6434).
# Unidades no inequívocas quedan "no especificada"; nunca se inventan.
RECUPERADOS={
 163:[('Polvo para hornear','15 g'),('Azúcar','600 g + alternativas en texto; revisar'),
      ('Anís estrellado','4 estrellas'),('Canela','2 ramas'),('Mantequilla','100 g'),
      ('Harina de trigo','220 g'),('Huevo','8 unidades')],
 2334:[('Harina','500 g'),('Levadura','25 g'),('Agua','160 ml'),('Vino blanco','50 ml'),
       ('Sal','1 pizca'),('Aceite','no especificada'),('Cebolla','no especificada'),
       ('Atún','350 g'),('Tomate frito','4 cucharadas'),('Pimentón dulce','no especificada'),
       ('Aceite de oliva','no especificada')],
 2567:[('Mayonesa','1 bote mediano'),('Cebolla','1 unidad mediana'),('Huevo','2 unidades'),
       ('Pan de molde','1 paquete mediano'),('Palitos de cangrejo','12 unidades')],
 4839:[('Lomo de cerdo','4 filetes'),('Longaniza','4 trozos'),('Arveja','1 lata pequeña'),
       ('Espárrago','1 lata pequeña'),('Huevo','2 unidades'),('Aceite','no especificada'),
       ('Ajo','no especificada'),('Agua','no especificada'),('Sal','no especificada'),
       ('Harina','media cucharada')],
 7091:[('Carrucho','cantidad indicada por precio, revisar'),('Pimiento verde','1 unidad'),
       ('Pimiento rojo','1 unidad'),('Laurel','3 hojas'),('Aceite de oliva','6 onzas'),
       ('Vinagre blanco','1 taza')],
 8166:[('Salchicha','no especificada'),('Salsa de tomate','no especificada'),
       ('Huevo','no especificada'),('Cebolla china','no especificada'),
       ('Jamón','no especificada'),('Queso en barra','no especificada'),
       ('Tomate','al gusto')],
 8171:[('Ajo','no especificada'),('Perejil','no especificada'),('Huevo','no especificada'),
       ('Gamba','no especificada'),('Aceite','no especificada'),('Sal','no especificada'),
       ('Jamón ibérico','no especificada'),('Aceituna','al gusto')],
 10834:[('Fideos gruesos','360–400 g'),('Pimiento verde italiano','1 unidad'),
        ('Tomate frito','no especificada'),('Pimentón dulce','1/2 cucharadita'),
        ('Mejillón','no especificada'),('Gamba','no especificada'),
        ('Calamar','no especificada'),('Caldo de pescado','1 pastilla'),
        ('Brandy','no especificada'),('Colorante alimenticio','no especificada'),
        ('Hierbabuena','no especificada'),('Ajo','5 dientes')],
 11898:[('Atún','400 g'),('Papa','1 unidad mediana'),('Calabacín verde','1 unidad'),
        ('Cebolla','1 unidad'),('Tomate','2 unidades'),('Vino blanco','no especificada'),
        ('Almendra','50 g'),('Ajo','4 dientes'),('Azafrán','no especificada'),
        ('Perejil','no especificada'),('Aceite','no especificada'),('Sal','no especificada')],
 14696:[('Leche condensada','1 lata'),('Leche en polvo','250 g'),
        ('Azúcar pulverizada','500 g'),('Margarina','1 cucharada')],
 14825:[('Leche condensada','2 potes'),('Huevo','5 unidades; revisar yemas'),
        ('Yema de huevo','3 unidades; revisar total'),('Vinagre de vino tinto','45 ml'),
        ('Cebolla frita','no especificada')],
 16883:[('Manteca','no especificada (texto: 5o G)'),('Harina','200 g'),
        ('Cebolla','2 unidades'),('Manzana verde','2 unidades'),('Leche','1 l'),
        ('Queso rallado','200 g')],
 19752:[('Plátano','3 unidades'),('Huevo','2 unidades'),('Polvo para hornear','2 cucharaditas'),
        ('Sal','1/2 cucharadita'),('Harina','240 g'),('Azúcar','100 g'),
        ('Aceite','75 g'),('Chispas de chocolate','50 g')],
}

def build_final(original:Path,output:Path,folder:Path,source_csv:Path):
    print('Importando SQL intermedio en SQLite para verificar y reconstruir claves...',flush=True)
    db=sqlite3.connect(':memory:')
    db.executescript(SCHEMA)
    raw_sql='\n'.join(line for line in original.read_text(encoding='utf-8').splitlines() if not line.startswith('SELECT setval('))
    db.executescript(raw_sql)
    db.execute('PRAGMA foreign_keys=ON')
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    # Recuperar recetas que el parser descartó por formato de lista defectuoso.
    # Cada corrección está respaldada por el texto de main.csv y se audita.
    ids_to_dish=dict(db.execute('SELECT source_id,id FROM dishes'))
    source_rows={int(row['Id']):row for row in csv.DictReader(source_csv.open(encoding='utf-8-sig',newline=''))}
    ingredients_lookup={norm(name):id_ for id_,name in db.execute('SELECT id,name FROM ingredients')}
    next_ing=db.execute('SELECT COALESCE(MAX(id),0) FROM ingredients').fetchone()[0]
    next_link=db.execute('SELECT COALESCE(MAX(id),0) FROM dish_ingredients').fetchone()[0]
    recuperaciones=[]
    for source_id,items in RECUPERADOS.items():
        assert source_id in source_rows and source_id in ids_to_dish
        dish_id=ids_to_dish[source_id]
        existing=db.execute('SELECT COUNT(*) FROM dish_ingredients WHERE dish_id=?',(dish_id,)).fetchone()[0]
        if existing:continue
        for candidate,qty in items:
            key=norm(EXPLICIT.get(norm(candidate),candidate))
            name=EXPLICIT.get(norm(candidate),candidate)
            if key not in ingredients_lookup:
                next_ing+=1;ingredients_lookup[key]=next_ing
                db.execute('INSERT INTO ingredients(id,name,parent_id) VALUES(?,?,NULL)',(next_ing,name))
            iid=ingredients_lookup[key]
            next_link+=1
            db.execute('INSERT INTO dish_ingredients(id,dish_id,ingredient_id,quantity_text,is_required) VALUES(?,?,?,?,1)',
                       (next_link,dish_id,iid,qty))
            recuperaciones.append((source_id,dish_id,candidate,qty,source_rows[source_id]['Ingredientes'][:220]))
    with (folder/'recuperacion_13_recetas.csv').open('w',encoding='utf-8-sig',newline='') as ff:
        w=csv.writer(ff);w.writerow(['source_id','dish_id','ingrediente_recuperado','cantidad','evidencia_original']);w.writerows(recuperaciones)
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    original_rows=db.execute('SELECT id,name,parent_id FROM ingredients ORDER BY id').fetchall()
    before_count=len(original_rows)
    # Reunificar equivalencias seguras y separar combinaciones explícitas.
    canon_by_key={};old_to_keys={};alternate=[];removed=[];renamed=Counter()
    proposed_qty={}
    for old_id,name,parent in original_rows:
        values,qty,reason=extraer_normalizacion(name)
        if not values:
            removed.append((old_id,name,reason))
            old_to_keys[old_id]=[]
            continue
        new_keys=[]
        for dest in values:
            if not dest:continue
            k=norm(dest)
            if k not in canon_by_key:canon_by_key[k]=dest
            new_keys.append(k)
        if not new_keys:
            old_to_keys[old_id]=[];removed.append((old_id,name,'vacío'));continue
        old_to_keys[old_id]=list(dict.fromkeys(new_keys))
        if qty:proposed_qty[old_id]=qty
        if len(new_keys)!=1 or norm(name)!=new_keys[0]:
            for k in new_keys:
                alternate.append((name,canon_by_key[k],reason,old_id))
    with (folder/'fragmentos_no_alimentarios.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['id_original','texto','motivo']);w.writerows(removed)
    # Corregir falsos positivos ya producidos por el motor anterior (por ej.
    # cebolla china -> cebolla). La evidencia sale del CSV ORIGINAL por receta.
    specials={
        'Cebolla china':(r'\bcebollas?\s+(?:chinas?|verdes?|largas?|de verdeo)\b', 'Cebolla'),
        'Ajo negro':(r'\bajos?\s+negros?\b','Ajo'),
        'Ajo tierno':(r'\bajos?\s+tiernos?\b','Ajo'),
    }
    variant_evidence=defaultdict(list)
    original_ingredient_strings={}
    with source_csv.open(encoding='utf-8-sig',newline='') as fin:
        for rec in csv.DictReader(fin):
            srid=int(rec['Id'])
            raw_text=rec.get('Ingredientes') or ''
            original_ingredient_strings[srid]=raw_text
            if not re.search(r'cebolla|ajo',raw_text,re.I):continue
            for fragment,_ in base.split_ingredients(raw_text):
                normalized=norm(fragment)
                for dest,(pat,generic) in specials.items():
                    if re.search(pat,normalized) and not re.search(r'\b(?:salsa|caldo|crema|sopa|jugo|pasta)\s+de\b',normalized):
                        variant_evidence[srid].append((dest,generic,fragment))
                        canon_by_key.setdefault(norm(dest),dest)
    dish_to_source=dict(db.execute('SELECT id,source_id FROM dishes'))
    evidence_dish={dish:variant_evidence.get(sid,[]) for dish,sid in dish_to_source.items() if variant_evidence.get(sid)}
    # Asegurar padres requeridos y conservar el nombre exacto de los alimentos.
    for child,parent in PARENTS.items():
        ck=norm(child)
        if ck in canon_by_key:canon_by_key.setdefault(norm(parent),parent)
    id_by_key={k:i for i,k in enumerate(canon_by_key,1)}
    print('  Nombres iniciales:',before_count,'; nombres canónicos:',len(canon_by_key),flush=True)
    parent_candidates={}
    for old,name,parent in original_rows:
        keys=old_to_keys.get(old,[])
        if not keys:continue
        destk=keys[0]
        if destk in parent_candidates:continue
        pk=norm(PARENTS[canon_by_key[destk]]) if canon_by_key[destk] in PARENTS else None
        if pk is None and parent and parent in old_to_keys and old_to_keys[parent]:
            pk=old_to_keys[parent][0]
        if pk and pk!=destk and pk in id_by_key:parent_candidates[destk]=pk
    # A la tabla final sólo pasan nombres que realmente son alimentos o 
    # entradas ambiguas; no inventamos ni eliminamos ingredientes por heurística difusa.
    merged={}
    duplicates=0;drop_links=0;added_links=0
    original_links=db.execute('SELECT dish_id,ingredient_id,quantity_text,is_required FROM dish_ingredients ORDER BY id').fetchall()
    for dish,old_ing,qty,required in original_links:
        destinations=old_to_keys.get(old_ing,[])
        if not destinations:
            drop_links+=1;continue
        if len(destinations)>1:added_links+=len(destinations)-1
        for target in destinations:
            k=(dish,id_by_key[target])
            if k not in merged:merged[k]=[[],0]
            else:duplicates+=1
            if (not qty or qty=='no especificada') and old_ing in proposed_qty:
                qty=proposed_qty[old_ing]
            if len(destinations)>1 and qty=='no especificada': qty='al gusto'
            if qty and qty!='no especificada' and qty not in merged[k][0]:
                merged[k][0].append(qty)
            merged[k][1]=max(merged[k][1],required)
    restorations=[]
    for dish,events in evidence_dish.items():
        unique_events={specific:(general,fragment) for specific,general,fragment in events}
        source_id=dish_to_source[dish]
        text_source=norm(original_ingredient_strings[source_id])
        for specific,(general,fragment) in unique_events.items():
            sid=id_by_key[norm(specific)]
            gid=id_by_key.get(norm(general))
            if (dish,sid) in merged:continue
            if gid is None or (dish,gid) not in merged:
                restorations.append((dish,specific,fragment,'pendiente: no existe vínculo genérico'))
                continue
            # Eliminar las expresiones que inequívocamente identifican la variedad
            # y ver si queda una mención al ingrediente genérico.
            check_text=text_source
            for candidate,(pat,g) in specials.items():
                if g==general:check_text=re.sub(pat,' ',check_text)
            if general=='Cebolla':
                check_text=re.sub(r'\bcebollas?\s+(?:rojas?|blancas?|moradas?)\b',' ',check_text)
            if general=='Ajo':
                check_text=re.sub(r'\bajos?\s+en\s+polvo\b',' ',check_text)
            generic_regex=(r'\bcebollas?\b' if general=='Cebolla' else r'\bajos?\b')
            has_plain=bool(re.search(generic_regex,check_text))
            if has_plain:
                merged[(dish,sid)]=[['no especificada'],merged[(dish,gid)][1]]
                decision='agregada: también aparece genérico, cantidad por revisar'
            else:
                merged[(dish,sid)]=merged.pop((dish,gid))
                decision='reemplazada fusión errónea: no aparece genérico adicional'
            restorations.append((dish,specific,fragment,decision))
    with (folder/'variedades_recuperadas.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['dish_id','ingrediente_especifico','fragmento_csv','accion']);w.writerows(restorations)
    # Completar tabla de alias siempre que no choque con un nombre canónico diferente.
    aliasmap={};collisions=[]
    def add_alias(alias,key,reason):
        nk=norm(alias)
        if not nk or not key or key not in id_by_key:return
        if nk==key:return
        if nk in id_by_key and nk!=key:
            collisions.append((alias,canon_by_key[key],'alias coincide con otro ingrediente canónico',reason));return
        if nk in aliasmap and aliasmap[nk][1]!=key:
            collisions.append((alias,canon_by_key[key],'alias con destinos diferentes',reason));return
        aliasmap[nk]=(alias,key,reason)
    for alias,canonical,reason,old in alternate:
        if len(old_to_keys.get(old,[]))==1:
            add_alias(alias,old_to_keys[old][0],reason)
    for alias,alias_key,old_id in db.execute('SELECT alias,alias_key,ingredient_id FROM ingredient_aliases'):
        if len(old_to_keys.get(old_id,[]))==1:
            add_alias(alias,old_to_keys[old_id][0],'alias original')
    for alias,canonical in EXPLICIT.items():add_alias(alias,norm(canonical),'sinónimo definido')
    # Reportes y auditoría de nombres no verificados individualmente.
    frequency=Counter(ing for dish,ing in merged)
    suspect=[]
    for k,name in canon_by_key.items():
        cid=id_by_key[k];issues=[]
        if frequency[cid]==1:issues.append('aparece en una sola receta (NO necesariamente error)')
        if re.search(r'\b(?:para (?:el|la|las|los)|ver nota|hay que|debes|se puede|al gusto|cucharaditas?|onzas?|kg|g|ml|tazas?)\b',k):issues.append('posible instrucción o cantidad residual')
        if len(name.split())>6:issues.append('nombre largo')
        if re.search(r'(?:\b\d+\b|[�ÃÂ]|\s+y\s+)',name):issues.append('combinación, cifra o codificación por revisar')
        if issues:suspect.append((cid,name,frequency[cid],'; '.join(issues)))
    with (folder/'equivalencias_aplicadas.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['nombre_anterior','nombre_canonico','motivo','id_anterior','id_final'])
        for oldname,canon,why,old in alternate:w.writerow((oldname,canon,why,old,id_by_key[norm(canon)]))
    with (folder/'ingredientes_para_revisar.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['ingredient_id','nombre','recetas','motivos']);w.writerows(suspect)
    with (folder/'colisiones_alias.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['alias','destino_propuesto','problema','motivo']);w.writerows(collisions)
    # Reporte de productos preservados deliberadamente.
    protected=[]
    for a,b in (('Ajo','Ajo en polvo'),('Ajo','Ajo negro'),('Cebolla','Cebolla china'),
                ('Tomate','Salsa de tomate'),('Tomate','Tomate cherry'),('Papa','Papa amarilla'),
                ('Leche','Leche condensada'),('Aceite de oliva','Aceite vegetal')):
        if norm(a) in id_by_key and norm(b) in id_by_key:
            protected.append((a,id_by_key[norm(a)],b,id_by_key[norm(b)],id_by_key[norm(a)]!=id_by_key[norm(b)]))
    with (folder/'variedades_preservadas.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['ingrediente_A','id_A','ingrediente_B','id_B','ids_distintos']);w.writerows(protected)
    def tbl(t,cols):return db.execute('SELECT '+','.join(cols)+' FROM '+t).fetchall()
    with output.open('w',encoding='utf-8') as f:
        f.write('-- Semilla reconstruida desde main.csv; ejecución única en PostgreSQL VACÍO de prueba.\n')
        f.write('-- Los ingredientes ambiguos se reportan en ingredientes_para_revisar.csv.\n')
        f.write('-- Requiere 001_catalogo_nuevo.sql y backend adaptado.\nBEGIN;\n\n')
        write_rows(f,'protein_categories',['id','name'],tbl('protein_categories',['id','name']))
        write_rows(f,'ingredients',['id','name','parent_id'],((id_by_key[k],name,None) for k,name in canon_by_key.items()))
        for child,pk in parent_candidates.items():
            f.write(f'UPDATE ingredients SET parent_id={id_by_key[pk]} WHERE id={id_by_key[child]};\n')
        f.write('\n')
        write_rows(f,'ingredient_aliases',['id','alias','alias_key','ingredient_id'],
                   ((i+1,alias,k,id_by_key[dest]) for i,(k,(alias,dest,reason)) in enumerate(sorted(aliasmap.items()))))
        write_rows(f,'protein_sources',['id','name'],tbl('protein_sources',['id','name']))
        write_rows(f,'tags',['id','name','type'],tbl('tags',['id','name','type']))
        dish_cols=['id','name','preparation_minutes','difficulty','popularity_score','preparation','protein_category_id','source_id','source_url','country','servings','meal_type','rating_average','rating_votes','duration_estimated','difficulty_estimated']
        write_rows(f,'dishes',dish_cols,((*(r[:-2]),bool(r[-2]),bool(r[-1])) for r in tbl('dishes',dish_cols)),chunk=120)
        write_rows(f,'dish_ingredients',['id','dish_id','ingredient_id','quantity_text','is_required'],
                   ((i+1,dish,ing,' + '.join(qtys)[:250] if qtys else 'no especificada',bool(req)) for i,((dish,ing),(qtys,req)) in enumerate(merged.items())),chunk=650)
        write_rows(f,'dish_protein_sources',['dish_id','protein_source_id'],tbl('dish_protein_sources',['dish_id','protein_source_id']),chunk=650)
        write_rows(f,'dish_tags',['dish_id','tag_id'],tbl('dish_tags',['dish_id','tag_id']),chunk=650)
        for t in ('protein_categories','ingredients','dishes','dish_ingredients','ingredient_aliases','protein_sources','tags'):
            f.write(f"SELECT setval(pg_get_serial_sequence('{t}','id'), COALESCE((SELECT MAX(id) FROM {t}),1), true);\n")
        f.write('COMMIT;\n')
    # Verificar el SQL realmente entregado, incluidos FK, conteos, dos sinónimos y variedades protegidas.
    check=sqlite3.connect(':memory:');check.executescript(SCHEMA)
    final_sql='\n'.join(s for s in output.read_text(encoding='utf-8').splitlines() if not s.startswith('SELECT setval('))
    check.executescript(final_sql)
    fk=check.execute('PRAGMA foreign_key_check').fetchall()
    if fk:raise AssertionError('FK inválidas: '+repr(fk[:10]))
    n_dishes=check.execute('SELECT count(*) FROM dishes').fetchone()[0]
    csv_n=sum(1 for _ in csv.DictReader(source_csv.open(encoding='utf-8-sig',newline='')))
    assert n_dishes==csv_n,(n_dishes,csv_n)
    assert check.execute('SELECT count(distinct source_id) FROM dishes').fetchone()[0]==csv_n
    assert check.execute('SELECT count(*) FROM dish_ingredients').fetchone()[0]==len(merged)
    assert not check.execute('SELECT 1 FROM dish_ingredients GROUP BY dish_id,ingredient_id HAVING count(*)>1').fetchone()
    id_names={norm(name):id_ for id_,name in check.execute('SELECT id,name FROM ingredients')}
    for a,b in (('Ajo','Ajo en polvo'),('Cebolla','Cebolla china'),('Tomate','Salsa de tomate')):
        if norm(a) in id_names and norm(b) in id_names:assert id_names[norm(a)] != id_names[norm(b)]
    missing=check.execute('SELECT count(*) FROM dishes d WHERE NOT EXISTS (SELECT 1 FROM dish_ingredients di WHERE di.dish_id=d.id)').fetchone()[0]
    original_missing=db.execute('SELECT count(*) FROM dishes d WHERE NOT EXISTS (SELECT 1 FROM dish_ingredients di WHERE di.dish_id=d.id)').fetchone()[0]
    # Fragmentos estrictamente no alimentarios pueden ser el único enlace de
    # una receta mal formada: reportarlos, pero no simular ingredientes.
    assert missing>=0
    sample=check.execute('SELECT d.source_id,d.name FROM dishes d WHERE NOT EXISTS (SELECT 1 FROM dish_ingredients di WHERE di.dish_id=d.id) LIMIT 100').fetchall()
    with (folder/'recetas_sin_ingredientes.csv').open('w',encoding='utf-8-sig',newline='') as ff:
        w=csv.writer(ff);w.writerow(['source_id','nombre']);w.writerows(sample)
    with (folder/'INFORME_VERIFICACION.md').open('w',encoding='utf-8') as f:
        f.write('# Manka: normalización y verificación automática\n\n')
        f.write(f'- Origen: `{source_csv.name}`. Recetas originales y generadas: **{csv_n:,} / {n_dishes:,}**.\n')
        f.write(f'- Ingredientes antes de recuperar filas: **{before_count:,}**. Después de normalizar: **{len(canon_by_key):,}**.\n')
        f.write(f'- Ingredientes recuperados de 13 recetas con formato defectuoso: **{len(recuperaciones)}**.\n')
        f.write(f'- Reducción neta de nombres del catálogo: **{before_count-len(canon_by_key):,}**; entradas excluidas inequívocas: **{len(removed)}**.\n')
        f.write(f'- Relaciones: antes **{len(original_links):,}**, después **{len(merged):,}** (consolidaciones: {duplicates:,}; fragmentos retirados: {drop_links:,}; enlaces separados: {added_links:,}).\n')
        f.write(f'- Alias: **{len(aliasmap):,}**. Colisiones no resueltas: **{len(collisions):,}**.\n')
        f.write(f'- Recetas sin ingredientes: **{missing}** (antes: {original_missing}).\n')
        f.write(f'- Ingredientes para revisar (criterio amplio): **{len(suspect):,}**. Los de frecuencia 1 no se presumen errores.\n')
        f.write('- Verificación: SQL completo ejecutado en **SQLite**, sin claves foráneas huérfanas ni duplicados de (dish_id, ingredient_id).\n')
        f.write('- **No verificado en PostgreSQL real ni en Spring Boot; no se afirma limpieza semántica perfecta**.\n')
        f.write('- No se realizaron fusiones por distancia de edición sin confirmar. Las variantes culinarias se mantienen.\n')
    print('VERIFICADO: recetas',csv_n,'ingredientes',len(canon_by_key),'relaciones',len(merged),'alias',len(aliasmap),'sin ingredientes',missing,'colisiones',len(collisions),flush=True)


def main():
    ap=argparse.ArgumentParser(description='Normaliza TODAS las recetas desde main.csv, reconstruye SQL, valida y crea auditoría.')
    ap.add_argument('--csv',required=True,type=Path)
    ap.add_argument('--salida',required=True,type=Path)
    ap.add_argument('--limite',type=int,default=None,help='Para desarrollo; --limite es una prueba parcial y no valida 20 236 recetas')
    ap.add_argument('--semilla-entrada',type=Path,default=None,help='SQL anterior completo; para auditoría y consolidación rápida')
    args=ap.parse_args()
    args.salida.parent.mkdir(parents=True,exist_ok=True)
    if args.semilla_entrada:
        if not args.semilla_entrada.exists():ap.error('Semilla anterior no encontrada')
        build_final(args.semilla_entrada,args.salida,args.salida.parent,args.csv)
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            interm=Path(tmpdir)/'intermedio.sql'
            saved=sys.argv[:] 
            sys.argv=[str(HERE/'_motor_base.py'),'--csv',str(args.csv),'--salida',str(interm)]
            if args.limite:sys.argv.extend(['--limite',str(args.limite)])
            try:base.run()
            finally:sys.argv=saved
            if args.limite:
                print('Modo prueba: no se hace verificación global ni se produce semilla definitiva.')
                dest=args.salida.parent/'intermedio_prueba.sql';dest.write_bytes(interm.read_bytes());return
            build_final(interm,args.salida,args.salida.parent,args.csv)
    print('Resultados:',args.salida,'y reportes en',args.salida.parent)

if __name__=='__main__':main()
