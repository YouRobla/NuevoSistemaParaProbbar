#!/bin/bash
# Script para limpiar archivos antes del despliegue

echo "🧹 Limpiando archivos para despliegue..."

# Eliminar carpetas __pycache__
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Eliminar archivos .pyc y .pyo
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete

# Eliminar archivos .pyc en __pycache__ (por si acaso)
find . -path "*/__pycache__/*.pyc" -delete

echo "✅ Limpieza completada. El proyecto está listo para despliegue."

