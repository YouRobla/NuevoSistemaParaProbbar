#!/bin/bash
# Script para limpiar y regenerar assets de Odoo

echo "🔧 Limpiando y regenerando assets de Odoo..."

# Limpiar archivos compilados de assets
find . -type f -name "*.css.map" -delete
find . -type f -name "*.js.map" -delete

# Limpiar archivos de caché de Odoo
find . -type d -name ".odoo" -exec rm -rf {} + 2>/dev/null || true

echo "✅ Limpieza completada."
echo "📝 Nota: Reinicia Odoo y actualiza los módulos para regenerar los assets."

