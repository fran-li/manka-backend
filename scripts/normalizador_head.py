"""Extrae sustantivo principal de nombres alimentarios. Reglas conservadoras.
No pretende ser etiquetado gramatical completo ni sustituye la revisión humana.
"""
import re

# Productos procesados y preparados mantienen identidad, aunque incluyan el nombre
# de un ingrediente fresco. Las listas de variantes se pueden seguir ampliando.
PROTECTED = [
 r'\b(?:salsa|sopa|caldo|consome|pur[eé]|mermelada|jarabe|gelatina|pasta|harina|almid[oó]n|f[eé]cula|aceite|vinagre|leche|crema|yogur|mantequilla|jugo|zumo|extracto|esencia)\s+de\s+',
 r'\b(?:leche\s+condensada|leche\s+evaporada|leche\s+en\s+polvo|ajo\s+en\s+polvo|cebolla\s+en\s+polvo|tomate\s+frito|papa\s+frita|pan\s+rallado|queso\s+crema|arroz\s+inflado)\b',
]
COMPILED_PROTECTED=[re.compile(p) for p in PROTECTED]

# Canonización de sustantivos que no estaban cubiertos por el motor anterior.
# Patrones se buscan a nivel de palabra. El primer token nominal suele dominar,
# excepto las combinaciones explícitas de varios ingredientes.
NOUNS = [
('Verduras',r'\b(?:vegetales?|verduras?|hortalizas?|mix\s+de\s+vegetales?|ensalada\s+de\s+vegetales?)\b'),
('Especias',r'\b(?:especias?|condimentos?\s+variados?)\b'),
('Hierbas',r'\b(?:hierbas?\s+(?:frescas?|secas?|arom[aá]ticas?|finas?)|finas?\s+hierbas?)\b'),
('Batata',r'\b(?:batatas?|boniatos?|camotes?)\b'),
('Betarraga',r'\b(?:betabel(?:es)?|betarragas?|remolachas?)\b'),
('Alcachofa',r'\balcachofas?\b'),
('Arveja',r'\b(?:arverjitas?|arverjas?|arvejitas?)\b'),
('Brócoli',r'\b(?:br[oó]culi|br[oó]coli)\b'),
('Tomatillo',r'\b(?:to\s*matillos?|tomatillos?)\b'),
('Tomate',r'\b(?:to\s+mate|jitomate)\b'),
('Queso',r'\bquesillos?\b'),
('Col',r'\b(?:col|coles)\b'),
('Jalapeño',r'\bjalape[nñ]os?\b'),
('Pepinillo',r'\bpepinillos?\b'),
('Guayaba',r'\bguayabas?\b'),
('Anís',r'\ban[ií]s\b'),
('Café',r'\bcaf[eé]s?\b'),
('Té',r'\bt[eé]\b'),
('Galleta',r'\bgalletas?\b'),
('Jerez',r'\bjerez\b'),
('Vino',r'\bvin[oa]s?\b'),
('Ron',r'\bron\b'),
('Brandy',r'\bbrandy\b'),
('Vodka',r'\bvodka\b'),
('Piloncillo',r'\bpiloncillos?\b'),
('Vainilla',r'\bvainilla\b'),
('Jícama',r'\bj[ií]camas?\b'),
('Tamarindo',r'\btamarindos?\b'),
('Alcachofa',r'\balcachofas?\b'),
('Cereza',r'\bcerezas?\b'),
('Pecana',r'\bpecanas?\b'),
('Rúcula',r'\br[uú]culas?\b'),
('Chía',r'\bch[ií]as?\b'),
('Sésamo',r'\b(?:s[eé]samo|ajonjol[ií])\b'),
('Linaza',r'\b(?:linaza|semillas?\s+de\s+lino)\b'),
('Ricota',r'\b(?:ricota|ricotta|reques[oó]n)\b'),
('Mozzarella',r'\bmozzarellas?\b'),
('Tofu',r'\btofu\b'),
('Soja',r'\b(?:soja|soya)\b'),
('Masa',r'\bmasa\b'),
('Sémola',r'\bs[eé]mola\b'),
('Cuscús',r'\b(?:cusc[uú]s|cous\s*cous)\b'),
('Alga',r'\balgas?\b'),
('Mariscos',r'\bmariscos?\b'),
('Bogavante',r'\bbogavantes?\b'),
('Langosta',r'\blangostas?\b'),
('Jaiba',r'\bjaibas?\b'),
('Cangrejo',r'\bcangrejos?\b'),
('Ostra',r'\bostras?\b'),
('Vieira',r'\bvieiras?\b'),
('Caracol',r'\bcaracoles?\b'),
('Corvina',r'\bcorvinas?\b'),
('Trucha',r'\btruchas?\b'),
('Lomo',r'\blomos?\b'),
('Carne',r'\bcarne(?:s)?\b'),
('Morcillo',r'\bmorcillo\b'),
('Salchichón',r'\bsalchich[oó]n\b'),
('Morcilla',r'\bmorcillas?\b'),
('Chicharrón',r'\bchicharrones?\b'),
('Manteca',r'\bmantecas?\b'),
('Crema',r'\bcrema\b'),
('Soda',r'\b(?:soda|gaseosa|refresco)\b'),
('Gaseosa',r'\bgaseosas?\b'),
('Cacao',r'\bcacao\b'),
('Bicarbonato',r'\bbicarbonato\b'),
('Edulcorante',r'\b(?:edulcorante|endulzante)\b'),
('Miel de caña',r'\bmiel\s+de\s+ca[nñ]a\b'),
('Ciruela',r'\bciruelas?\b'),
('Granada',r'\bgranadas?\b'),
('Chirimoya',r'\bchirimoyas?\b'),
('Higo',r'\bhigos?\b'),
('Dátil',r'\bd[aá]tiles?\b'),
('Maíz',r'\b(?:ma[ií]z|elote|choclo)\b'),
('Aceite',r'\baceite\b'),
]

