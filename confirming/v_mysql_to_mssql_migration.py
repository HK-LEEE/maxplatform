#!/usr/bin/env python3
"""
MySQL to MSSQL Data Migration Script
GenbaX Platform Database Migration

This script migrates all data from MySQL to MSSQL while preserving
foreign key relationships and data integrity.
"""

import pymysql
import pyodbc
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Any
import json
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class DatabaseMigrator:
    def __init__(self, mysql_config: Dict, mssql_config: Dict):
        """
        Initialize database migrator with connection configurations
        
        Args:
            mysql_config: MySQL connection parameters
            mssql_config: MSSQL connection parameters
        """
        self.mysql_config = mysql_config
        self.mssql_config = mssql_config
        self.mysql_conn = None
        self.mssql_conn = None
        
        # Define table migration order (respecting foreign key dependencies)
        self.migration_order = [
            'roles',
            'service_categories', 
            'permissions',
            'features',
            'users',  # depends on roles (role_id)
            'groups',  # depends on users (created_by)
            'workspaces',  # depends on users (owner_id)
            'services',  # depends on users (created_by)
            'user_service_permissions',  # depends on users, services
            # Association tables
            'user_permissions',
            'user_features', 
            'role_permissions',
            'role_features',
            'group_permissions',
            'group_features',
            'user_services',
            'role_services'
        ]
    
    def connect_mysql(self):
        """Connect to MySQL database"""
        try:
            self.mysql_conn = pymysql.connect(**self.mysql_config)
            logging.info("✅ Connected to MySQL database")
        except Exception as e:
            logging.error(f"❌ Failed to connect to MySQL: {e}")
            raise
    
    def connect_mssql(self):
        """Connect to MSSQL database"""
        try:
            # Build connection string
            conn_str = f"""
                DRIVER={{{self.mssql_config['driver']}}};
                SERVER={self.mssql_config['server']};
                DATABASE={self.mssql_config['database']};
                UID={self.mssql_config['username']};
                PWD={self.mssql_config['password']};
                TrustServerCertificate=yes;
            """
            self.mssql_conn = pyodbc.connect(conn_str.replace('\n', '').replace(' ', ''))
            logging.info("✅ Connected to MSSQL database")
        except Exception as e:
            logging.error(f"❌ Failed to connect to MSSQL: {e}")
            raise
    
    def get_table_data(self, table_name: str) -> Tuple[List[str], List[Tuple]]:
        """
        Fetch all data from MySQL table
        
        Returns:
            Tuple of (column_names, rows)
        """
        try:
            with self.mysql_conn.cursor() as cursor:
                # Get column names
                cursor.execute(f"DESCRIBE {table_name}")
                columns = [row[0] for row in cursor.fetchall()]
                
                # Get all data
                cursor.execute(f"SELECT * FROM {table_name} ORDER BY id")
                rows = cursor.fetchall()
                
                logging.info(f"📊 Fetched {len(rows)} rows from {table_name}")
                return columns, rows
                
        except Exception as e:
            logging.error(f"❌ Failed to fetch data from {table_name}: {e}")
            raise
    
    def get_table_exists(self, table_name: str) -> bool:
        """Check if table exists in MySQL"""
        try:
            with self.mysql_conn.cursor() as cursor:
                cursor.execute(f"""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = '{self.mysql_config['database']}' 
                    AND table_name = '{table_name}'
                """)
                return cursor.fetchone()[0] > 0
        except Exception as e:
            logging.warning(f"⚠️ Could not check if table {table_name} exists: {e}")
            return False
    
    def clear_mssql_table(self, table_name: str):
        """Clear MSSQL table data"""
        try:
            with self.mssql_conn.cursor() as cursor:
                # Disable foreign key constraints temporarily
                cursor.execute("ALTER TABLE {} NOCHECK CONSTRAINT ALL".format(table_name))
                cursor.execute(f"DELETE FROM {table_name}")
                cursor.execute("ALTER TABLE {} CHECK CONSTRAINT ALL".format(table_name))
                self.mssql_conn.commit()
                logging.info(f"🧹 Cleared table {table_name}")
        except Exception as e:
            logging.warning(f"⚠️ Could not clear table {table_name}: {e}")
    
    def insert_data(self, table_name: str, columns: List[str], rows: List[Tuple]):
        """Insert data into MSSQL table"""
        if not rows:
            logging.info(f"📭 No data to insert for {table_name}")
            return
        
        try:
            with self.mssql_conn.cursor() as cursor:
                # Handle IDENTITY columns
                has_identity = table_name in ['roles', 'groups', 'workspaces', 'services', 
                                            'service_categories', 'permissions', 'features', 
                                            'user_service_permissions']
                
                if has_identity:
                    cursor.execute(f"SET IDENTITY_INSERT {table_name} ON")
                
                # Create placeholders for SQL query
                placeholders = ', '.join(['?' for _ in columns])
                column_list = ', '.join(columns)
                
                insert_query = f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})"
                
                # Convert MySQL data types to MSSQL compatible types
                converted_rows = []
                for row in rows:
                    converted_row = []
                    for i, value in enumerate(row):
                        # Convert MySQL boolean (tinyint) to MSSQL bit
                        if isinstance(value, int) and columns[i] in [
                            'is_active', 'is_admin', 'is_verified', 'is_public', 
                            'is_external', 'requires_auth', 'open_in_new_tab',
                            'auto_grant', 'requires_approval'
                        ]:
                            converted_row.append(bool(value))
                        # Convert datetime
                        elif isinstance(value, datetime):
                            converted_row.append(value)
                        else:
                            converted_row.append(value)
                    converted_rows.append(tuple(converted_row))
                
                # Batch insert
                cursor.executemany(insert_query, converted_rows)
                
                if has_identity:
                    cursor.execute(f"SET IDENTITY_INSERT {table_name} OFF")
                
                self.mssql_conn.commit()
                logging.info(f"✅ Inserted {len(rows)} rows into {table_name}")
                
        except Exception as e:
            logging.error(f"❌ Failed to insert data into {table_name}: {e}")
            if has_identity:
                try:
                    with self.mssql_conn.cursor() as cursor:
                        cursor.execute(f"SET IDENTITY_INSERT {table_name} OFF")
                        self.mssql_conn.commit()
                except:
                    pass
            raise
    
    def migrate_table(self, table_name: str):
        """Migrate a single table from MySQL to MSSQL"""
        logging.info(f"🔄 Migrating table: {table_name}")
        
        # Check if table exists in MySQL
        if not self.get_table_exists(table_name):
            logging.warning(f"⚠️ Table {table_name} does not exist in MySQL, skipping...")
            return
        
        # Clear existing data in MSSQL
        self.clear_mssql_table(table_name)
        
        # Get data from MySQL
        columns, rows = self.get_table_data(table_name)
        
        # Insert data into MSSQL
        self.insert_data(table_name, columns, rows)
    
    def verify_migration(self):
        """Verify data migration integrity"""
        logging.info("🔍 Verifying migration...")
        
        verification_results = {}
        
        for table_name in self.migration_order:
            if not self.get_table_exists(table_name):
                continue
                
            try:
                # Count rows in MySQL
                with self.mysql_conn.cursor() as cursor:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    mysql_count = cursor.fetchone()[0]
                
                # Count rows in MSSQL
                with self.mssql_conn.cursor() as cursor:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    mssql_count = cursor.fetchone()[0]
                
                verification_results[table_name] = {
                    'mysql_count': mysql_count,
                    'mssql_count': mssql_count,
                    'match': mysql_count == mssql_count
                }
                
                status = "✅" if mysql_count == mssql_count else "❌"
                logging.info(f"{status} {table_name}: MySQL({mysql_count}) -> MSSQL({mssql_count})")
                
            except Exception as e:
                logging.error(f"❌ Failed to verify {table_name}: {e}")
                verification_results[table_name] = {'error': str(e)}
        
        return verification_results
    
    def run_migration(self):
        """Run complete migration process"""
        try:
            logging.info("🚀 Starting MySQL to MSSQL migration...")
            
            # Connect to databases
            self.connect_mysql()
            self.connect_mssql()
            
            # Disable foreign key checks in MSSQL temporarily
            with self.mssql_conn.cursor() as cursor:
                cursor.execute("EXEC sp_MSforeachtable 'ALTER TABLE ? NOCHECK CONSTRAINT ALL'")
                self.mssql_conn.commit()
            
            # Migrate tables in order
            for table_name in self.migration_order:
                self.migrate_table(table_name)
            
            # Re-enable foreign key checks
            with self.mssql_conn.cursor() as cursor:
                cursor.execute("EXEC sp_MSforeachtable 'ALTER TABLE ? CHECK CONSTRAINT ALL'")
                self.mssql_conn.commit()
            
            # Verify migration
            verification = self.verify_migration()
            
            # Report results
            successful_tables = sum(1 for v in verification.values() 
                                  if isinstance(v, dict) and v.get('match', False))
            total_tables = len([t for t in self.migration_order if self.get_table_exists(t)])
            
            logging.info(f"🎉 Migration completed: {successful_tables}/{total_tables} tables successful")
            
            return verification
            
        except Exception as e:
            logging.error(f"💥 Migration failed: {e}")
            raise
        finally:
            # Close connections
            if self.mysql_conn:
                self.mysql_conn.close()
                logging.info("🔌 MySQL connection closed")
            if self.mssql_conn:
                self.mssql_conn.close()
                logging.info("🔌 MSSQL connection closed")

