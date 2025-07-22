#!/usr/bin/env python3
"""
OAuth 2.0 Database Schema Creation Script V2
Handles PostgreSQL dollar-quoted functions properly
"""

import os
import re
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:2300@172.28.32.1:5432/platform_integration")

def split_sql_statements(sql_content):
    """
    Split SQL content into individual statements, handling dollar-quoted strings
    """
    # Remove single-line comments
    lines = sql_content.split('\n')
    cleaned_lines = []
    for line in lines:
        # Skip full line comments
        if line.strip().startswith('--'):
            continue
        cleaned_lines.append(line)
    
    sql_content = '\n'.join(cleaned_lines)
    
    # Regular expression to match SQL statements, considering:
    # 1. Dollar-quoted strings (PostgreSQL functions)
    # 2. String literals
    # 3. Statement terminators (;)
    
    # Split by semicolon but not within dollar quotes or string literals
    statements = []
    current_pos = 0
    content_len = len(sql_content)
    
    while current_pos < content_len:
        # Find next semicolon that's not in quotes
        in_single_quote = False
        in_dollar_quote = False
        dollar_tag = None
        statement_start = current_pos
        
        while current_pos < content_len:
            char = sql_content[current_pos]
            
            # Handle single quotes
            if char == "'" and not in_dollar_quote:
                if current_pos + 1 < content_len and sql_content[current_pos + 1] == "'":
                    current_pos += 2  # Skip escaped quote
                    continue
                in_single_quote = not in_single_quote
            
            # Handle dollar quotes
            elif char == '$' and not in_single_quote:
                # Look for dollar quote pattern
                match = re.match(r'\$([A-Za-z_]*)\$', sql_content[current_pos:])
                if match:
                    if not in_dollar_quote:
                        in_dollar_quote = True
                        dollar_tag = match.group(0)
                        current_pos += len(dollar_tag)
                        continue
                    elif dollar_tag == match.group(0):
                        in_dollar_quote = False
                        dollar_tag = None
                        current_pos += len(match.group(0))
                        continue
            
            # Check for statement terminator
            elif char == ';' and not in_single_quote and not in_dollar_quote:
                # Found statement end
                statement = sql_content[statement_start:current_pos + 1].strip()
                if statement:
                    statements.append(statement)
                current_pos += 1
                break
            
            current_pos += 1
        
        # If we reached the end without finding a semicolon
        if current_pos >= content_len and statement_start < content_len:
            statement = sql_content[statement_start:].strip()
            if statement and statement != ';':
                statements.append(statement)
            break
    
    return statements

def create_oauth_schema():
    """Create OAuth 2.0 database schema with proper statement parsing"""
    
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
        # Split SQL into individual statements properly
        statements = split_sql_statements(schema_sql)
        
        print(f"📊 Found {len(statements)} SQL statements to execute")
        
        success_count = 0
        with engine.connect() as connection:
            for i, statement in enumerate(statements, 1):
                try:
                    # Show first 80 chars of statement for logging
                    preview = statement.replace('\n', ' ')[:80]
                    print(f"\n[{i}/{len(statements)}] Executing: {preview}...")
                    
                    # Use a transaction for each statement
                    trans = connection.begin()
                    try:
                        connection.execute(text(statement))
                        trans.commit()
                        success_count += 1
                        print(f"✅ Success")
                    except Exception as e:
                        trans.rollback()
                        raise e
                    
                except Exception as e:
                    print(f"❌ Error: {str(e)}")
                    # Continue with other statements
                    continue
            
        print(f"\n📊 Execution Summary: {success_count}/{len(statements)} statements succeeded")
        return success_count > 0
        
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
            print("\n🔍 Verifying OAuth tables:")
            existing_tables = 0
            
            for table_name in expected_tables:
                result = connection.execute(text(f"""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = :table_name
                """), {"table_name": table_name})
                count = result.scalar()
                
                if count > 0:
                    print(f"✅ Table '{table_name}' exists")
                    existing_tables += 1
                    
                    # Check if it has data (for tables that should have initial data)
                    if table_name in ['oauth_clients', 'oauth_scopes']:
                        try:
                            data_result = connection.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                            data_count = data_result.scalar()
                            print(f"   └─ Contains {data_count} records")
                        except Exception as e:
                            print(f"   └─ Could not count records: {str(e)}")
                else:
                    print(f"❌ Table '{table_name}' does not exist")
            
            print(f"\n📊 Summary: {existing_tables}/{len(expected_tables)} tables exist")
            return existing_tables == len(expected_tables)
        
    except Exception as e:
        print(f"❌ Error verifying tables: {str(e)}")
        return False
    
    finally:
        engine.dispose()

def verify_oauth_clients():
    """Verify that OAuth clients were registered"""
    
    engine = create_engine(DATABASE_URL)
    
    expected_clients = [
        'maxflowstudio',
        'maxteamsync',
        'maxlab',
        'maxworkspace',
        'maxapa',
        'maxmlops'
    ]
    
    try:
        with engine.connect() as connection:
            print("\n🔍 Verifying OAuth clients:")
            
            # Check if oauth_clients table exists first
            table_check = connection.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'oauth_clients'
            """))
            
            if table_check.scalar() == 0:
                print("❌ oauth_clients table does not exist")
                return False
            
            # Get all registered clients
            result = connection.execute(text("SELECT client_id, client_name FROM oauth_clients"))
            registered_clients = {row[0]: row[1] for row in result}
            
            for client_id in expected_clients:
                if client_id in registered_clients:
                    print(f"✅ Client '{client_id}' registered as '{registered_clients[client_id]}'")
                else:
                    print(f"❌ Client '{client_id}' not found")
            
            print(f"\n📊 Total clients registered: {len(registered_clients)}")
            return len(registered_clients) >= len(expected_clients)
        
    except Exception as e:
        print(f"❌ Error verifying clients: {str(e)}")
        return False
    
    finally:
        engine.dispose()

if __name__ == "__main__":
    print("🚀 Starting OAuth 2.0 schema creation (V2)...")
    print(f"📊 Database URL: {DATABASE_URL}")
    
    success = create_oauth_schema()
    
    if success:
        print("\n✨ Schema creation completed!")
        verify_oauth_tables()
        verify_oauth_clients()
    else:
        print("\n💥 OAuth 2.0 schema creation failed!")
        exit(1)