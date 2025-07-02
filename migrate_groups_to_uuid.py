#!/usr/bin/env python3
"""
Groups Migration Script: Integer ID → UUID
Migrates existing groups and all related data to use UUID-based group IDs
"""

import json
import uuid
import logging
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
from app.database import get_database_url

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GroupsMigration:
    def __init__(self):
        self.engine = create_engine(get_database_url())
        self.uuid_mappings = {}
        self.backup_file = f"groups_migration_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
    def backup_existing_data(self):
        """Backup all existing group-related data"""
        logger.info("Creating backup of existing data...")
        
        backup_data = {
            "timestamp": datetime.now().isoformat(),
            "groups": [],
            "users": [],
            "group_permissions": [],
            "group_features": [],
            "flow_studio_projects": [],
            "flow_studio_flows": [],
            "llm_publish_access": []
        }
        
        with self.engine.connect() as conn:
            # Backup groups
            result = conn.execute(text("SELECT * FROM groups ORDER BY id"))
            for row in result:
                group_data = dict(row._mapping)
                backup_data["groups"].append(group_data)
                
                # Generate UUID mapping
                new_uuid = str(uuid.uuid4())
                self.uuid_mappings[str(group_data["id"])] = new_uuid
                logger.info(f"Group ID {group_data['id']} → {new_uuid}")
            
            # Backup users with group assignments
            result = conn.execute(text("SELECT * FROM users WHERE group_id IS NOT NULL"))
            for row in result:
                backup_data["users"].append(dict(row._mapping))
            
            # Backup group relationships
            for table in ["group_permissions", "group_features"]:
                result = conn.execute(text(f"SELECT * FROM {table}"))
                backup_data[table] = [dict(row._mapping) for row in result]
            
            # Backup FlowStudio data if tables exist
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            
            if "flow_studio_projects" in tables:
                result = conn.execute(text("SELECT * FROM flow_studio_projects WHERE group_id IS NOT NULL"))
                backup_data["flow_studio_projects"] = [dict(row._mapping) for row in result]
                
            if "flow_studio_flows" in tables:
                result = conn.execute(text("SELECT * FROM flow_studio_flows WHERE group_id IS NOT NULL"))
                backup_data["flow_studio_flows"] = [dict(row._mapping) for row in result]
                
            if "maxllm_flow_publish_access" in tables:
                result = conn.execute(text("SELECT * FROM maxllm_flow_publish_access WHERE target_group_id IS NOT NULL"))
                backup_data["llm_publish_access"] = [dict(row._mapping) for row in result]
        
        # Save backup
        with open(self.backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Backup completed: {self.backup_file}")
        logger.info(f"Groups to migrate: {len(backup_data['groups'])}")
        logger.info(f"Users affected: {len(backup_data['users'])}")
        return backup_data
    
    def migrate_groups_table(self):
        """Migrate groups table to use UUID primary keys"""
        logger.info("Migrating groups table...")
        
        with self.engine.connect() as conn:
            trans = conn.begin()
            try:
                # Create new temporary groups table with UUID
                conn.execute(text("""
                    CREATE TABLE groups_new (
                        id UUID PRIMARY KEY,
                        name VARCHAR(100) UNIQUE NOT NULL,
                        description TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_by UUID
                    )
                """))
                
                # Migrate data to new table
                for old_id, new_uuid in self.uuid_mappings.items():
                    conn.execute(text("""
                        INSERT INTO groups_new (id, name, description, is_active, created_at, created_by)
                        SELECT :new_id, name, description, is_active, created_at, created_by
                        FROM groups WHERE id = :old_id
                    """), {"new_id": new_uuid, "old_id": int(old_id)})
                
                trans.commit()
                logger.info("Groups table migration completed")
                
            except Exception as e:
                trans.rollback()
                raise e
    
    def migrate_users_table(self):
        """Update users table group_id references"""
        logger.info("Updating users table group_id references...")
        
        with self.engine.connect() as conn:
            trans = conn.begin()
            try:
                # Add new UUID group_id column
                conn.execute(text("ALTER TABLE users ADD COLUMN group_id_new UUID"))
                
                # Update with UUID values
                for old_id, new_uuid in self.uuid_mappings.items():
                    conn.execute(text("""
                        UPDATE users SET group_id_new = :new_uuid 
                        WHERE group_id = :old_id
                    """), {"new_uuid": new_uuid, "old_id": int(old_id)})
                
                trans.commit()
                logger.info("Users table updated")
                
            except Exception as e:
                trans.rollback()
                raise e
    
    def migrate_association_tables(self):
        """Update group_permissions and group_features tables"""
        logger.info("Migrating association tables...")
        
        with self.engine.connect() as conn:
            trans = conn.begin()
            try:
                for table in ["group_permissions", "group_features"]:
                    # Create new table
                    conn.execute(text(f"""
                        CREATE TABLE {table}_new (
                            group_id UUID NOT NULL,
                            {"permission_id" if "permissions" in table else "feature_id"} INTEGER NOT NULL,
                            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            PRIMARY KEY (group_id, {"permission_id" if "permissions" in table else "feature_id"})
                        )
                    """))
                    
                    # Migrate data
                    for old_id, new_uuid in self.uuid_mappings.items():
                        id_column = "permission_id" if "permissions" in table else "feature_id"
                        conn.execute(text(f"""
                            INSERT INTO {table}_new (group_id, {id_column}, granted_at)
                            SELECT :new_uuid, {id_column}, granted_at
                            FROM {table} WHERE group_id = :old_id
                        """), {"new_uuid": new_uuid, "old_id": int(old_id)})
                
                trans.commit()
                logger.info("Association tables migrated")
                
            except Exception as e:
                trans.rollback()
                raise e
    
    def migrate_flow_studio_tables(self):
        """Update FlowStudio tables if they exist"""
        logger.info("Checking for FlowStudio tables...")
        
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()
        
        if "flow_studio_projects" not in tables:
            logger.info("FlowStudio tables not found, skipping...")
            return
        
        with self.engine.connect() as conn:
            trans = conn.begin()
            try:
                # Update flow_studio_projects
                conn.execute(text("ALTER TABLE flow_studio_projects ADD COLUMN group_id_new UUID"))
                for old_id, new_uuid in self.uuid_mappings.items():
                    conn.execute(text("""
                        UPDATE flow_studio_projects SET group_id_new = :new_uuid 
                        WHERE group_id = :old_id
                    """), {"new_uuid": new_uuid, "old_id": old_id})
                
                # Update flow_studio_flows
                conn.execute(text("ALTER TABLE flow_studio_flows ADD COLUMN group_id_new UUID"))
                for old_id, new_uuid in self.uuid_mappings.items():
                    conn.execute(text("""
                        UPDATE flow_studio_flows SET group_id_new = :new_uuid 
                        WHERE group_id = :old_id
                    """), {"new_uuid": new_uuid, "old_id": old_id})
                
                trans.commit()
                logger.info("FlowStudio tables updated")
                
            except Exception as e:
                trans.rollback()
                raise e
    
    def finalize_migration(self):
        """Replace old tables with new ones"""
        logger.info("Finalizing migration...")
        
        with self.engine.connect() as conn:
            trans = conn.begin()
            try:
                # Drop old tables and rename new ones
                conn.execute(text("DROP TABLE IF EXISTS groups CASCADE"))
                conn.execute(text("ALTER TABLE groups_new RENAME TO groups"))
                
                # Update users table
                conn.execute(text("ALTER TABLE users DROP COLUMN group_id"))
                conn.execute(text("ALTER TABLE users RENAME COLUMN group_id_new TO group_id"))
                
                # Update association tables
                for table in ["group_permissions", "group_features"]:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                    conn.execute(text(f"ALTER TABLE {table}_new RENAME TO {table}"))
                
                # Update FlowStudio tables if they exist
                inspector = inspect(self.engine)
                tables = inspector.get_table_names()
                
                if "flow_studio_projects" in tables:
                    conn.execute(text("ALTER TABLE flow_studio_projects DROP COLUMN group_id"))
                    conn.execute(text("ALTER TABLE flow_studio_projects RENAME COLUMN group_id_new TO group_id"))
                    
                if "flow_studio_flows" in tables:
                    conn.execute(text("ALTER TABLE flow_studio_flows DROP COLUMN group_id"))
                    conn.execute(text("ALTER TABLE flow_studio_flows RENAME COLUMN group_id_new TO group_id"))
                
                # Add foreign key constraints
                conn.execute(text("""
                    ALTER TABLE users ADD CONSTRAINT fk_users_group_id 
                    FOREIGN KEY (group_id) REFERENCES groups(id)
                """))
                
                conn.execute(text("""
                    ALTER TABLE group_permissions ADD CONSTRAINT fk_group_permissions_group_id 
                    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
                """))
                
                conn.execute(text("""
                    ALTER TABLE group_features ADD CONSTRAINT fk_group_features_group_id 
                    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
                """))
                
                trans.commit()
                logger.info("Migration finalized successfully")
                
            except Exception as e:
                trans.rollback()
                raise e
    
    def verify_migration(self):
        """Verify migration completed successfully"""
        logger.info("Verifying migration...")
        
        with self.engine.connect() as conn:
            # Check groups table
            result = conn.execute(text("SELECT id, name FROM groups LIMIT 5"))
            logger.info("Groups table:")
            for row in result:
                logger.info(f"  ID: {row.id} ({type(row.id).__name__}), Name: {row.name}")
            
            # Check users with group assignments
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
        
        logger.info("Migration verification completed")
    
    def run_migration(self):
        """Execute the complete migration process"""
        try:
            logger.info("Starting Groups → UUID Migration")
            logger.info("=" * 50)
            
            # Step 1: Backup existing data
            backup_data = self.backup_existing_data()
            
            # Step 2: Migrate groups table
            self.migrate_groups_table()
            
            # Step 3: Update users table
            self.migrate_users_table()
            
            # Step 4: Migrate association tables
            self.migrate_association_tables()
            
            # Step 5: Update FlowStudio tables
            self.migrate_flow_studio_tables()
            
            # Step 6: Finalize migration
            self.finalize_migration()
            
            # Step 7: Verify migration
            self.verify_migration()
            
            logger.info("=" * 50)
            logger.info("Migration completed successfully!")
            logger.info(f"Backup file: {self.backup_file}")
            logger.info("UUID Mappings:")
            for old_id, new_uuid in self.uuid_mappings.items():
                logger.info(f"  {old_id} → {new_uuid}")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            logger.error("Please restore from backup if necessary")
            raise

if __name__ == "__main__":
    migration = GroupsMigration()
    migration.run_migration()