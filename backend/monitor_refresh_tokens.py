#!/usr/bin/env python3
"""
Real-time monitoring script for refresh token requests
Run this during client testing to capture detailed logs
"""

import time
import requests
import json
from datetime import datetime, timedelta

def monitor_refresh_token_activity():
    print(f"🔍 Starting refresh token monitoring at {datetime.now()}")
    print("👀 Watching for refresh token requests...")
    print("💡 When you see '❌ Refresh token renewal failed' on client, logs will appear here")
    print("=" * 60)
    
    last_check = datetime.now()
    
    try:
        from app.database import get_db
        from sqlalchemy import text
        
        while True:
            db = next(get_db())
            
            # Check for recent token activities
            result = db.execute(text("""
                SELECT 
                    rt.token_hash,
                    rt.user_id,
                    rt.client_id,
                    rt.created_at,
                    rt.last_used_at,
                    rt.rotation_count,
                    rt.revoked_at,
                    u.email
                FROM oauth_refresh_tokens rt
                LEFT JOIN users u ON rt.user_id = u.id
                WHERE rt.created_at > %s 
                OR rt.last_used_at > %s
                OR rt.revoked_at > %s
                ORDER BY GREATEST(
                    COALESCE(rt.created_at, '1970-01-01'::timestamp),
                    COALESCE(rt.last_used_at, '1970-01-01'::timestamp),
                    COALESCE(rt.revoked_at, '1970-01-01'::timestamp)
                ) DESC
                LIMIT 5
            """), (last_check, last_check, last_check))
            
            activities = result.fetchall()
            
            if activities:
                print(f"\n🔄 Recent token activity detected at {datetime.now()}:")
                for activity in activities:
                    token_hash, user_id, client_id, created_at, last_used_at, rotation_count, revoked_at, email = activity
                    
                    status = "🟢 ACTIVE"
                    if revoked_at:
                        status = "🔴 REVOKED"
                    elif last_used_at:
                        status = f"🟡 USED (rotation: {rotation_count})"
                    
                    print(f"  {status} | {token_hash[:10]}... | {client_id} | {email}")
                    print(f"    Created: {created_at}, Last Used: {last_used_at}, Revoked: {revoked_at}")
            
            # Check for recent OAuth logs
            log_result = db.execute(text("""
                SELECT 
                    action,
                    client_id,
                    user_id,
                    success,
                    error_code,
                    error_description,
                    created_at
                FROM oauth_audit_logs
                WHERE created_at > %s
                AND action = 'token'
                ORDER BY created_at DESC
                LIMIT 5
            """), (last_check,))
            
            oauth_logs = log_result.fetchall()
            
            if oauth_logs:
                print(f"\n📋 Recent OAuth token requests:")
                for log in oauth_logs:
                    action, client_id, user_id, success, error_code, error_description, created_at = log
                    status_icon = "✅" if success else "❌"
                    error_info = f" | {error_code}: {error_description}" if error_code else ""
                    print(f"  {status_icon} {created_at} | {client_id} | {user_id}{error_info}")
            
            last_check = datetime.now()
            time.sleep(2)  # Check every 2 seconds
            
    except KeyboardInterrupt:
        print(f"\n🛑 Monitoring stopped at {datetime.now()}")
    except Exception as e:
        print(f"❌ Error during monitoring: {e}")

if __name__ == "__main__":
    monitor_refresh_token_activity()