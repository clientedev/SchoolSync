import os
import psycopg2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_railway():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL not found in environment variables.")
        return

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Check if the column exists
        cur.execute("""
            SELECT count(*) 
            FROM information_schema.columns 
            WHERE table_name='user' AND column_name='plain_password';
        """)
        exists = cur.fetchone()[0]
        
        if not exists:
            logger.info("Adding column 'plain_password' to 'user' table...")
            cur.execute('ALTER TABLE "user" ADD COLUMN plain_password VARCHAR(255);')
            conn.commit()
            logger.info("Migration successful: Column added.")
        else:
            logger.info("Column 'plain_password' already exists. Skipping.")
            
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate_railway()
