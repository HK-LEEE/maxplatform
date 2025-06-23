#!/usr/bin/env python3
"""
MySQL to PostgreSQL User Migration Script

This script migrates user data from MySQL to PostgreSQL while preserving
password hashes and other user information.
"""

import os
import sys
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

import pymysql
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """Handles migration from MySQL to PostgreSQL"""
    
    def __init__(self):
        """Initialize database connections"""
        self.mysql_conn = None
        self.postgresql_conn = None
        
        # MySQL connection parameters
        self.mysql_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', 'jupyter_platform'),
            'charset': 'utf8mb4'
        }
        
        # PostgreSQL connection parameters
        self.postgresql_config = {
            'host': os.getenv('POSTGRESQL_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRESQL_PORT', 5432)),
            'user': os.getenv('POSTGRESQL_USER', 'postgres'),
            'password': os.getenv('POSTGRESQL_PASSWORD', ''),
            'database': os.getenv('POSTGRESQL_DATABASE', 'auth_system')
        }
    
    def connect_mysql(self) -> bool:
        """Connect to MySQL database"""
        try:
            self.mysql_conn = pymysql.connect(**self.mysql_config)
            logger.info("Successfully connected to MySQL database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            return False
    
    def connect_postgresql(self) -> bool:
        """Connect to PostgreSQL database"""
        try:
            self.postgresql_conn = psycopg2.connect(**self.postgresql_config)
            logger.info("Successfully connected to PostgreSQL database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return False
    
    def fetch_users_from_mysql(self) -> List[Dict[str, Any]]:
        """Fetch all users from MySQL database"""
        if not self.mysql_conn:
            logger.error("MySQL connection not established")
            return []
        
        try:
            with self.mysql_conn.cursor(pymysql.cursors.DictCursor) as cursor:
                # Adjust the table name and column names based on your existing schema
                query = """
                SELECT 
                    id,
                    username,
                    password,
                    `group`,
                    department,
                    created_at,
                    updated_at
                FROM users 
                ORDER BY id
                """
                cursor.execute(query)
                users = cursor.fetchall()
                logger.info(f"Fetched {len(users)} users from MySQL")
                return users
        except Exception as e:
            logger.error(f"Failed to fetch users from MySQL: {e}")
            return []
    
    def insert_users_to_postgresql(self, users: List[Dict[str, Any]]) -> bool:
        """Insert users into PostgreSQL database"""
        if not self.postgresql_conn or not users:
            logger.error("PostgreSQL connection not established or no users to migrate")
            return False
        
        try:
            with self.postgresql_conn.cursor() as cursor:
                # Clear existing data (optional - remove if you want to preserve existing data)
                cursor.execute("TRUNCATE TABLE refresh_tokens, users RESTART IDENTITY CASCADE")
                logger.info("Cleared existing data from PostgreSQL tables")
                
                # Insert users
                insert_query = """
                INSERT INTO users (username, password, "group", department, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (username) DO UPDATE SET
                    password = EXCLUDED.password,
                    "group" = EXCLUDED."group",
                    department = EXCLUDED.department,
                    updated_at = EXCLUDED.updated_at
                """
                
                inserted_count = 0
                for user in users:
                    try:
                        cursor.execute(insert_query, (
                            user['username'],
                            user['password'],  # Password hash is preserved as-is
                            user.get('group'),
                            user.get('department'),
                            user.get('created_at', datetime.now()),
                            user.get('updated_at', datetime.now())
                        ))
                        inserted_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert user {user['username']}: {e}")
                
                self.postgresql_conn.commit()
                logger.info(f"Successfully inserted {inserted_count} users into PostgreSQL")
                return True
                
        except Exception as e:
            logger.error(f"Failed to insert users into PostgreSQL: {e}")
            if self.postgresql_conn:
                self.postgresql_conn.rollback()
            return False
    
    def verify_migration(self) -> bool:
        """Verify that the migration was successful"""
        if not self.mysql_conn or not self.postgresql_conn:
            logger.error("Database connections not established")
            return False
        
        try:
            # Count users in MySQL
            with self.mysql_conn.cursor() as mysql_cursor:
                mysql_cursor.execute("SELECT COUNT(*) as count FROM users")
                mysql_count = mysql_cursor.fetchone()[0]
            
            # Count users in PostgreSQL
            with self.postgresql_conn.cursor() as pg_cursor:
                pg_cursor.execute("SELECT COUNT(*) as count FROM users")
                pg_count = pg_cursor.fetchone()[0]
            
            logger.info(f"MySQL users: {mysql_count}, PostgreSQL users: {pg_count}")
            
            if mysql_count == pg_count:
                logger.info("Migration verification successful!")
                return True
            else:
                logger.warning("User count mismatch between databases")
                return False
                
        except Exception as e:
            logger.error(f"Failed to verify migration: {e}")
            return False
    
    def close_connections(self):
        """Close database connections"""
        if self.mysql_conn:
            self.mysql_conn.close()
            logger.info("Closed MySQL connection")
        
        if self.postgresql_conn:
            self.postgresql_conn.close()
            logger.info("Closed PostgreSQL connection")
    
    def migrate(self) -> bool:
        """Execute the complete migration process"""
        logger.info("Starting user migration from MySQL to PostgreSQL")
        
        # Connect to databases
        if not self.connect_mysql():
            return False
        
        if not self.connect_postgresql():
            return False
        
        # Fetch users from MySQL
        users = self.fetch_users_from_mysql()
        if not users:
            logger.error("No users found to migrate")
            return False
        
        # Insert users into PostgreSQL
        if not self.insert_users_to_postgresql(users):
            return False
        
        # Verify migration
        if not self.verify_migration():
            logger.warning("Migration completed but verification failed")
        
        logger.info("Migration completed successfully!")
        return True


def main():
    """Main function to run the migration"""
    migrator = DatabaseMigrator()
    
    try:
        success = migrator.migrate()
        if success:
            logger.info("User migration completed successfully!")
            sys.exit(0)
        else:
            logger.error("User migration failed!")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        sys.exit(1)
    
    finally:
        migrator.close_connections()


if __name__ == "__main__":
    main() 