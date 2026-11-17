# Manka — ingredientes genéricos con variante por receta

## Objetivo

`Papa`, `Papa roja`, `Papa amarilla`, `Papa blanca` comparten un solo
`ingredients.id` (en esta ejecución ID=12), conservando su variedad en
`dish_ingredients.ingredient_detail`. No se mezclan automáticamente productos
elaborados como Salsa de tomate, Pasta de tomate, Papa frita o Ajo en polvo.

## Archivos

- `database/seed/manka_seed_familias.sql`: datos completos, SOLO para catálogo vacío.
- `database/migrations/003_catalogo_familias_SOLO_BD_NUEVA.sql`: crea tablas en PostgreSQL **nuevo y vacío**. NO es ALTER ni migración incremental.
- `database/source/main.csv`: datos originales, fuente de verdad.
- `database/intermediate/manka_seed_normalizado.sql`: resultado intermedio generado del CSV, necesario para repetir rápidamente la fase de familias.
- `scripts/convertir_a_familias.py`: agrupación en familias y construcción del SQL.
- `scripts/verificar_familias.py`: validación SQLite contra el CSV original.
- `scripts/normalizar_y_verificar.py`, `scripts/_motor_base.py`: fase previa del CSV; se pueden usar para generar semilla intermedia nueva.
- `database/seed/catalogo_generico.csv`: ingredientes/IDs y frecuencia.
- `database/seed/equivalencias_familias.csv`: mapeo de nombres de la versión anterior a IDs nuevos.
- `database/seed/ambiguedades.csv`: casos por revisar antes de producción.
- `database/seed/ejemplos_agrupacion.csv`: demostración de familias compartidas.

## Repetir conversión en VS Code / Git Bash

En la carpeta `backend-manka`:

```bash
python scripts/convertir_a_familias.py \
  --semilla database/intermediate/manka_seed_normalizado.sql \
  --csv database/source/main.csv \
  --salida database/seed
```

Esto NO requiere API ni suscripción distinta de Python. Si se modifica `main.csv`,
primero debe regenerarse la semilla intermedia (con el conversor de la fase 1):

```bash
python scripts/normalizar_y_verificar.py \
  --csv database/source/main.csv \
  --salida database/intermediate/manka_seed_normalizado.sql
```

El proceso completo genera a partir del CSV; el archivo intermedio incluido
está únicamente para ahorrar repetir la fase más lenta con el mismo CSV.

**Validación**: desde `backend-manka` el validador busca `equivalencias_familias.csv`
aliado a su script. Se puede ejecutar desde la carpeta de trabajo inicial
(donde los scripts e informes están juntos) o copiar `database/seed/equivalencias_familias.csv`
a `scripts/` y ejecutar:

```bash
python scripts/verificar_familias.py database/seed/manka_seed_familias.sql database/source/main.csv
```

## PostgreSQL: cargar SOLO en una base NUEVA de prueba

Usa `psql` y una base de prueba vacía, sin ejecutar primero las migraciones viejas:

```bash
psql -h localhost -U postgres -d manka_test -v ON_ERROR_STOP=1 \
  -f database/migrations/003_catalogo_familias_SOLO_BD_NUEVA.sql
psql -h localhost -U postgres -d manka_test -v ON_ERROR_STOP=1 \
  -f database/seed/manka_seed_familias.sql
```

Después comprueba:

```sql
SELECT COUNT(*) FROM dishes;             -- 20236
SELECT COUNT(*) FROM ingredients;        -- 10075 (incluye no clasificados)
SELECT COUNT(*) FROM dish_ingredients;   -- 168653
SELECT id,name FROM ingredients WHERE name='Papa';
SELECT di.quantity_text, di.ingredient_detail, i.name
FROM dish_ingredients di JOIN ingredients i ON i.id=di.ingredient_id
WHERE i.name='Papa' LIMIT 15;
```

## Respuesta HTTP que cambia

`GET /dishes/{id}` conserva `ingredienteId`, `nombre`, `cantidad`, `obligatorio`
y añade **`detalle`**, con variedad específica, cuando corresponde.

### Limitaciones reales

- 10 075 IDs NO representan 10 075 ingredientes genuinamente distintos:
  muchos son nombres **provisionales** que no se pudieron interpretar con certeza.
- Hay 10 018 entradas antiguas marcadas para revisión; no necesariamente todas
  son incorrectas. Consulta `ambiguedades.csv` para decidir qué fusionar.
- No se verificó en PostgreSQL real ni compiló Spring Boot con Maven aquí.
  Se verificó en SQLite y se analizaron los archivos Java sintácticamente.
- Unos ingredientes no alimentarios se excluyen del catálogo, sin perder su
  texto original: `dishes.source_ingredients_text` contiene íntegro el CSV.
- El parser inicial puede producir cantidades imperfectas. El detalle y
  `source_ingredients_text` permiten corregirlas manualmente.
- La categoría de proteína `Otros` sigue siendo provisional para muchas recetas.
- **No importar sobre Railway ni sobre una base con datos existentes**:
  los IDs se reconstruyen y las relaciones con la despensa y favoritos
  existentes se perderían si se reemplazan sin migración de datos de usuario.
