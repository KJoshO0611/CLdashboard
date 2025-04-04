#!/usr/bin/env python
import os
import psycopg2
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_local_database():
    """Run the SQL setup script against a local PostgreSQL database"""
    # Get the database URL from environment, default to a local development connection
    database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/lvlbot')
    
    # Ensure PostgreSQL format
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    print(f"Setting up database: {database_url}")
    
    try:
        # Connect to the database
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        cursor = conn.cursor()
        
        # Read the SQL script
        with open('create_local_db.sql', 'r') as f:
            sql_script = f.read()
        
        # Execute the script
        cursor.execute(sql_script)
        
        # Commit the changes
        conn.commit()
        print("Database setup completed successfully!")
        
    except Exception as e:
        print(f"Error setting up database: {e}")
        if 'conn' in locals():
            conn.rollback()
        sys.exit(1)
    finally:
        # Close the connection
        if 'conn' in locals():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    # Check if we want to include user-specific data
    if len(sys.argv) > 1:
        your_discord_id = sys.argv[1]
        your_username = sys.argv[2] if len(sys.argv) > 2 else "YourUsername"
        
        print(f"Adding user {your_username} with ID {your_discord_id} to database")
        
        # Update the SQL file to include your Discord ID
        with open('create_local_db.sql', 'r') as f:
            sql_content = f.read()
        
        # Uncomment and update the user-specific INSERT statements
        sql_content = sql_content.replace('-- INSERT INTO users (discord_id', 'INSERT INTO users (discord_id')
        sql_content = sql_content.replace('-- VALUES (YOUR_DISCORD_ID', f'VALUES ({your_discord_id}')
        sql_content = sql_content.replace('YourUsername', your_username)
        
        # Uncomment user_guild insertions
        sql_content = sql_content.replace('-- INSERT INTO user_guild (user_id, guild_id)', 'INSERT INTO user_guild (user_id, guild_id)')
        sql_content = sql_content.replace('--     (YOUR_DISCORD_ID', f'    ({your_discord_id}')
        
        # Write the updated SQL back to the file
        with open('create_local_db.sql', 'w') as f:
            f.write(sql_content)
    
    setup_local_database() 