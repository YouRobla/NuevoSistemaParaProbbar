# Script PowerShell para limpiar archivos antes del despliegue

Write-Host "🧹 Limpiando archivos para despliegue..." -ForegroundColor Cyan

# Eliminar carpetas __pycache__
Get-ChildItem -Path . -Filter __pycache__ -Recurse -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Eliminar archivos .pyc y .pyo
Get-ChildItem -Path . -Filter *.pyc -Recurse -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path . -Filter *.pyo -Recurse -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "✅ Limpieza completada. El proyecto está listo para despliegue." -ForegroundColor Green

