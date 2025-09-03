-- SCRIPT COMPLETO DE MIGRAÇÃO PARA RAILWAY POSTGRESQL
-- Execute este script diretamente no console SQL do Railway

-- ========================================
-- 1. CRIAR TABELAS SE NÃO EXISTEM
-- ========================================

-- Tabela semester
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

-- Tabela curricular_unit
CREATE TABLE IF NOT EXISTS curricular_unit (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    code VARCHAR(20),
    course_id INTEGER NOT NULL,
    workload INTEGER,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES course(id)
);

-- Tabela scheduled_evaluation
CREATE TABLE IF NOT EXISTS scheduled_evaluation (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL,
    curricular_unit_id INTEGER NOT NULL,
    semester_id INTEGER NOT NULL,
    scheduled_month INTEGER NOT NULL,
    scheduled_year INTEGER NOT NULL,
    scheduled_date TIMESTAMP,
    is_completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER NOT NULL,
    FOREIGN KEY (teacher_id) REFERENCES teacher(id),
    FOREIGN KEY (curricular_unit_id) REFERENCES curricular_unit(id),
    FOREIGN KEY (semester_id) REFERENCES semester(id),
    FOREIGN KEY (created_by) REFERENCES "user"(id)
);

-- Tabela digital_signature
CREATE TABLE IF NOT EXISTS digital_signature (
    id SERIAL PRIMARY KEY,
    evaluation_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    signature_data TEXT NOT NULL,
    signature_type VARCHAR(20) NOT NULL,
    signed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    FOREIGN KEY (evaluation_id) REFERENCES evaluation(id),
    FOREIGN KEY (user_id) REFERENCES "user"(id)
);

-- ========================================
-- 2. ADICIONAR COLUNAS FALTANTES
-- ========================================

-- Adicionar user_id na tabela teacher
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'teacher' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE teacher ADD COLUMN user_id INTEGER;
        ALTER TABLE teacher ADD CONSTRAINT fk_teacher_user_id 
            FOREIGN KEY (user_id) REFERENCES "user"(id);
    END IF;
END $$;

-- Adicionar semester_id na tabela evaluation
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'evaluation' AND column_name = 'semester_id'
    ) THEN
        ALTER TABLE evaluation ADD COLUMN semester_id INTEGER;
        ALTER TABLE evaluation ADD CONSTRAINT fk_evaluation_semester_id 
            FOREIGN KEY (semester_id) REFERENCES semester(id);
    END IF;
END $$;

-- Adicionar curricular_unit_id na tabela evaluation
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'evaluation' AND column_name = 'curricular_unit_id'
    ) THEN
        ALTER TABLE evaluation ADD COLUMN curricular_unit_id INTEGER;
        ALTER TABLE evaluation ADD CONSTRAINT fk_evaluation_curricular_unit_id 
            FOREIGN KEY (curricular_unit_id) REFERENCES curricular_unit(id);
    END IF;
END $$;

-- Adicionar scheduled_evaluation_id na tabela evaluation
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'evaluation' AND column_name = 'scheduled_evaluation_id'
    ) THEN
        ALTER TABLE evaluation ADD COLUMN scheduled_evaluation_id INTEGER;
        ALTER TABLE evaluation ADD CONSTRAINT fk_evaluation_scheduled_evaluation_id 
            FOREIGN KEY (scheduled_evaluation_id) REFERENCES scheduled_evaluation(id);
    END IF;
END $$;

-- Adicionar teacher_signed na tabela evaluation
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'evaluation' AND column_name = 'teacher_signed'
    ) THEN
        ALTER TABLE evaluation ADD COLUMN teacher_signed BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- Adicionar evaluator_signed na tabela evaluation
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'evaluation' AND column_name = 'evaluator_signed'
    ) THEN
        ALTER TABLE evaluation ADD COLUMN evaluator_signed BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- Adicionar updated_at na tabela evaluation
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'evaluation' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE evaluation ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;
END $$;

-- ========================================
-- 3. INSERIR DADOS INICIAIS
-- ========================================

-- Criar semestre padrão 2025.1
INSERT INTO semester (name, year, number, start_date, end_date, is_active)
SELECT '2025.1', 2025, 1, '2025-01-01'::timestamp, '2025-06-30'::timestamp, true
WHERE NOT EXISTS (SELECT 1 FROM semester WHERE name = '2025.1');

