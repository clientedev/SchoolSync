#!/bin/bash
# Script de deploy que executa migrações automaticamente
# Para usar no Railway ou outro serviço de deploy

echo "🚀 Iniciando processo de deploy..."

echo "📋 Verificando variáveis de ambiente..."
if [ -z "$DATABASE_URL" ]; then
    echo "❌ ERROR: DATABASE_URL não está definida"
    exit 1
fi

echo "🔄 Executando migrações da base de dados..."

# Executar o script de migração SQL
if [ -f "database_migration_complete.sql" ]; then
    echo "📊 Executando migração completa da base de dados..."
    psql $DATABASE_URL -f database_migration_complete.sql
    
    if [ $? -eq 0 ]; then
        echo "✅ Migração da base de dados concluída com sucesso"
    else
        echo "❌ Erro na migração da base de dados"
        exit 1
    fi
else
    echo "⚠️  Arquivo de migração não encontrado, continuando..."
fi

echo "🏗️  Iniciando aplicação..."
exec "$@"