# Manka — Backend actualizado y migración de `main.csv` a PostgreSQL

Esta carpeta es una **copia modificada** de `manka-main.zip`. No cambia ningún despliegue remoto. Se conservaron los controladores de autenticación, despensa, favoritos, historial y sus rutas públicas existentes.

## 1. Qué cambió realmente

| Elemento | Antes | Ahora |
|---|---|---|
| `dishes.name` | UNIQUE (impedía dos recetas con el mismo nombre) | No único; `id` es la PK y `source_id` identifica el registro del CSV |
| Datos de receta | Nombre, tiempo, dificultad, etc. | Se añaden `source_id`, `source_url`, `country`, `servings`, `meal_type`, `rating_average`, `rating_votes` |
| Datos faltantes | Se inventaban 45 min, FACIL, puntuación 80 | Tiempo y dificultad pasan a `NULL`; la popularidad usa puntaje neutro 50 sin valoración |
| Ingredientes | Catálogo y padre | Continúa igual + `ingredient_aliases` para sinónimos explícitos + padres conocidos |
| Proteínas | Una sola categoría | Se mantiene por compatibilidad + `protein_sources`/`dish_protein_sources` (múltiples) |
| Otras categorías | Sin clasificación adicional | `tags`/`dish_tags` almacena `SOURCE_CATEGORY`, `MEAL`, `NUTRITION_SOURCE`; son etiquetas de origen, no certificados dietéticos |
| Listado | `GET /dishes`, `GET /ingredients` sin paginación | Rutas nuevas `/dishes/page`, `/ingredients/page`; las antiguas siguen entregando arrays |
| Recomendación | Consulta todos los candidatos por tiempo | PostgreSQL filtra primero por tiempo + ingredientes compartidos; luego Java puntúa |
| Carga al arrancar | `data.sql` se reejecutaba siempre | SQL autoinicialización desactivado por defecto (variable `SQL_INIT_MODE=never`) |

> **Límites**: 25 658 ingredientes siguen siendo detecciones heurísticas. El convertidor no puede garantizar correspondencia gastronómica exacta. Unas 13 195 recetas quedaron con categoría principal «Otros»; revisar `auditoria_recetas.csv`. Las recetas con duración `NULL` no entran en recomendaciones basadas en tiempo (sí aparecen en el catálogo). No afirmar que se realizó una migración en PostgreSQL real.

## 2. Cómo generar el SQL otra vez en VS Code

Se entrega el archivo original `database/source/main.csv`. Desde la raíz del proyecto:

```bash
python scripts/convertir_manka.py --csv database/source/main.csv --salida database/seed/manka_seed.sql
```

Se generan `manka_seed.sql` y reportes `auditoria_ingredientes.csv`, `auditoria_recetas.csv`, `fragmentos_descartados.csv` dentro de `database/seed/`.

El script **solo lee el CSV**. No copia recetas de `data_legacy_212.sql`. Los IDs internos empiezan en 1; conserva la columna original `Id` como `source_id`. Está hecho para una **base nueva**.

Para un ensayo pequeño:

```bash
python scripts/convertir_manka.py --csv database/source/main.csv --limite 10 --salida database/seed/prueba_10.sql
```

### Comprobar el SQL sin PostgreSQL

```bash
python scripts/validar_semilla.py database/seed/manka_seed.sql
```

El validador utiliza SQLite solo para revisar número de filas, unicidad y claves foráneas; **no equivale a probar Spring Boot y PostgreSQL**.

## 3. Importación recomendada: BASE NUEVA de PostgreSQL

**No uses todavía la base de Railway que ya contiene usuarios y datos de producción.** Si quieres conservar tus usuarios/contraseñas, primero planifica una migración específica; crear una base nueva no los copia.

1. Crea una base de datos vacía (por ejemplo, `manka_pruebas`) en PostgreSQL local / pgAdmin o en un servicio de pruebas.
2. En el Query Tool de pgAdmin, selecciona esa base y ejecuta `database/migrations/001_catalogo_nuevo.sql` para crear el catálogo.
3. Como el archivo SQL es grande (decenas de MB), importa con **psql** en la terminal (cambia parámetros según tu instalación):

```bash
psql -h localhost -p 5433 -U postgres -d manka_pruebas \
  -v ON_ERROR_STOP=1 -1 -f database/seed/manka_seed.sql
```

`-1` intenta la importación en una sola transacción. Si falla alguna instrucción, no se debe dar por completada. El generador nuevo no usa `ON CONFLICT DO NOTHING`, porque escondería errores de importación.

4. Comprueba los datos:

