import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    def __init__(self):
        # Database configuration
        self.DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/lvl')
        
        # Discord configuration
        self.DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
        self.DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
        self.DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
        
        # Application configuration
        self.DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
        self.SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
        
        # Database pool settings
        self.DB_POOL_MIN_SIZE = int(os.getenv('DB_POOL_MIN_SIZE', '1'))
        self.DB_POOL_MAX_SIZE = int(os.getenv('DB_POOL_MAX_SIZE', '10'))
        self.DB_COMMAND_TIMEOUT = int(os.getenv('DB_COMMAND_TIMEOUT', '60')) 