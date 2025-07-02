#!/usr/bin/env python3
"""
Rollback script for Groups UUID Migration
Restores the database to integer-based group IDs from backup
"""

import json
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from app.database import get_database_url

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GroupsRollback:
    def __init__(self, backup_file):
        self.engine = create_engine(get_database_url())
        self.backup_file = backup_file
        self.backup_data = None
        
    def load_backup(self):
        """Load backup data from file"""
        logger.info(f"Loading backup from {self.backup_file}")
        
        try:
            with open(self.backup_file, 'r', encoding='utf-8') as f:
                self.backup_data = json.load(f)
            
            logger.info(f"Backup loaded successfully")
            logger.info(f"Backup timestamp: {self.backup_data.get('timestamp')}")
            logger.info(f"Groups in backup: {len(self.backup_data.get('groups', []))}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load backup: {e}")
            return False
    
    def restore_groups_table(self):
        """Restore groups table to integer-based IDs"""
        logger.info("Restoring groups table...")
        
        with self.engine.connect() as conn:
            trans = conn.begin()
            try:
                # Drop current groups table
                conn.execute(text("DROP TABLE IF EXISTS groups CASCADE"))
                
                # Recreate original groups table with integer IDs
                conn.execute(text("""
                    CREATE TABLE groups (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) UNIQUE NOT NULL,
                        description TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_by UUID
                    )
                """))
                
                # Restore original group data
                for group in self.backup_data["groups"]:
                    conn.execute(text("""
                        INSERT INTO groups (id, name, description, is_active, created_at, created_by)
                        VALUES (:id, :name, :description, :is_active, :created_at, :created_by)
                    """), group)
                
                # Reset sequence
                conn.execute(text("SELECT setval('groups_id_seq', (SELECT MAX(id) FROM groups))"))
                
                trans.commit()
                logger.info("Groups table restored successfully")
                
            except Exception as e:
                trans.rollback()
                raise e
    
    def restore_users_table(self):
        """Restore users table group_id to integer type"""
        logger.info("Restoring users table...")
        
        with self.engine.connect() as conn:
            trans = conn.begin()
            try:
                # Drop UUID group_id column if it exists
                conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS group_id"))
                
                # Add integer group_id column
                conn.execute(text("ALTER TABLE users ADD COLUMN group_id INTEGER"))
                
                # Restore user group assignments
                for user in self.backup_data["users"]:
                    if user.get("group_id"):
                        conn.execute(text("""
                            UPDATE users SET group_id = :group_id WHERE id = :user_id
                        """), {"group_id": user["group_id"], "user_id": user["id"]})
                
                # Add foreign key constraint
                conn.execute(text("""
                    ALTER TABLE users ADD CONSTRAINT fk_users_group_id 
                    FOREIGN KEY (group_id) REFERENCES groups(id)
                """))
                
                trans.commit()
                logger.info("Users table restored successfully")
                
            except Exception as e:
                trans.rollback()
                raise e
    
    def restore_association_tables(self):
        """Restore group_permissions and group_features tables"""
        logger.info("Restoring association tables...")
        
        with self.engine.connect() as conn:
            trans = conn.begin()
            try:
                for table_name in ["group_permissions", "group_features"]:
                    # Drop current table
                    conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
                    
                    # Recreate with integer group_id
                    id_column = "permission_id" if "permissions" in table_name else "feature_id"
                    conn.execute(text(f"""
                        CREATE TABLE {table_name} (
                            group_id INTEGER REFERENCES groups(id) ON DELETE CASCADE,
                            {id_column} INTEGER REFERENCES {"permissions" if "permissions" in table_name else "features"}(id) ON DELETE CASCADE,
                            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            PRIMARY KEY (group_id, {id_column})
                        )
                    """))
                    
                    # Restore data
                    for row in self.backup_data.get(table_name, []):
                        conn.execute(text(f"""
                            INSERT INTO {table_name} (group_id, {id_column}, granted_at)
                            VALUES (:group_id, :{id_column}, :granted_at)
                        """), row)
                
                trans.commit()
                logger.info("Association tables restored successfully")
                
            except Exception as e:
                trans.rollback()
                raise e
    
    def restore_flow_studio_tables(self):
        """Restore FlowStudio tables if they exist in backup"""
        if not self.backup_data.get("flow_studio_projects"):
            logger.info("No FlowStudio data to restore")
            return
        
        logger.info("Restoring FlowStudio tables...")
        
        with self.engine.connect() as conn:
            trans = conn.begin()
            try:
                # Restore flow_studio_projects
                conn.execute(text("ALTER TABLE flow_studio_projects DROP COLUMN IF EXISTS group_id"))
                conn.execute(text("ALTER TABLE flow_studio_projects ADD COLUMN group_id VARCHAR(36)"))
                
                for project in self.backup_data["flow_studio_projects"]:
                    if project.get("group_id"):
                        conn.execute(text("""
                            UPDATE flow_studio_projects SET group_id = :group_id WHERE id = :project_id
                        """), {"group_id": project["group_id"], "project_id": project["id"]})
                
                # Restore flow_studio_flows
                conn.execute(text("ALTER TABLE flow_studio_flows DROP COLUMN IF EXISTS group_id"))
                conn.execute(text("ALTER TABLE flow_studio_flows ADD COLUMN group_id VARCHAR(36)"))
                
                for flow in self.backup_data["flow_studio_flows"]:
                    if flow.get("group_id"):
                        conn.execute(text("""
                            UPDATE flow_studio_flows SET group_id = :group_id WHERE id = :flow_id
                        """), {"group_id": flow["group_id"], "flow_id": flow["id"]})
                
                trans.commit()
                logger.info("FlowStudio tables restored successfully")
                
            except Exception as e:
                trans.rollback()
                raise e
    
    def verify_rollback(self):
        """Verify rollback was successful"""
        logger.info("Verifying rollback...")
        
        with self.engine.connect() as conn:
            # Check groups table
            result = conn.execute(text("SELECT id, name FROM groups LIMIT 3"))
            logger.info("Groups table (should be integers):")
            for row in result:
                logger.info(f"  ID: {row.id} ({type(row.id).__name__}), Name: {row.name}")
            
            # Check users table
            result = conn.execute(text("""
                SELECT u.email, u.group_id, g.name as group_name 
                FROM users u 
                LEFT JOIN groups g ON u.group_id = g.id 
                WHERE u.group_id IS NOT NULL 
                LIMIT 3
            """))
            logger.info("User-group assignments:")
            for row in result:
                logger.info(f"  User: {row.email}, Group: {row.group_name}, ID: {row.group_id}")
        
        logger.info("Rollback verification completed")
    
    def run_rollback(self):
        """Execute the complete rollback process"""
        try:
            logger.info("Starting Groups UUID Migration Rollback")
            logger.info("=" * 50)
            
            # Step 1: Load backup
            if not self.load_backup():
                raise Exception("Failed to load backup file")
            
            # Step 2: Restore groups table
            self.restore_groups_table()
            
            # Step 3: Restore users table
            self.restore_users_table()
            
            # Step 4: Restore association tables
            self.restore_association_tables()
            
            # Step 5: Restore FlowStudio tables
            self.restore_flow_studio_tables()
            
            # Step 6: Verify rollback
            self.verify_rollback()
            
            logger.info("=" * 50)
            logger.info("Rollback completed successfully!")
            logger.info("Database has been restored to integer-based group IDs")
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            raise

def main():
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python rollback_uuid_migration.py <backup_file>")
        print("Example: python rollback_uuid_migration.py groups_migration_backup_20231201_120000.json")
        sys.exit(1)
    
    backup_file = sys.argv[1]
    
    print(f"WARNING: This will rollback the UUID migration and restore from {backup_file}")
    print("This will overwrite current data in the database!")
    confirm = input("Are you sure you want to proceed? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("Rollback cancelled")
        sys.exit(0)
    
    rollback = GroupsRollback(backup_file)
    rollback.run_rollback()

if __name__ == "__main__":
    main()