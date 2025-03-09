#!/usr/bin/env python3
"""
Migration script to move API keys from password field to the new api_key field.
Run this once after updating the codebase if there are existing API keys.
"""

import os
import sys
import pathlib

# Add parent directories to path
parent_path = str(pathlib.Path(__file__).parent.absolute())
parent_parent_path = str(pathlib.Path(__file__).parent.parent.absolute())
sys.path.append(parent_parent_path)
sys.path.append(os.path.join(parent_parent_path, 'database'))

import configs
import security

def migrate_api_keys():
    """
    Migrate API keys from password field to api_key field.
    This is only needed if you were using the previous implementation
    where API keys were stored in the password field with a prefix.
    """
    print("Starting API key migration...")
    
    # Get database connection
    db_configs = configs.database_configs()
    conn = db_configs.conn
    cursor = conn.cursor()
    
    # Check if api_key column exists
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    column_names = [column[1] for column in columns]
    
    if 'api_key' not in column_names:
        print("Error: api_key column doesn't exist. Run the application first to apply the migration.")
        return False
    
    # Get all users
    cursor.execute("SELECT username, password FROM users")
    users = cursor.fetchall()
    
    migrated_count = 0
    
    for username, password in users:
        if password and password.startswith('api_key:'):
            # Extract API key
            api_key = password.split('api_key:')[1]
            
            # Store in new column
            cursor.execute("UPDATE users SET api_key = ? WHERE username = ?", (api_key, username))
            
            # Reset password to a new hashed random password 
            # (user will need to use password reset functionality)
            import random
            import string
            temp_password = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
            hashed_password = security.hash_password(temp_password)
            
            cursor.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_password, username))
            
            migrated_count += 1
            print(f"Migrated API key for user: {username}")
    
    # Commit changes
    conn.commit()
    
    print(f"Migration complete. Migrated {migrated_count} API keys.")
    if migrated_count > 0:
        print("IMPORTANT: Users with migrated API keys will need to reset their passwords!")
    
    return True

if __name__ == "__main__":
    migrate_api_keys() 