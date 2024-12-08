from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from schema import Base
import os
from dotenv import load_dotenv

load_dotenv()

def migrate_database():
    """Migrate the database to the new schema"""
    # Get database URL from environment variable
    database_url = os.getenv('DATABASE_URL', 'sqlite:///contracts.db')
    
    # Create engine
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Add the details column to recommendations table
            conn.execute(text("""
                ALTER TABLE recommendations 
                ADD COLUMN IF NOT EXISTS details JSONB DEFAULT '{}'::jsonb;
            """))
            
            # Commit the transaction
            conn.commit()
            
            print("Migration completed successfully!")
            return True
        
    except Exception as e:
        print(f"Error during migration: {e}")
        return False

if __name__ == "__main__":
    migrate_database() 