# Vocabulario ampliado: nombres principales que aparecían en descripciones.
# Las expresiones más específicas siempre anteceden al nombre general.
EXTRA_NOUNS = [
('Puerro',r'\b(?:puerros?|poros?)\b'),
('Yuca',r'\byucas?\b'),
('Papa',r'\b(?:patatas?|papas?)\b'),
('Frijol',r'\b(?:fr[eé]joles?|fr[ií]joles?|habichuelas?|jud[ií]as?\s+(?:verdes|blancas|rojas))\b'),
('Arveja',r'\b(?:alberjas?|alverjas?|arvejitas?)\b'),
('Cebolla',r'\b(?:cebollitas?|cebollla|ceboll)\b'),
('Ajo',r'\b(?:ajitos?|ajos?)\b'),
('Pan',r'\bpanes\b'),
('Fideo',r'\b(?:noodles?|fideos?)\b'),
('Cerveza',r'\bcervezas?\b'),
('Sidra',r'\bsidras?\b'),
('Pisco',r'\bpisco\b'),
('Vermut',r'\b(?:vermut|vermouth)\b'),
('Licor',r'\blicores?\b'),
('Ginebra',r'\bginebra\b'),
('Hueso',r'\bhuesos?\b'),
('Pimiento',r'\b(?:pimientos?|morrones?)\b'),
('Colorante',r'\bcolorantes?\b'),
('Hojaldre',r'\bhojaldre\b'),
('Achiote',r'\bachiotes?\b'),
('Guindilla',r'\bguindillas?\b'),
('Cardamomo',r'\bcardamomo\b'),
('Cordero',r'\bcorderos?\b'),
('Bonito',r'\bbonito\b'),
('Mero',r'\bmeros?\b'),
('Lenguado',r'\blenguados?\b'),
('Erizo de mar',r'\berizos?\s+de\s+mar\b'),
('Sazonador',r'\bsazonadores?\b'),
('Frutas',r'\bfrutas?\b'),
('Frutos secos',r'\bfrutos?\s+secos?\b'),
('Zarzamora',r'\bzarzamoras?\b'),
('Damasco',r'\bdamascos?\b'),
('Lúcuma',r'\bl[uú]cumas?\b'),
('Jamaica',r'\bjam[aá]ica\b'),
('Pallar',r'\bpallares?\b'),
('Semillas',r'\bsemillas?\b'),
('Grenetina',r'\bgrenetinas?\b'),
('Gelatina',r'\bgelatinas?\b'),
('Cuajada',r'\bcuajadas?\b'),
('Provolone',r'\bprovolones?\b'),
('Queso',r'\bquesillos?\b'),
('Hígado',r'\bh[ií]gados?\b'),
('Bistec',r'\b(?:bistecs?|bifes?)\b'),
('Chuleta',r'\bchuletas?\b'),
('Jalea',r'\bjaleas?\b'),
('Carne',r'\b(?:pulpa\s+de\s+res|carne\s+picada)\b'),
('Pimienta',r'\b(?:pimenta|pimen[oó]on)\b'),
('Páprika',r'\bpaprika\b'),
('Nata',r'\bnata\b'),
('Pimentón',r'\bpiment[oó]n\b'),
('Sirope',r'\bsiropes?\b'),
('Mermelada',r'\bmermeladas?\b'),
('Pastilla de caldo',r'\bpastillas?\s+de\s+caldo\b'),
('Aderezo',r'\baderezos?\b'),
('Tofu',r'\btofu\b'),
('Sake',r'\bsake\b'),
('Lima',r'\blimas?\b'),
('Limón',r'\blimones?\b'),
('Curry',r'\bcurry\b'),
('Aguacate',r'\b(?:palta|aguacate)\b'),
]
NOUNS=EXTRA_NOUNS+NOUNS