-- Criar semestre 2025.2
INSERT INTO semester (name, year, number, start_date, end_date, is_active)
SELECT '2025.2', 2025, 2, '2025-07-01'::timestamp, '2025-12-31'::timestamp, false
WHERE NOT EXISTS (SELECT 1 FROM semester WHERE name = '2025.2');

-- Inserir cursos de exemplo se não existirem
INSERT INTO course (name, period, curriculum_component) 
SELECT 'Desenvolvimento de Sistemas', '2025.1', 'Técnico Profissionalizante'
WHERE NOT EXISTS (SELECT 1 FROM course WHERE name = 'Desenvolvimento de Sistemas');

INSERT INTO course (name, period, curriculum_component) 
SELECT 'Eletrônica', '2025.1', 'Técnico Profissionalizante'
WHERE NOT EXISTS (SELECT 1 FROM course WHERE name = 'Eletrônica');

INSERT INTO course (name, period, curriculum_component) 
SELECT 'Mecânica Industrial', '2025.1', 'Técnico Profissionalizante'
WHERE NOT EXISTS (SELECT 1 FROM course WHERE name = 'Mecânica Industrial');

-- Inserir unidades curriculares de exemplo
INSERT INTO curricular_unit (name, code, course_id, workload, description) 
SELECT 'Programação Orientada a Objetos', 'POO01', c.id, 80, 'Fundamentos de POO com Java e Python'
FROM course c WHERE c.name = 'Desenvolvimento de Sistemas'
AND NOT EXISTS (SELECT 1 FROM curricular_unit WHERE name = 'Programação Orientada a Objetos');

INSERT INTO curricular_unit (name, code, course_id, workload, description) 
SELECT 'Banco de Dados', 'BD01', c.id, 60, 'Modelagem e SQL com PostgreSQL'
FROM course c WHERE c.name = 'Desenvolvimento de Sistemas'
AND NOT EXISTS (SELECT 1 FROM curricular_unit WHERE name = 'Banco de Dados');

INSERT INTO curricular_unit (name, code, course_id, workload, description) 
SELECT 'Desenvolvimento Web', 'DW01', c.id, 80, 'HTML, CSS, JavaScript e Flask'
FROM course c WHERE c.name = 'Desenvolvimento de Sistemas'
AND NOT EXISTS (SELECT 1 FROM curricular_unit WHERE name = 'Desenvolvimento Web');

INSERT INTO curricular_unit (name, code, course_id, workload, description) 
SELECT 'Circuitos Eletrônicos', 'CE01', c.id, 80, 'Análise e projeto de circuitos'
FROM course c WHERE c.name = 'Eletrônica'
AND NOT EXISTS (SELECT 1 FROM curricular_unit WHERE name = 'Circuitos Eletrônicos');

INSERT INTO curricular_unit (name, code, course_id, workload, description) 
SELECT 'Microcontroladores', 'MC01', c.id, 60, 'Arduino e PIC'
FROM course c WHERE c.name = 'Eletrônica'
AND NOT EXISTS (SELECT 1 FROM curricular_unit WHERE name = 'Microcontroladores');

-- ========================================
-- 4. VERIFICAÇÕES FINAIS
-- ========================================

-- Verificar tabelas criadas
SELECT 'TABELAS CRIADAS:' as status;
SELECT table_name 
FROM information_schema.tables 
WHERE table_name IN ('semester', 'curricular_unit', 'scheduled_evaluation', 'digital_signature')
ORDER BY table_name;

-- Verificar colunas da tabela teacher
SELECT 'COLUNAS TEACHER:' as status;
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'teacher' AND column_name IN ('user_id')
ORDER BY column_name;

-- Verificar colunas da tabela evaluation
SELECT 'COLUNAS EVALUATION:' as status;
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'evaluation' 
AND column_name IN ('semester_id', 'curricular_unit_id', 'scheduled_evaluation_id', 'teacher_signed', 'evaluator_signed', 'updated_at')
ORDER BY column_name;

-- Verificar dados inseridos
SELECT 'DADOS INSERIDOS:' as status;
SELECT 'Semestres: ' || COUNT(*) as quantidade FROM semester
UNION ALL
SELECT 'Cursos: ' || COUNT(*) as quantidade FROM course
UNION ALL
SELECT 'Unidades Curriculares: ' || COUNT(*) as quantidade FROM curricular_unit;

-- Mensagem final
SELECT '✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO! ✅' as resultado;
SELECT 'Todas as tabelas e colunas foram criadas.' as info;
SELECT 'O sistema SENAI está pronto para uso completo!' as info;