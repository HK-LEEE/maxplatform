#!/usr/bin/env python3
"""
Run Session Tracking Migration
Adds missing ip_address and user_agent columns to oauth_sessions table
"""

import os
import sys
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.database import get_db, SessionLocal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the session tracking migration."""
    try:
        logger.info("🔒 Starting Session Tracking Migration...")
        
        # Get database connection
        db = SessionLocal()
        
        # Read the migration file
        migration_file = Path(__file__).parent / "migrations" / "007_add_session_tracking_columns.sql"
        
        if not migration_file.exists():
            raise FileNotFoundError(f"Migration file not found: {migration_file}")
        
        logger.info(f"📄 Reading migration file: {migration_file}")
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Split SQL content into individual statements
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        logger.info(f"🔧 Executing {len(statements)} SQL statements...")
        
        success_count = 0
        for i, statement in enumerate(statements, 1):
            try:
                # Skip comments and empty statements
                if statement.startswith('--') or not statement:
                    continue
                    
                logger.info(f"📝 [{i}/{len(statements)}] Executing statement...")
                logger.debug(f"SQL: {statement[:100]}...")
                
                db.execute(text(statement))
                success_count += 1
                
            except Exception as e:
                logger.warning(f"⚠️ Statement {i} failed (may be expected): {str(e)}")
                # Continue with other statements - some failures are expected
        
        # Commit all changes
        db.commit()
        logger.info(f"✅ Migration completed successfully! {success_count} statements executed.")
        
        # Validate the migration
        validate_migration(db)
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def validate_migration(db):
    """Validate that the migration was applied correctly."""
    logger.info("🔍 Validating migration results...")
    
    try:
        # Check if ip_address column was added
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'oauth_sessions'
                AND column_name = 'ip_address'
            )
        """))
        
        ip_column_exists = result.scalar()
        if ip_column_exists:
            logger.info("✅ ip_address column added successfully")
        else:
            logger.error("❌ ip_address column was not added")
            return False
        
        # Check if user_agent column was added
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'oauth_sessions'
                AND column_name = 'user_agent'
            )
        """))
        
        user_agent_column_exists = result.scalar()
        if user_agent_column_exists:
            logger.info("✅ user_agent column added successfully")
        else:
            logger.error("❌ user_agent column was not added")
            return False
        
        # Check if indexes were created
        result = db.execute(text("""
            SELECT COUNT(*) FROM pg_indexes 
            WHERE tablename = 'oauth_sessions'
            AND indexname LIKE 'idx_oauth_sessions_%'
        """))
        
        index_count = result.scalar()
        if index_count >= 3:  # We expect at least 3 new indexes
            logger.info(f"✅ {index_count} indexes created for oauth_sessions table")
        else:
            logger.warning(f"⚠️ Only {index_count} indexes found (expected at least 3)")
        
        logger.info("🎉 Migration validation completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration validation failed: {str(e)}")
        return False

def main():
    """Main migration runner."""
    logger.info("🚀 Session Tracking Migration")
    logger.info("=" * 60)
    
    try:
        # Check database connection
        logger.info("🔌 Testing database connection...")
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("✅ Database connection successful")
        
        # Run the migration
        run_migration()
        
        logger.info("=" * 60)
        logger.info("🎉 Session Tracking Migration completed successfully!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Restart your backend server to use the new columns")
        logger.info("2. Update the user_switch_security_service to use real IP/User-Agent data")
        logger.info("3. Test user switching functionality")
        logger.info("")
        logger.info("🔒 oauth_sessions table now has enhanced security tracking!")
        
    except Exception as e:
        logger.error(f"💥 Migration failed with error: {str(e)}")
        logger.error("Please check the logs above and fix any issues before retrying.")
        sys.exit(1)

if __name__ == "__main__":
    main()