# Script PowerShell para limpiar y regenerar assets de Odoo

Write-Host "🔧 Limpiando y regenerando assets de Odoo..." -ForegroundColor Cyan

# Limpiar archivos compilados de assets
Get-ChildItem -Path . -Filter *.css.map -Recurse -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path . -Filter *.js.map -Recurse -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

# Limpiar archivos de caché de Odoo
Get-ChildItem -Path . -Filter .odoo -Recurse -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "✅ Limpieza completada." -ForegroundColor Green
Write-Host "📝 Nota: Reinicia Odoo y actualiza los módulos para regenerar los assets." -ForegroundColor Yellow

