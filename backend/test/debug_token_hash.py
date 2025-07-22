#!/usr/bin/env python3
"""
Debug script to analyze token hash generation and database consistency
"""

import hashlib
import secrets
from datetime import datetime

def generate_token_hash(token: str) -> str:
    """Generate SHA256 hash of token for storage (same as production)"""
    return hashlib.sha256(token.encode()).hexdigest()

def test_hash_consistency():
    print("🔍 Testing token hash generation consistency...")
    
    # Test 1: Same input produces same hash
    test_token = "test_token_12345"
    hash1 = generate_token_hash(test_token)
    hash2 = generate_token_hash(test_token)
    
    print(f"Test token: {test_token}")
    print(f"Hash 1:     {hash1}")
    print(f"Hash 2:     {hash2}")
    print(f"Consistent: {'✅' if hash1 == hash2 else '❌'}")
    
    # Test 2: Different inputs produce different hashes
    token_a = "token_a"
    token_b = "token_b"
    hash_a = generate_token_hash(token_a)
    hash_b = generate_token_hash(token_b)
    
    print(f"\nDifferent tokens test:")
    print(f"Token A hash: {hash_a[:16]}...")
    print(f"Token B hash: {hash_b[:16]}...")
    print(f"Different:    {'✅' if hash_a != hash_b else '❌'}")
    
    # Test 3: Real token generation
    real_token = secrets.token_urlsafe(48)
    real_hash = generate_token_hash(real_token)
    
    print(f"\nReal token test:")
    print(f"Token:  {real_token[:20]}...")
    print(f"Hash:   {real_hash[:16]}...")
    print(f"Length: {len(real_hash)} chars")
    
    return hash1 == hash2 and hash_a != hash_b

def analyze_database_tokens():
    print(f"\n🔍 Analyzing database token patterns...")
    
    try:
        from app.database import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        # Get sample tokens from database
        result = db.execute(text("""
            SELECT 
                token_hash,
                created_at,
                last_used_at,
                revoked_at,
                rotation_count
            FROM oauth_refresh_tokens 
            WHERE client_id = 'maxlab'
            ORDER BY created_at DESC 
            LIMIT 10
        """))
        
        tokens = result.fetchall()
        
        print(f"📊 Found {len(tokens)} recent tokens:")
        
        for i, token in enumerate(tokens):
            token_hash, created_at, last_used_at, revoked_at, rotation_count = token
            status = "🟢 ACTIVE"
            if revoked_at:
                status = "🔴 REVOKED"
            elif last_used_at:
                status = f"🟡 USED ({rotation_count}x)"
            
            print(f"  {i+1}. {token_hash[:16]}... | {status} | {created_at}")
        
        # Check for hash duplicates
        hash_result = db.execute(text("""
            SELECT token_hash, COUNT(*) as count
            FROM oauth_refresh_tokens 
            WHERE client_id = 'maxlab'
            GROUP BY token_hash
            HAVING COUNT(*) > 1
        """))
        
        duplicates = hash_result.fetchall()
        
        if duplicates:
            print(f"\n⚠️  Found {len(duplicates)} duplicate hashes:")
            for hash_val, count in duplicates:
                print(f"  {hash_val[:16]}... appears {count} times")
        else:
            print(f"\n✅ No duplicate hashes found")
        
        # Check hash format consistency
        hash_lengths = set()
        for token in tokens:
            hash_lengths.add(len(token[0]))
        
        print(f"\n📏 Hash length consistency:")
        print(f"  Lengths found: {hash_lengths}")
        print(f"  Consistent: {'✅' if len(hash_lengths) <= 1 else '❌'}")
        
        return len(duplicates) == 0 and len(hash_lengths) <= 1
        
    except Exception as e:
        print(f"❌ Database analysis error: {e}")
        return False

def test_token_edge_cases():
    print(f"\n🔍 Testing edge cases...")
    
    # Test with whitespace
    token_with_space = " test_token "
    token_trimmed = "test_token"
    
    hash_space = generate_token_hash(token_with_space)
    hash_trimmed = generate_token_hash(token_trimmed)
    
    print(f"Whitespace handling:")
    print(f"  '{token_with_space}' → {hash_space[:16]}...")
    print(f"  '{token_trimmed}' → {hash_trimmed[:16]}...")
    print(f"  Different: {'✅' if hash_space != hash_trimmed else '❌'}")
    
    # Test with special characters
    special_token = "token+with/special=chars"
    special_hash = generate_token_hash(special_token)
    
    print(f"\nSpecial characters:")
    print(f"  Token: {special_token}")
    print(f"  Hash:  {special_hash[:16]}...")
    
    return hash_space != hash_trimmed

def main():
    print("=" * 60)
    print("🧪 TOKEN HASH CONSISTENCY ANALYSIS")
    print("=" * 60)
    
    # Run all tests
    consistency_ok = test_hash_consistency()
    database_ok = analyze_database_tokens()
    edge_cases_ok = test_token_edge_cases()
    
    print(f"\n" + "=" * 60)
    print(f"📊 ANALYSIS RESULTS")
    print(f"=" * 60)
    print(f"✅ Hash Generation: {'PASS' if consistency_ok else 'FAIL'}")
    print(f"✅ Database Integrity: {'PASS' if database_ok else 'FAIL'}")
    print(f"✅ Edge Cases: {'PASS' if edge_cases_ok else 'FAIL'}")
    
    if consistency_ok and database_ok and edge_cases_ok:
        print(f"\n🎉 ALL TESTS PASSED - Hash function is working correctly")
        print(f"💡 The 'token not found' issue is likely in token transmission/storage")
    else:
        print(f"\n⚠️  Issues found - Hash inconsistencies detected")
    
    print(f"\n✅ Analysis completed at {datetime.now()}")

if __name__ == "__main__":
    main()