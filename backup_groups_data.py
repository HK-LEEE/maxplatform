#!/usr/bin/env python3
"""
Groups Data Backup Script
Creates backup of existing groups data before UUID migration
"""

import json
import uuid
from datetime import datetime
from sqlalchemy import create_engine, text
from app.database import get_database_url

def backup_groups_data():
    """Backup existing groups data and generate UUID mappings"""
    
    # Create database connection
    engine = create_engine(get_database_url())
    
    backup_data = {
        "backup_timestamp": datetime.now().isoformat(),
        "groups": [],
        "user_group_assignments": [],
        "group_permissions": [],
        "group_features": [],
        "uuid_mappings": {}
    }
    
    with engine.connect() as conn:
        # Backup groups table
        result = conn.execute(text("SELECT * FROM groups ORDER BY id"))
        for row in result:
            group_data = dict(row._mapping)
            group_uuid = str(uuid.uuid4())
            
            backup_data["groups"].append(group_data)
            backup_data["uuid_mappings"][str(group_data["id"])] = group_uuid
            
        print(f"Backed up {len(backup_data['groups'])} groups")
        
        # Backup user group assignments
        result = conn.execute(text("SELECT id, real_name, email, group_id FROM users WHERE group_id IS NOT NULL"))
        for row in result:
            backup_data["user_group_assignments"].append(dict(row._mapping))
            
        print(f"Backed up {len(backup_data['user_group_assignments'])} user-group assignments")
        
        # Backup group permissions
        result = conn.execute(text("SELECT * FROM group_permissions"))
        for row in result:
            backup_data["group_permissions"].append(dict(row._mapping))
            
        print(f"Backed up {len(backup_data['group_permissions'])} group-permission relationships")
        
        # Backup group features  
        result = conn.execute(text("SELECT * FROM group_features"))
        for row in result:
            backup_data["group_features"].append(dict(row._mapping))
            
        print(f"Backed up {len(backup_data['group_features'])} group-feature relationships")
    
    # Save backup to file
    backup_filename = f"groups_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(backup_filename, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"Backup saved to {backup_filename}")
    print("UUID Mappings:")
    for old_id, new_uuid in backup_data["uuid_mappings"].items():
        print(f"  Group ID {old_id} → {new_uuid}")
    
    return backup_data

if __name__ == "__main__":
    backup_groups_data()