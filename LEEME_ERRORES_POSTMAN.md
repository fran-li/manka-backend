# Reparación de Postman — Manka (estado recibido en revisar.zip)

## Causas diagnosticadas

1. La base configurada es `jdbc:postgresql://localhost:5433/manka` (mismo valor en `.env`).
2. `src/main/resources/data.sql` contiene la semilla final de ingredientes y recetas, pero `spring.sql.init.mode=never`; **no se carga automáticamente**.
3. Los endpoints `/ingredients/page` y `/dishes/page` usaban JPQL con `:term is null` / `:maxMinutes is null`, susceptible de fallos de inferencia del tipo de parámetro en PostgreSQL. Ahora usan consultas diferenciadas para filtros presentes/ausentes.
4. El backend anterior ocultaba la excepción de los 500. `GlobalExceptionHandler` ahora la registra en la terminal (no en el JSON HTTP).
5. Los endpoints antiguos que responden 200 NO prueban que existan recetas: también devuelven 200 si las tablas están vacías.

## A. Verificar si los datos ya están cargados

Desde la carpeta del proyecto con Docker levantado:

```bash
docker compose up -d
docker exec -i manka-postgres psql -U postgres -d manka -v ON_ERROR_STOP=1 < scripts/diagnosticar_catalogo.sql
```

Deberían existir 7 306 ingredientes y 20 236 platos; si hay 0, la semilla no se ha importado.

## B. Si el catálogo está vacío (y SOLO si las tablas compatibles existen)

**No borres volúmenes ni importes sobre una base con datos de catálogo anteriores.**

La semilla incluye `BEGIN` y `COMMIT`, y está en `resources`, pero con `mode=never` puede importarse manualmente:

```bash
docker exec -i manka-postgres psql -U postgres -d manka -v ON_ERROR_STOP=1 < src/main/resources/data.sql
```

Si falla por columna/tabla o FK, revisa el error concreto; NO uses `continue-on-error` ni `down -v`. La semilla debe cargarse en un esquema compatible con el catálogo nuevo; `ddl-auto=update` no garantiza migrar una base anterior. Si ya tienes usuarios, historial u otros datos importantes, haz respaldo antes de cambios estructurales.

## C. Mantener la configuración después de importar

```properties
spring.sql.init.mode=never
```

La ubicación del archivo en `resources` no requiere `mode=always` después de haber hecho la importación.

## D. Compilar e iniciar

```bash
./mvnw -DskipTests package
./mvnw spring-boot:run
```

Detén la instancia antigua antes de iniciar para no usar clases anteriores.

## E. Postman

- `01 Login` debe dar 200. `00 Registro` puede dar 409 si el usuario ya existe.
- `02 GET /ingredients/page?page=0&size=20` debe dar 200 con contenido si el catálogo está cargado.
- `03 GET /ingredients/page?search=jitomate&page=0&size=10` debe dar 200; verificar alias.
- `04 GET /dishes/page?page=0&size=20&search=pollo` debe dar 200.
- `05 GET /dishes/1` solo da 200 si existe `dishes.id=1`.
- `06 POST /recommendations` requiere un `ingredientId` **existente**. Por ejemplo usar `2` (Tomate) cuando se haya importado esta semilla.

Si aún hay HTTP 500, revisar el nuevo stacktrace de Spring Boot (busca `Caused by:`). No se han ejecutado PostgreSQL ni Postman contra el equipo local del usuario.
