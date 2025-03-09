import sqlite3
from typing import List, Tuple

def get_table_schema(cursor, table_name: str) -> List[Tuple]:
    """Get the current schema of a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return cursor.fetchall()

def get_expected_schemas() -> dict:
    """Define the expected schema for each table"""
    return {
        'users': [
            ('username', 'text', 1, None, 0),  # (name, type, notnull, dflt_value, pk)
            ('password', 'text', 1, "'admin'", 0),
            ('admin', 'bool', 1, '0', 0),
            ('order_manager', 'bool', 1, '0', 0),
            ('name', 'text', 0, None, 0),
            ('email', 'text', 0, None, 0),
            ('email_enabled', 'bool', 1, '1', 0),
            ('id', 'integer', 0, None, 1)
        ],
        'messages': [
            ('id', 'integer', 0, None, 1),
            ('author', 'text', 1, None, 0),
            ('message', 'text', 1, None, 0),
            ('date', 'text', 1, None, 0),
            ('destination', 'text', 1, None, 0),
            ('read', 'integer', 0, '0', 0)
        ],
        'notifications': [
            ('id', 'integer', 0, None, 1),
            ('author', 'text', 1, None, 0),
            ('message', 'text', 1, None, 0),
            ('date', 'text', 1, None, 0),
            ('destination', 'text', 1, None, 0),
            ('read', 'integer', 0, '0', 0),
            ('type', 'text', 1, None, 0),
            ('reference_id', 'integer', 0, None, 0),
        ]
        # Add other tables as needed
    }

def migrate_database():
    """Check and update all tables to match expected schema"""
    try:
        conn = sqlite3.connect('./src/database/db_main.db')
        cursor = conn.cursor()
        
        # Get list of all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [table[0] for table in cursor.fetchall()]
        
        expected_schemas = get_expected_schemas()
        migrations_performed = []
        
        for table_name, expected_columns in expected_schemas.items():
            if table_name not in existing_tables:
                continue
                
            current_schema = get_table_schema(cursor, table_name)
            current_columns = [col[1] for col in current_schema]
            
            # Check for missing columns
            for col_name, col_type, notnull, default, pk in expected_columns:
                if col_name not in current_columns:
                    default_str = f"DEFAULT {default}" if default else ""
                    notnull_str = "NOT NULL" if notnull else ""
                    
                    alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} {notnull_str} {default_str}"
                    cursor.execute(alter_sql.strip())
                    migrations_performed.append(f"Added column {col_name} to {table_name}")
                    
                    # Special case for email_enabled: set default value for existing rows
                    if col_name == 'email_enabled':
                        cursor.execute(f"UPDATE {table_name} SET email_enabled = 1 WHERE email_enabled IS NULL")
                        migrations_performed.append(f"Set default email_enabled=1 for existing users")
            
            conn.commit()
        
        conn.close()
        
        if migrations_performed:
            print("Database migrations performed:")
            for migration in migrations_performed:
                print(f"- {migration}")
        else:
            print("Database schema is up to date")
            
        return True
        
    except Exception as e:
        print(f"Error during database migration: {str(e)}")
        return False

def add_api_key_to_users_table(conn):
    """Add api_key column to users table for browser extension authentication"""
    try:
        cursor = conn.cursor()
        
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'api_key' not in column_names:
            cursor.execute("ALTER TABLE users ADD COLUMN api_key TEXT")
            conn.commit()
            print("Added api_key column to users table")
            return True
        else:
            print("api_key column already exists in users table")
            return False
    except Exception as e:
        print(f"Error adding api_key column to users table: {str(e)}")
        return False

if __name__ == "__main__":
    migrate_database() 