-- Ejecutar sobre la base de datos a la que apunta DB_URL (manka).
SELECT 'ingredients' AS tabla, count(*) AS registros FROM ingredients
UNION ALL SELECT 'dishes', count(*) FROM dishes
UNION ALL SELECT 'dish_ingredients', count(*) FROM dish_ingredients
UNION ALL SELECT 'ingredient_aliases', count(*) FROM ingredient_aliases
ORDER BY tabla;
SELECT id, name FROM ingredients ORDER BY id LIMIT 5;
SELECT id, name FROM dishes ORDER BY id LIMIT 5;
