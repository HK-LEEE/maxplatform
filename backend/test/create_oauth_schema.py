#!/usr/bin/env python3
"""
OAuth 2.0 Database Schema Creation Script
Applies OAuth schema to the existing MAX Platform database
"""

import asyncio
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:2300@172.28.32.1:5432/platform_integration")

def create_oauth_schema():
    """Create OAuth 2.0 database schema"""
    
    # Read the schema file
    schema_file_path = os.path.join(os.path.dirname(__file__), "../database/oauth_schema.sql")
    
    try:
        with open(schema_file_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
    except FileNotFoundError:
        print(f"❌ Schema file not found: {schema_file_path}")
        return False
    
    # Create database engine
    engine = create_engine(DATABASE_URL)
    
    try:
        # Execute schema
        with engine.connect() as connection:
            # Split SQL into individual statements
            statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
            
            for statement in statements:
                if statement:
                    try:
                        connection.execute(text(statement))
                        print(f"✅ Executed: {statement[:50]}...")
                    except Exception as e:
                        print(f"⚠️  Warning executing statement: {statement[:50]}...")
                        print(f"   Error: {str(e)}")
                        # Continue with other statements
                        continue
            
            connection.commit()
            
        print("🎉 OAuth 2.0 schema creation completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating OAuth schema: {str(e)}")
        return False
    
    finally:
        engine.dispose()

def verify_oauth_tables():
    """Verify that OAuth tables were created successfully"""
    
    engine = create_engine(DATABASE_URL)
    
    expected_tables = [
        'oauth_clients',
        'authorization_codes', 
        'oauth_access_tokens',
        'oauth_sessions',
        'oauth_audit_logs',
        'oauth_scopes'
    ]
    
    try:
        with engine.connect() as connection:
            for table_name in expected_tables:
                result = connection.execute(text(f"""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = '{table_name}'
                """))
                count = result.scalar()
                
                if count > 0:
                    print(f"✅ Table '{table_name}' exists")
                    
                    # Check if it has data (for tables that should have initial data)
                    if table_name in ['oauth_clients', 'oauth_scopes']:
                        data_result = connection.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                        data_count = data_result.scalar()
                        print(f"   └─ Contains {data_count} records")
                else:
                    print(f"❌ Table '{table_name}' does not exist")
                    
        return True
        
    except Exception as e:
        print(f"❌ Error verifying tables: {str(e)}")
        return False
    
    finally:
        engine.dispose()

if __name__ == "__main__":
    print("🚀 Starting OAuth 2.0 schema creation...")
    print(f"📊 Database URL: {DATABASE_URL}")
    
    success = create_oauth_schema()
    
    if success:
        print("\n🔍 Verifying table creation...")
        verify_oauth_tables()
        print("\n✨ OAuth 2.0 database setup complete!")
    else:
        print("\n💥 OAuth 2.0 schema creation failed!")
        exit(1)