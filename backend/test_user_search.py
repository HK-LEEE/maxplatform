#!/usr/bin/env python3
"""Test script for user search endpoint"""

import requests
import json

# Test endpoint URL
BASE_URL = "http://localhost:8000"
SEARCH_URL = f"{BASE_URL}/api/users/search"

def test_search_with_q_parameter():
    """Test the new q parameter"""
    print("Testing /api/users/search with q parameter...")
    
    # Test cases
    test_cases = [
        {"params": {"q": "ad"}, "description": "Search with q='ad'"},
        {"params": {"q": "admin"}, "description": "Search with q='admin'"},
        {"params": {"email": "admin"}, "description": "Search with email='admin' (legacy)"},
        {"params": {"name": "admin"}, "description": "Search with name='admin' (legacy)"},
        {"params": {}, "description": "Search with no parameters (should return 400)"},
    ]
    
    # You'll need a valid token - replace with actual token
    headers = {
        "Authorization": "Bearer YOUR_ACCESS_TOKEN_HERE"
    }
    
    for test in test_cases:
        print(f"\n{test['description']}:")
        print(f"  Params: {test['params']}")
        
        try:
            response = requests.get(SEARCH_URL, params=test['params'], headers=headers)
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"  Results: {len(data)} users found")
                if data:
                    print(f"  First result: {data[0].get('email', 'N/A')}")
            else:
                print(f"  Error: {response.json().get('detail', 'Unknown error')}")
                
        except Exception as e:
            print(f"  Exception: {str(e)}")

if __name__ == "__main__":
    print("User Search Endpoint Test")
    print("=" * 50)
    test_search_with_q_parameter()