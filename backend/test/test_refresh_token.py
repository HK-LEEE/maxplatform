#!/usr/bin/env python3
"""
Test script to validate refresh token functionality
"""

import requests
import json
import sys
from datetime import datetime

def test_refresh_token():
    print(f"🔄 Testing refresh token functionality at {datetime.now()}")
    
    # Get the most recent refresh token from database
    try:
        from app.database import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        # Get the latest refresh token for maxlab client
        result = db.execute(text("""
            SELECT token_hash, user_id, scope, created_at 
            FROM oauth_refresh_tokens 
            WHERE client_id = 'maxlab' 
            AND revoked_at IS NULL 
            AND expires_at > NOW()
            ORDER BY created_at DESC 
            LIMIT 1
        """))
        
        token_row = result.first()
        if not token_row:
            print("❌ No valid refresh tokens found in database")
            return
            
        print(f"✅ Found refresh token: hash={token_row[0][:10]}..., user_id={token_row[1]}, created_at={token_row[3]}")
        
        # We can't use the actual token since we only have the hash
        # Instead, let's test with a dummy token to see the error flow
        dummy_refresh_token = "dummy_refresh_token_for_testing"
        
        # Get client credentials
        client_result = db.execute(text("""
            SELECT client_id, client_secret, is_confidential 
            FROM oauth_clients 
            WHERE client_id = 'maxlab'
        """))
        
        client_row = client_result.first()
        if not client_row:
            print("❌ Client 'maxlab' not found")
            return
            
        print(f"✅ Found client: {client_row[0]}, is_confidential={client_row[2]}")
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return
    
    # Test refresh token request
    print(f"\n🔄 Testing refresh token request with dummy token...")
    
    url = "http://localhost:8000/api/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": dummy_refresh_token,
        "client_id": client_row[0],
        "client_secret": client_row[1] if client_row[2] else None
    }
    
    # Remove None values
    data = {k: v for k, v in data.items() if v is not None}
    
    print(f"📤 Request data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(url, data=data, timeout=10)
        print(f"📥 Response status: {response.status_code}")
        print(f"📥 Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ Unexpected success - this should have failed with dummy token")
            print(f"Response: {response.json()}")
        else:
            print(f"⚠️  Expected failure: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Error text: {response.text}")
                
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    
    print(f"\n✅ Test completed at {datetime.now()}")

if __name__ == "__main__":
    test_refresh_token()