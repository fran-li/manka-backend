# Manka — sustantivos principales y equivalencias

## Qué hace esta versión

Se ejecutó sobre **20 236 recetas originales**. Usa la semilla intermedia derivada íntegramente de `main.csv` (NO copia las 212 recetas del viejo data.sql). Unifica cantidades, calificativos, grafías y sinónimos de alimentos reconocibles bajo un ID genérico.

**Ejemplo**: `1 taza de mezcla de vegetales para guiso` → familia `Verduras`. En cada receta se conserva el ingrediente escrito originalmente en `dish_ingredients.ingredient_detail` y, además, el texto íntegro original del CSV en `dishes.source_ingredients_text`.

Los productos elaborados se diferencian de su materia prima: `Tomate` ≠ `Salsa de tomate`; `Verduras` ≠ `Caldo de verduras`; `Ajo` ≠ `Ajo en polvo`. `Tomatillo` se trata como un alimento diferente de `Tomate`.

## Resultado comprobado

- Recetas: 20 236
- Familias / nombres provisionales (`ingredients`): 7 306 (antes: 10 075)
- Relaciones receta-ingrediente: 168 336
- Alias: 18 281
- Referencias huérfanas / pares receta-ingrediente repetidos: **0**, validados con SQLite.
- Nombres de la semilla intermedia no resueltos automáticamente: **7 166** (son textos originales marcados para revisión; NO 7 166 errores confirmados ni necesariamente 7 166 IDs).

Este resultado **no** demuestra que haya 7 306 alimentos semánticamente distintos, ni que las cantidades o los sinónimos sean perfectos. Tampoco se ha probado contra PostgreSQL real ni compilado Maven.

Cuando una cadena contiene *varios ingredientes diferentes* (`arroz y mariscos`, `sal y pimienta`), el programa **no selecciona solo uno** arbitrariamente. Los deja para revisión; el siguiente perfeccionamiento sería descomponer esas cadenas en varias relaciones.

## Cómo utilizarlo en VS Code, Git Bash

Abre la carpeta principal del backend (`backend-manka`) y ejecuta desde allí:

```bash
python scripts/convertir_a_familias.py \
  --semilla database/intermediate/manka_seed_normalizado.sql \
  --csv database/source/main.csv \
  --salida database/seed
```

Luego verifica:

```bash
python scripts/verificar_familias.py database/seed/manka_seed_familias.sql database/source/main.csv
```

Para regenerar la *semilla intermedia* desde un CSV diferente, primero ejecuta el script previo:

```bash
python scripts/normalizar_y_verificar.py \
  --csv database/source/main.csv \
  --salida database/intermediate/manka_seed_normalizado.sql
```

El `manka_seed_familias.sql` ya está generado. No necesitas ejecutar esos comandos para descargar/usar la semilla incluida.

## Importar a PostgreSQL

**Solo en una BD nueva de prueba** y vacía. NO usar sobre Railway ni sobre una base de datos con usuarios, historial y despensas existentes; los IDs de ingredientes cambian.

```bash
psql -h localhost -U postgres -d manka_test -v ON_ERROR_STOP=1 \
  -f database/migrations/003_catalogo_familias_SOLO_BD_NUEVA.sql
psql -h localhost -U postgres -d manka_test -v ON_ERROR_STOP=1 \
  -f database/seed/manka_seed_familias.sql
```

Ejemplo de búsqueda por IDs:

```sql
SELECT id, name FROM ingredients WHERE name='Verduras';
SELECT di.dish_id, i.name AS ingrediente_generico, di.ingredient_detail,
       di.quantity_text
FROM dish_ingredients di JOIN ingredients i ON i.id=di.ingredient_id
WHERE i.name='Verduras'
LIMIT 20;
```

## Archivos de auditoría

- `database/seed/equivalencias_familias.csv`: cada nombre anterior, sustantivo/familia asignada, ID y grado de seguridad.
- `database/seed/catalogo_generico.csv`: los IDs y la cantidad de recetas que los usan.
- `database/seed/ambiguedades.csv`: nombres no interpretados de forma fiable.
- `database/seed/alias_ambiguos.csv`: conflictos de alias.

El script se diseñó sin dependencias externas ni llamadas a la API de IA. En caso de encontrar errores, añade una equivalencia verificada al módulo `scripts/normalizador_head.py` y repite la conversión.
