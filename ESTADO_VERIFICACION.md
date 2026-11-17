# Estado real de verificación

**Realizado (sin servidor PostgreSQL ni Maven)**

- `python scripts/convertir_manka.py ...` con las 20 236 filas de `main.csv`.
- SQL completo validado con `python scripts/validar_semilla.py database/seed/manka_seed.sql` en SQLite en memoria, usando FK, PK y restricciones UNIQUE equivalentes.
- Conteos: 20 236 recetas; 25 658 ingredientes detectados; 173 368 relaciones; 64 alias; 771 etiquetas; 84 762 asociaciones con etiquetas; 7 952 vínculos a fuentes de proteína.
- Comprobación de sintaxis Java por el parser del JDK (106 archivos .java): sin errores de sintaxis.
- Postman: archivo de colección JSON válido (8 peticiones); **peticiones no ejecutadas**.

**Pendiente antes del deployment**

- `./mvnw -DskipTests package`: Maven Wrapper no pudo descargar Maven 3.9.9 desde Maven Central en este entorno.
- `./mvnw test`: pruebas de integración y Testcontainers no ejecutadas.
- Importación real en PostgreSQL 16/17/18 y arranque Spring Boot no probados.
- Los cambios en repositorios y servicios Java fueron revisados a nivel de código, **no compilados con las dependencias reales**.
- Revisión manual de 14 recetas sin ingredientes, 2 767 fragmentos excluidos y 13 195 clasificaciones como `Otros`.
- Pruebas de rendimiento y revisión de seguridad del despliegue (incluido reemplazo de claves RSA de desarrollo).

El archivo `database/seed/data_legacy_212.sql` solo se conserva para pruebas/consulta; la semilla nueva usa exclusivamente el CSV y IDs nuevos. **No importar en una base productiva que ya contiene registros.**