NOUNS=[(label,re.compile(rx)) for label,rx in NOUNS]

# Cabeceras, notas y utensilios no deben transformarse en ingredientes.
NON_FOOD = re.compile(r'\b(?:cuchillo|tabla\s+de\s+cortar|termomix|thermomix|horno|licuadora|servilleta|papel\s+film|palillos?\s+de\s+madera|bolsa\s+de\s+pl[aá]stico|para\s+aderezar|al\s+gusto|en\s+caso\s+que|si\s+deseas|te\s+gusta|comenzamos)\b')
START_NOISE = re.compile(r'^(?:(?:\d+[\s/½¼¾.]*)|(?:una?|unos?|otras?|varias?|aprox|aproximadamente|de|un|las?|los?|copa|copas|copita|cucharadita|cucharadas?|taza|tazas|pu[nñ]ado|pizca|pellizco|libra|libras|kg|g|ml|litros?|kilo|gramos?|bandeja|bote|bolsa|lata|trozo|trozos|pedazo|pedazos|ramillete|hojas|hojitas|rodajas|rebanadas|chorro|caja|vaso|vasos|medida|porci[oó]n|porciones|cent[ií]metros|cubicos|c[uú]bicos)\s+(?:de\s+)?)+')
MIXED=re.compile(r'[,;]|\s+(?:y|u|o)\s+')
NO_FOOD_EXACT={'tiernos y','limpio','enjuagada y seca','para el pollo','para el relleno','para las albondigas','para el guiso','corte largo en cuatro pedazos cada uno'}

