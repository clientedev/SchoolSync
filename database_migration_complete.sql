-- Script completo de migração da base de dados
-- Execute este comando na sua base de dados PostgreSQL do Railway

-- ========================================
-- 1. ADICIONAR COLUNAS FALTANTES NA TABELA teacher
-- ========================================

-- Adicionar coluna user_id na tabela teacher
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'teacher' AND column_name = 'user_id') THEN
        ALTER TABLE teacher ADD COLUMN user_id INTEGER;
        ALTER TABLE teacher ADD CONSTRAINT fk_teacher_user_id 
            FOREIGN KEY (user_id) REFERENCES "user"(id);
    END IF;
END $$;

-- ========================================
-- 2. CRIAR TABELAS DE APOIO (se não existem)
-- ========================================

-- Criar tabela semester
CREATE TABLE IF NOT EXISTS semester (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    year INTEGER NOT NULL,
    number INTEGER NOT NULL,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Criar tabela curricular_unit
CREATE TABLE IF NOT EXISTS curricular_unit (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    code VARCHAR(20),
    course_id INTEGER NOT NULL REFERENCES course(id),
    workload INTEGER,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Criar tabela scheduled_evaluation
CREATE TABLE IF NOT EXISTS scheduled_evaluation (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES teacher(id),
    curricular_unit_id INTEGER NOT NULL REFERENCES curricular_unit(id),
    semester_id INTEGER NOT NULL REFERENCES semester(id),
    scheduled_month INTEGER NOT NULL,
    scheduled_year INTEGER NOT NULL,
    scheduled_date TIMESTAMP,
    is_completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER NOT NULL REFERENCES "user"(id)
);

-- Criar tabela digital_signature
CREATE TABLE IF NOT EXISTS digital_signature (
    id SERIAL PRIMARY KEY,
    evaluation_id INTEGER NOT NULL REFERENCES evaluation(id),
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    signature_data TEXT NOT NULL,
    signature_type VARCHAR(20) NOT NULL,
    signed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45)
);

-- ========================================
-- 3. ADICIONAR COLUNAS FALTANTES NA TABELA evaluation
-- ========================================

-- Adicionar semester_id
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'evaluation' AND column_name = 'semester_id') THEN
        ALTER TABLE evaluation ADD COLUMN semester_id INTEGER REFERENCES semester(id);
    END IF;
END $$;

-- Adicionar curricular_unit_id
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'evaluation' AND column_name = 'curricular_unit_id') THEN
        ALTER TABLE evaluation ADD COLUMN curricular_unit_id INTEGER REFERENCES curricular_unit(id);
    END IF;
END $$;

-- Adicionar scheduled_evaluation_id
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'evaluation' AND column_name = 'scheduled_evaluation_id') THEN
        ALTER TABLE evaluation ADD COLUMN scheduled_evaluation_id INTEGER REFERENCES scheduled_evaluation(id);
    END IF;
END $$;

-- Adicionar teacher_signed
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'evaluation' AND column_name = 'teacher_signed') THEN
        ALTER TABLE evaluation ADD COLUMN teacher_signed BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- Adicionar evaluator_signed
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'evaluation' AND column_name = 'evaluator_signed') THEN
        ALTER TABLE evaluation ADD COLUMN evaluator_signed BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- Adicionar updated_at
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'evaluation' AND column_name = 'updated_at') THEN
        ALTER TABLE evaluation ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;
END $$;

-- ========================================
-- 4. CRIAR SEMESTRE PADRÃO (se não existe)
-- ========================================

INSERT INTO semester (name, year, number, start_date, end_date, is_active)
SELECT '2025.1', 2025, 1, '2025-01-01'::timestamp, '2025-06-30'::timestamp, true
WHERE NOT EXISTS (SELECT 1 FROM semester WHERE name = '2025.1');

-- ========================================
-- 5. VERIFICAÇÕES FINAIS
-- ========================================

-- Verificar colunas da tabela teacher
SELECT 'teacher' as tabela, column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'teacher' 
ORDER BY ordinal_position;

-- Verificar colunas da tabela evaluation
SELECT 'evaluation' as tabela, column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'evaluation' 
ORDER BY ordinal_position;

-- Verificar se as novas tabelas foram criadas
SELECT table_name 
FROM information_schema.tables 
WHERE table_name IN ('semester', 'curricular_unit', 'scheduled_evaluation', 'digital_signature')
ORDER BY table_name;