```sql
SELECT COUNT(*) FROM dishes; -- esperado: 20236
SELECT COUNT(*) FROM ingredients; -- esperado: 25658
SELECT COUNT(*) FROM dish_ingredients; -- esperado: 173368
SELECT COUNT(*) FROM ingredient_aliases; -- esperado: 64
SELECT COUNT(*) FROM dishes WHERE preparation_minutes IS NULL; -- 6630 aprox.
SELECT COUNT(*) FROM dishes WHERE difficulty IS NULL; -- 6454 aprox.
SELECT source_id, name FROM dishes ORDER BY id LIMIT 10;
SELECT i.name, p.name AS parent FROM ingredients i LEFT JOIN ingredients p ON p.id=i.parent_id WHERE p.id IS NOT NULL LIMIT 10;
```

5. Configura la nueva base en el backend. Puedes establecer `DB_URL=jdbc:postgresql://localhost:5433/manka_pruebas`, `DB_USERNAME`, `DB_PASSWORD`. Arranca `./mvnw spring-boot:run` (`mvnw.cmd spring-boot:run` en CMD Windows), lo que creará también las tablas de usuario/sesión con JPA.
6. Desde Postman, registra un usuario con `POST /users/register`, inicia sesión con `POST /auth/login` y usa el JWT en las peticiones siguientes.

No cometas contraseñas ni URLs de bases privadas en GitHub. La clave RSA de ejemplo incluida en el proyecto original debe rotarse en despliegues reales.

### Si prefieres actualizar una base EXISTENTE

Se incluye `database/migrations/002_actualizacion_existente_OPCIONAL.sql` para cambiar las columnas y eliminar el UNIQUE de `dishes.name`, **pero NO incorpora el nuevo catálogo en la misma base**. Hacerlo junto a los IDs anteriores requeriría mapear las referencias a usuarios, favoritos y el historial, por lo que no se hace automáticamente.

## 4. Postman: endpoints nuevos y antiguos

Importa `Manka-Mejorado.postman_collection.json`. Cambia `baseUrl`, `email`, `password` y ejecuta primero Login. Postman guarda el `token` como `accessToken`. Los endpoints de catálogo **siguen protegidos por JWT**.

**Nuevo (paginado)**

```http
GET /dishes/page?page=0&size=20&search=pollo
GET /dishes/page?page=1&size=20&maxMinutes=45
GET /ingredients/page?page=0&size=20&search=jitomate
GET /dishes/{id}
```

Los endpoints `/page` devuelven un objeto paginado con `content`, `totalElements`, `totalPages`, etc. `GET /dishes/{id}` añade metadatos, tags y fuentes de proteína.

**Se mantienen**

```http
GET /dishes?search=pollo&maxMinutes=30
GET /ingredients?search=tomate
POST /recommendations
PUT /pantry
```

`GET /dishes` sin filtros y `GET /ingredients` sin filtro conservan las respuestas antiguas (arrays) pero pueden ser pesadas con 20 mil recetas. Prefiere `/page` en apps nuevas. Las colecciones antiguas de Postman usan IDs fijos del catálogo de 212 recetas: **no son válidas como pruebas de datos para el catálogo nuevo**.

### Verificar recomendaciones con IDs reales

1. `GET /ingredients/page?search=jitomate&page=0&size=10` debe devolver `Tomate` con ID real del catálogo.
2. Utiliza ese ID en:

```json
{
  "ingredientIds": [2],
  "availableMinutes": 60,
  "limit": 10
}
```

El `2` es solamente un ejemplo: reemplázalo con el valor obtenido del primer endpoint. No supongas que el `id=1` sea `Pollo` en el nuevo CSV.

## 5. Validación y límites pendientes

- Se ejecutó el SQL completo en una base de pruebas **SQLite** con el mismo modelo de claves primarias, foráneas y relaciones; no hubo referencias huérfanas.
- No fue posible ejecutar `./mvnw test` ni un PostgreSQL real desde el entorno de generación: se requiere conexión para dependencias de Maven y un Docker para Testcontainers.
- Las recomendaciones aún pueden necesitar ajustes de desempeño según memoria, índices y carga; el nuevo filtro previo limita candidatos pero no sustituye pruebas de carga.
- La clasificación de proteínas y las etiquetas dietéticas inferidas no son una certificación fiable. Revisa los reportes de CSV antes de usar información dietética como filtro de seguridad.
- El archivo legacy `database/seed/data_legacy_212.sql` queda para comparar o probar; solo se activa automáticamente en el **classpath de tests** para conservar las pruebas antiguas.

## 6. Comprobaciones para la próxima iteración

```bash
./mvnw test
./mvnw spring-boot:run
```

Las pruebas de integración usan Testcontainers, por lo que requieren Docker disponible. Para comprobar Maven sin ejecutar las pruebas: `./mvnw -DskipTests package`.
