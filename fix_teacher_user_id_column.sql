-- Script to add missing user_id column to teacher table
-- Execute this command on your Railway PostgreSQL database

-- Add the missing user_id column
ALTER TABLE teacher ADD COLUMN user_id INTEGER;

-- Add the foreign key constraint
ALTER TABLE teacher ADD CONSTRAINT fk_teacher_user_id 
    FOREIGN KEY (user_id) REFERENCES "user"(id);

-- Verification queries (optional)
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'teacher' AND column_name = 'user_id';

SELECT constraint_name, constraint_type 
FROM information_schema.table_constraints 
WHERE table_name = 'teacher' AND constraint_name LIKE '%user_id%';