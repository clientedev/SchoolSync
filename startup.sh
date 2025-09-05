#!/bin/bash
# Startup script para Railway

echo "🚀 Iniciando aplicação SENAI..."

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERRO: DATABASE_URL não está configurada"
    echo "Configure a variável DATABASE_URL no Railway"
    exit 1
fi

echo "✅ DATABASE_URL configurada"

# Start the application
echo "🏗️ Iniciando aplicação Flask..."
exec python production_app.py