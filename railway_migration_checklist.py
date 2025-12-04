#!/usr/bin/env python3
"""
Railway Database Migration Script for EvaluationChecklistItem
This script is idempotent and can be run multiple times safely.
It creates the evaluation_checklist_item table if it doesn't exist.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """Run the database migration for EvaluationChecklistItem table."""
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable is not set")
        sys.exit(1)
    
    logger.info("Starting Railway database migration for EvaluationChecklistItem...")
    
    try:
        from sqlalchemy import create_engine, text, inspect
        from sqlalchemy.orm import sessionmaker
        
        # Create engine
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check if table already exists
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        if 'evaluation_checklist_item' in existing_tables:
            logger.info("Table 'evaluation_checklist_item' already exists. Checking for missing columns...")
            
            # Get existing columns
            existing_columns = {col['name'] for col in inspector.get_columns('evaluation_checklist_item')}
            required_columns = {'id', 'evaluation_id', 'label', 'value', 'category', 'is_default', 'display_order', 'created_at', 'updated_at'}
            
            missing_columns = required_columns - existing_columns
            
            if missing_columns:
                logger.info(f"Missing columns found: {missing_columns}")
                
                # Add missing columns
                for col in missing_columns:
                    if col == 'display_order':
                        session.execute(text("ALTER TABLE evaluation_checklist_item ADD COLUMN display_order INTEGER DEFAULT 0"))
                        logger.info("Added 'display_order' column")
                    elif col == 'updated_at':
                        session.execute(text("ALTER TABLE evaluation_checklist_item ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
                        logger.info("Added 'updated_at' column")
                
                session.commit()
                logger.info("Missing columns added successfully")
            else:
                logger.info("All required columns exist. No changes needed.")
        else:
            logger.info("Creating 'evaluation_checklist_item' table...")
            
            # Create the table
            create_table_sql = """
            CREATE TABLE evaluation_checklist_item (
                id SERIAL PRIMARY KEY,
                evaluation_id INTEGER NOT NULL REFERENCES evaluation(id) ON DELETE CASCADE,
                label VARCHAR(500) NOT NULL,
                value VARCHAR(50),
                category VARCHAR(50) DEFAULT 'planning',
                is_default BOOLEAN DEFAULT TRUE,
                display_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            session.execute(text(create_table_sql))
            
            # Create index for faster queries
            session.execute(text("CREATE INDEX IF NOT EXISTS idx_checklist_evaluation_id ON evaluation_checklist_item(evaluation_id)"))
            session.execute(text("CREATE INDEX IF NOT EXISTS idx_checklist_category ON evaluation_checklist_item(category)"))
            
            session.commit()
            logger.info("Table 'evaluation_checklist_item' created successfully with indexes")
        
        # Verify the table structure
        logger.info("\nFinal table structure:")
        columns = inspector.get_columns('evaluation_checklist_item')
        for col in columns:
            logger.info(f"  - {col['name']}: {col['type']}")
        
        session.close()
        logger.info("\nMigration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
