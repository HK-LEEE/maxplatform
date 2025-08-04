#!/usr/bin/env python3
"""
LLM Performance Migration Runner - Wave 2 Database Optimization
Applies performance indexes to resolve timeout issues with model permission queries
"""

import asyncio
import sys
import os
from pathlib import Path
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add the parent directory to Python path to import app modules
sys.path.append(str(Path(__file__).parent))

from app.config import settings
from app.database import get_db, SessionLocal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def read_migration_file(filepath: str) -> str:
    """Read the SQL migration file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Migration file not found: {filepath}")
        raise
    except Exception as e:
        logger.error(f"Error reading migration file: {e}")
        raise

def split_sql_statements(sql_content: str) -> list:
    """Split SQL content into individual statements"""
    # Remove comments and empty lines
    lines = []
    for line in sql_content.split('\n'):
        line = line.strip()
        if line and not line.startswith('--') and not line.startswith('/*'):
            lines.append(line)
    
    # Join and split by semicolon
    full_sql = ' '.join(lines)
    statements = [stmt.strip() for stmt in full_sql.split(';') if stmt.strip()]
    
    return statements

def run_migration():
    """Run the LLM performance migration"""
    logger.info("Starting LLM Performance Migration - Wave 2 Database Optimization")
    
    try:
        # Read migration file
        migration_file = Path(__file__).parent / 'migrations' / '005_add_llm_performance_indexes.sql'
        sql_content = read_migration_file(str(migration_file))
        
        # Split into individual statements
        statements = split_sql_statements(sql_content)
        logger.info(f"Found {len(statements)} SQL statements to execute")
        
        # Create database connection
        engine = create_engine(settings.database_url)
        
        with engine.connect() as connection:
            logger.info("Connected to database successfully")
            
            # Execute each statement
            for i, statement in enumerate(statements, 1):
                if not statement:
                    continue
                    
                try:
                    logger.info(f"Executing statement {i}/{len(statements)}: {statement[:50]}...")
                    connection.execute(text(statement))
                    connection.commit()
                    logger.info(f"✅ Statement {i} executed successfully")
                    
                except SQLAlchemyError as e:
                    # Log warning but continue with other statements
                    logger.warning(f"⚠️  Statement {i} failed (might already exist): {e}")
                    connection.rollback()
                    continue
                    
                except Exception as e:
                    logger.error(f"❌ Unexpected error in statement {i}: {e}")
                    connection.rollback()
                    raise
        
        logger.info("🎉 LLM Performance Migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

def verify_indexes():
    """Verify that indexes were created successfully"""
    logger.info("Verifying index creation...")
    
    verification_queries = [
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_model%'",  # SQLite
        # Add PostgreSQL verification if needed:
        # "SELECT indexname FROM pg_indexes WHERE tablename IN ('maxllm_models', 'maxllm_model_permissions')"
    ]
    
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as connection:
            for query in verification_queries:
                try:
                    result = connection.execute(text(query))
                    indexes = result.fetchall()
                    logger.info(f"Found {len(indexes)} performance indexes:")
                    for idx in indexes:
                        logger.info(f"  - {idx[0]}")
                    break  # Use first successful query
                except Exception:
                    continue  # Try next query format
                    
    except Exception as e:
        logger.warning(f"Index verification failed: {e}")

def test_performance():
    """Test performance of problematic queries"""
    logger.info("Testing query performance...")
    
    test_queries = [
        # Query that was timing out
        "SELECT COUNT(*) FROM maxllm_model_permissions WHERE model_id = '4a807dd5-d62a-45e2-a6b2-45b40c39903f'",
        
        # General performance test queries
        "SELECT COUNT(*) FROM maxllm_models WHERE is_active = true",
        "SELECT COUNT(*) FROM maxllm_model_permissions WHERE grantee_type = 'GROUP'",
        "SELECT COUNT(*) FROM maxllm_models WHERE owner_type = 'USER'"
    ]
    
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as connection:
            for i, query in enumerate(test_queries, 1):
                try:
                    import time
                    start_time = time.time()
                    result = connection.execute(text(query))
                    count = result.scalar()
                    end_time = time.time()
                    
                    duration_ms = (end_time - start_time) * 1000
                    logger.info(f"Test {i}: {count} records in {duration_ms:.2f}ms")
                    
                    if duration_ms > 1000:  # > 1 second
                        logger.warning(f"Query {i} is still slow ({duration_ms:.2f}ms)")
                    
                except Exception as e:
                    logger.warning(f"Test query {i} failed: {e}")
                    
    except Exception as e:
        logger.error(f"Performance testing failed: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("LLM Performance Migration - Wave 2 Database Optimization")
    print("=" * 60)
    
    success = run_migration()
    
    if success:
        verify_indexes()
        test_performance()
        print("\n✅ Migration completed successfully!")
        print("🚀 Database performance should be significantly improved")
        print("📊 Monitor the application for reduced timeout errors")
    else:
        print("\n❌ Migration failed!")
        print("🔍 Check the logs above for details")
        sys.exit(1)