def main():
    """Main migration function"""
    
    # Database configurations
    mysql_config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'your_mysql_password',
        'database': 'jupyter_platform',
        'charset': 'utf8mb4'
    }
    
    mssql_config = {
        'driver': 'ODBC Driver 17 for SQL Server',
        'server': 'localhost',
        'database': 'jupyter_platform_mssql',
        'username': 'sa',
        'password': 'your_mssql_password'
    }
    
    # Override with environment variables if available
    import os
    mysql_config.update({
        'host': os.getenv('MYSQL_HOST', mysql_config['host']),
        'port': int(os.getenv('MYSQL_PORT', mysql_config['port'])),
        'user': os.getenv('MYSQL_USER', mysql_config['user']),
        'password': os.getenv('MYSQL_PASSWORD', mysql_config['password']),
        'database': os.getenv('MYSQL_DATABASE', mysql_config['database'])
    })
    
    mssql_config.update({
        'server': os.getenv('MSSQL_SERVER', mssql_config['server']),
        'database': os.getenv('MSSQL_DATABASE', mssql_config['database']),
        'username': os.getenv('MSSQL_USERNAME', mssql_config['username']),
        'password': os.getenv('MSSQL_PASSWORD', mssql_config['password'])
    })
    
    # Run migration
    migrator = DatabaseMigrator(mysql_config, mssql_config)
    
    try:
        results = migrator.run_migration()
        
        # Save verification results
        with open(f'migration_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
            
        logging.info("📋 Migration results saved to JSON file")
        
    except Exception as e:
        logging.error(f"💥 Migration process failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 