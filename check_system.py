#!/usr/bin/env python3
"""
Script para verificar o funcionamento completo do sistema SENAI
Usado para diagnosticar problemas no Railway
"""

import os
import sys
import logging
from datetime import datetime

def check_environment():
    """Verificar variáveis de ambiente necessárias"""
    print("🔍 Verificando variáveis de ambiente...")
    
    required_vars = ['DATABASE_URL']
    optional_vars = ['PORT', 'SESSION_SECRET']
    
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {'*' * min(len(value), 10)}...")
        else:
            print(f"❌ {var}: NÃO DEFINIDA")
            return False
    
    for var in optional_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {'*' * min(len(value), 10)}...")
        else:
            print(f"⚠️  {var}: usando valor padrão")
    
    return True

def check_database():
    """Verificar conexão com o banco de dados"""
    print("\n📊 Verificando conexão com banco de dados...")
    
    try:
        # Import do app de produção
        from production_app import app, db
        
        with app.app_context():
            # Testar conexão
            connection = db.engine.connect()
            connection.close()
            print("✅ Conexão com PostgreSQL: OK")
            
            # Verificar tabelas
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"✅ Tabelas encontradas: {len(tables)}")
            
            # Verificar tabelas principais
            expected_tables = ['user', 'teacher', 'course', 'evaluation', 'evaluator']
            for table in expected_tables:
                if table in tables:
                    print(f"  ✅ {table}")
                else:
                    print(f"  ❌ {table} - FALTANDO")
            
            return True
            
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False

def check_app_startup():
    """Verificar se a aplicação inicia corretamente"""
    print("\n🚀 Verificando inicialização da aplicação...")
    
    try:
        from production_app import app
        
        with app.app_context():
            print("✅ Aplicação Flask: OK")
            print(f"✅ Modo debug: {app.debug}")
            print(f"✅ Configurações carregadas: {len(app.config)} itens")
            
            # Testar rota de health
            with app.test_client() as client:
                response = client.get('/health')
                if response.status_code == 200:
                    print("✅ Health check: OK")
                else:
                    print(f"❌ Health check: {response.status_code}")
            
            return True
            
    except Exception as e:
        print(f"❌ Erro na aplicação: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def main():
    """Função principal"""
    print("=" * 50)
    print("🔧 DIAGNÓSTICO DO SISTEMA SENAI")
    print("=" * 50)
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python: {sys.version}")
    print(f"Diretório: {os.getcwd()}")
    
    # Verificações
    checks = [
        check_environment,
        check_database,
        check_app_startup
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"❌ Erro inesperado: {e}")
            results.append(False)
    
    # Resumo
    print("\n" + "=" * 50)
    print("📋 RESUMO DOS TESTES")
    print("=" * 50)
    
    test_names = [
        "Variáveis de ambiente",
        "Conexão com banco",
        "Inicialização da app"
    ]
    
    all_passed = True
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{i+1}. {name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("Sistema está pronto para produção no Railway")
        return 0
    else:
        print("⚠️  ALGUNS TESTES FALHARAM")
        print("Verifique os erros acima antes do deploy")
        return 1

if __name__ == '__main__':
    sys.exit(main())