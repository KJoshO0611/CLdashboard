#!/usr/bin/env python3
"""
Environment Switcher Script

This script helps switch between local and production environments
by updating redirect URIs and testing various parts of the application.
"""
import os
import sys
import requests
from dotenv import load_dotenv, set_key

def print_header(text):
    """Print a header with the given text"""
    print("\n" + "=" * 80)
    print(f" {text} ".center(80, "-"))
    print("=" * 80)

def switch_to_local():
    """Switch to local development environment"""
    print_header("Switching to Local Environment")
    
    # Test if .env.local exists
    if not os.path.exists('.env.local'):
        print("Error: .env.local file not found!")
        print("Create a .env.local file with local configuration first.")
        sys.exit(1)
    
    # Make a copy of .env if it doesn't exist
    if not os.path.exists('.env.backup'):
        print("Creating backup of .env to .env.backup...")
        try:
            with open('.env', 'r') as src, open('.env.backup', 'w') as dst:
                dst.write(src.read())
            print("Backup created successfully.")
        except Exception as e:
            print(f"Error creating backup: {e}")
            sys.exit(1)
    
    # Copy .env.local to .env
    print("Copying .env.local to .env...")
    try:
        with open('.env.local', 'r') as src, open('.env', 'w') as dst:
            dst.write(src.read())
        print("Local environment activated.")
    except Exception as e:
        print(f"Error setting local environment: {e}")
        sys.exit(1)
    
    print("\nLocal Environment Setup Complete!")
    print("Run your application with: python run_local.py")

def switch_to_production():
    """Switch back to production environment"""
    print_header("Switching to Production Environment")
    
    # Check if backup exists
    if not os.path.exists('.env.backup'):
        print("Error: .env.backup file not found!")
        print("Cannot restore production environment without backup.")
        sys.exit(1)
    
    # Restore .env from backup
    print("Restoring .env from .env.backup...")
    try:
        with open('.env.backup', 'r') as src, open('.env', 'w') as dst:
            dst.write(src.read())
        print("Production environment restored.")
    except Exception as e:
        print(f"Error restoring production environment: {e}")
        sys.exit(1)
    
    print("\nProduction Environment Setup Complete!")

def test_environment():
    """Test the current environment configuration"""
    print_header("Testing Environment")
    
    # Load current environment
    load_dotenv()
    
    print("Current Environment Variables:")
    print(f"FLASK_ENV: {os.getenv('FLASK_ENV')}")
    print(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")
    print(f"DISCORD_REDIRECT_URI: {os.getenv('DISCORD_REDIRECT_URI')}")
    
    # Check if we can connect to the database
    db_url = os.getenv('DATABASE_URL', '')
    if 'postgres' in db_url.lower():
        print("\nTesting database connection...")
        try:
            import psycopg2
            # Extract connection details from the URL
            url_parts = db_url.replace('postgresql://', '').replace('postgres://', '')
            credentials, address = url_parts.split('@')
            user_pass, host_port_db = address.split('/')
            user, password = credentials.split(':')
            host_port = host_port_db.split(':')
            host = host_port[0]
            port = int(host_port[1].split('/')[0]) if ':' in host_port[0] else 5432
            dbname = host_port_db.split('/')[-1]
            
            # Test connection
            conn = psycopg2.connect(
                dbname=dbname,
                user=user,
                password=password,
                host=host,
                port=port
            )
            conn.close()
            print("✓ Database connection successful!")
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
    else:
        print("\nSkipping database test for non-PostgreSQL database.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python switch_env.py [local|prod|test]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'local':
        switch_to_local()
    elif command in ['prod', 'production']:
        switch_to_production()
    elif command == 'test':
        test_environment()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python switch_env.py [local|prod|test]")
        sys.exit(1) 