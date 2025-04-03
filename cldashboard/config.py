import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 3,  # Reduced pool size
        'max_overflow': 5,  # Reduced max overflow
        'pool_recycle': 1800,  # Recycle connections after 30 minutes
        'pool_pre_ping': True,  # Enable connection health checks
        'connect_args': {
            'sslmode': 'require',  # Force SSL
            'connect_timeout': 3,  # Reduced timeout
            'keepalives': 1,  # Enable keepalive
            'keepalives_idle': 30,  # Send keepalive every 30 seconds
            'keepalives_interval': 10,  # Retry keepalive every 10 seconds
            'keepalives_count': 3  # Reduced retry count
        }
    }
    
    # Discord OAuth2 settings
    DISCORD_CLIENT_ID = os.environ.get('DISCORD_CLIENT_ID')
    DISCORD_CLIENT_SECRET = os.environ.get('DISCORD_CLIENT_SECRET')
    DISCORD_REDIRECT_URI = os.environ.get('DISCORD_REDIRECT_URI')
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Application settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year cache for static files
    
    # Worker settings
    WORKER_TIMEOUT = 30  # 30 seconds timeout
    WORKER_KEEPALIVE = 5  # 5 seconds keepalive 