def normalize_extra(name, base_fn, key_fn, known_patterns=None):
    """Devuelve (nombre genérico, motivo, seguridad) o delega al motor anterior.
    No confunde dos ingredientes de una lista ni productos preparados.
    """
    k=key_fn(name)
    if not k: return base_fn(name)
    if k in NO_FOOD_EXACT or NON_FOOD.search(k) and not re.search(r'\b(?:sal|pimienta|ajo)\b',k):
        return None,'no alimentario / nota',False
    # Enumeraciones con dos alimentos reales: NO inventar una sola identidad.
    # Se evalúan antes del motor anterior, que en ciertos casos reconocía solo
    # uno de los alimentos presentes en una frase como «arroz y mariscos».
    if MIXED.search(k) and known_patterns:
        segments=[part.strip() for part in MIXED.split(k) if part.strip()]
        classes=[]
        for segment in segments:
            present=[]
            for label, rx in known_patterns:
                if rx.search(segment):present.append(label)
            for label, rx in NOUNS:
                if rx.search(segment):present.append(label)
            if present:classes.append(present[0])
        if len(set(classes))>1:
            return name,'lista de varios alimentos; separar manualmente',False
    # Algunas variedades son alimentos independientes, no errores del nombre
    # genérico más frecuente (tomatillo no es tomate).
    if re.search(r'\b(?:tomatillos?|to\s+matillos?)\b',k):
        return 'Tomatillo','variedad alimentaria independiente reconocida',True
    # Productos rellenos/embutidos: el nombre principal describe el producto;
    # su relleno o procedencia quedan en el detalle original de la receta.
    head_compounds=[(r'^aceitunas?\s+rellenas?\s+de\b','Aceituna'),
                    (r'^chorizos?\s+de\s+(?:cerdo|res|pollo)\b','Chorizo'),
                    (r'^jam[oó]n\s+de\s+(?:pavo|cerdo|pollo)\b','Jamón')]
    for expr,head in head_compounds:
        if re.search(expr,k):return head,'sustantivo principal del producto',True
    # «de buena calidad» no es una variedad ni un ingrediente adicional.
    generic_quality=re.match(r'^(aceite|vinagre|caldo|crema|leche|harina)\s+de\s+(?:buena\s+calidad|calidad|la\s+mejor\s+calidad|tu\s+preferencia)\b',k)
    if generic_quality:
        h=generic_quality.group(1).capitalize()
        return h,'sustantivo principal sin calificativo de calidad',True
    # Procesar primero las equivalencias específicas ya verificadas.
    base_family,base_reason,base_safe=base_fn(name)
    if base_safe or base_family is None:
        return base_family,base_reason,base_safe
    # No reducir a materia prima las preparaciones claramente transformadas.
    if any(p.search(k) for p in COMPILED_PROTECTED):
        # Excepción: leche como alimento con calificativo genérico no transformado.
        if k.startswith(('mezcla de vegetales','mezcla de verduras')):
            return 'Verduras','sustantivo núcleo: vegetales/verduras',True
        return base_family,base_reason,base_safe
    # Caso solicitado: mezcla de vegetales, verduras y hortalizas -> Verduras.
    if re.search(r'\b(?:vegetales?|verduras?|hortalizas?)\b',k):
        # Importa cuál es el núcleo del producto: «pastilla de caldo
        # concentrado de verduras» es Caldo de verduras, NO Verduras.
        pre=re.split(r'\b(?:vegetales?|verduras?|hortalizas?)\b',k,1)[0]
        processed=[('caldo','Caldo de verduras'),('sopa','Sopa de verduras'),
                   ('crema','Crema de verduras'),('salsa','Salsa de verduras')]
        for word,product in processed:
            if re.search(r'\b'+word+r'\b',pre) and not re.search(r'\bpara\b',pre):
                return product,'preparación con verduras (identidad protegida)',True
        return 'Verduras','sustantivo principal y sinónimo: vegetales → verduras',True
    # Las enumeraciones de alimentos no representan un solo ingrediente.
    # Sal y pimienta se deberá separar en otra etapa; no convertir a "Sal".
    if MIXED.search(k) and base_reason=='combinación de alimentos: revisión':
        # Si se trata de una alternativa del mismo ingrediente (e.g. tilapia u otro pescado),
        # mejor mantenerla pendiente que inventar equivalencias.
        return base_family,base_reason,base_safe
    clean=START_NOISE.sub('',k).strip()
    clean=re.sub(r'^\d+[\s\./-]*','',clean).strip()
    clean=re.sub(r'^(?:de|del|el|la|los|las|para)\s+','',clean)
    if not clean: return base_family,base_reason,base_safe
    # Determinamos el núcleo dentro de las primeras palabras, no de notas
    # procedimentales al final de la descripción.
    core=re.split(r'\b(?:para|al\s+gusto|a\s+gusto|cortad[oa]s?|picad[oa]s?|pelad[oa]s?)\b',clean,1)[0].strip()
    if not core:core=clean
    hits=[]
    for lab,pat in NOUNS:
        m=pat.search(core)
        if m and m.start()<=max(28,len(core)//2):hits.append((m.start(),lab))
    if not hits:return base_family,base_reason,base_safe
    hits.sort(key=lambda a:a[0])
    first=hits[0][1]
    # Cuidado con productos con ingredientes alternativos o mezclas reales.
    uniq={lab for _,lab in hits}
    if len(uniq)>1 and MIXED.search(core):
        return base_family,'varios ingredientes: revisión, no fusionar',False
    return first,'sustantivo principal reconocido y equivalente',True
