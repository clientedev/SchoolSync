-- Script para resolver o erro de evaluator_id
-- Execute este comando no banco de dados Railway PostgreSQL

ALTER TABLE evaluation ALTER COLUMN evaluator_id DROP NOT NULL;

-- Verificação (opcional)
SELECT column_name, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'evaluation' AND column_name = 'evaluator_id';