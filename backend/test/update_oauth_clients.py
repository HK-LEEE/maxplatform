#!/usr/bin/env python3
"""
Update OAuth 2.0 Clients with new port configuration
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:2300@172.28.32.1:5432/platform_integration")

def update_oauth_clients():
    """Update OAuth clients with new port configuration"""
    
    # Read the update file
    update_file_path = os.path.join(os.path.dirname(__file__), "../database/update_oauth_clients.sql")
    
    try:
        with open(update_file_path, 'r', encoding='utf-8') as f:
            update_sql = f.read()
    except FileNotFoundError:
        print(f"❌ Update file not found: {update_file_path}")
        return False
    
    # Create database engine
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # Execute update SQL
            connection.execute(text(update_sql))
            connection.commit()
            
        print("🎉 OAuth clients updated successfully!")
        
        # Verify updates
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT client_id, client_name, homepage_url 
                FROM oauth_clients 
                ORDER BY client_id
            """))
            
            print("\n📊 Current OAuth Clients:")
            print("-" * 70)
            print(f"{'Client ID':<20} {'Client Name':<25} {'Homepage URL':<25}")
            print("-" * 70)
            
            for row in result:
                print(f"{row[0]:<20} {row[1]:<25} {row[2]:<25}")
                
        return True
        
    except Exception as e:
        print(f"❌ Error updating OAuth clients: {str(e)}")
        return False
    
    finally:
        engine.dispose()

if __name__ == "__main__":
    print("🚀 Starting OAuth client update...")
    print(f"📊 Database URL: {DATABASE_URL}")
    
    success = update_oauth_clients()
    
    if success:
        print("\n✨ OAuth client update complete!")
    else:
        print("\n💥 OAuth client update failed!")
        exit(1)