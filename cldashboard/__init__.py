import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_session import Session
from flask_discord import DiscordOAuth2Session
from flask_wtf.csrf import CSRFProtect, generate_csrf
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize SQLAlchemy
db = SQLAlchemy()

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

# Initialize Discord OAuth
discord = DiscordOAuth2Session()

# Initialize CSRF protection
csrf = CSRFProtect()

def fix_database_url(url):
    """Fix database URL format issues"""
    if not url:
        return "sqlite:///site.db"
    
    # Check if this is a Render PostgreSQL URL
    # Render uses postgres:// but SQLAlchemy requires postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    
    return url

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Flask configuration
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or "dev-secret-key-change-in-production"
    
    # Fix database URL
    database_url = fix_database_url(os.getenv("DATABASE_URL"))
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Server-side session configuration
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_PERMANENT"] = True
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
    app.config["SESSION_FILE_DIR"] = os.path.join(app.root_path, "flask_session")
    app.config["SESSION_USE_SIGNER"] = True
    app.config["SESSION_COOKIE_SECURE"] = not os.getenv("DEBUG")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    
    # CSRF protection configuration
    app.config["WTF_CSRF_ENABLED"] = True
    app.config["WTF_CSRF_TIME_LIMIT"] = 3600  # 1 hour
    
    # Discord OAuth2 configuration
    app.config["DISCORD_CLIENT_ID"] = os.getenv("DISCORD_CLIENT_ID")
    app.config["DISCORD_CLIENT_SECRET"] = os.getenv("DISCORD_CLIENT_SECRET")
    app.config["DISCORD_REDIRECT_URI"] = os.getenv("DISCORD_REDIRECT_URI")
    app.config["DISCORD_BOT_TOKEN"] = os.getenv("DISCORD_BOT_TOKEN")
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    Session(app)
    csrf.init_app(app)
    discord.init_app(app)
    
    # Create flask_session directory if it doesn't exist
    os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
    
    # Add CSRF token to all templates
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf)
    
    # Register blueprints
    from cldashboard.routes.main import main
    from cldashboard.routes.auth import auth
    from cldashboard.routes.dashboard import dashboard
    from cldashboard.routes.admin import admin
    from cldashboard.routes.api import api
    
    app.register_blueprint(main)
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(dashboard)
    app.register_blueprint(admin)
    app.register_blueprint(api)
    
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
    
    return app 