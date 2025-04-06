import os
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_session import Session
from flask_discord import DiscordOAuth2Session
from flask_wtf.csrf import CSRFProtect, generate_csrf
from datetime import timedelta, datetime
from dotenv import load_dotenv
from .config import Config
import logging
from logging.handlers import RotatingFileHandler
from sqlalchemy import text
from pathlib import Path
import subprocess
from flask_migrate import Migrate

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

# Initialize Flask-Migrate
migrate = Migrate()

def fix_database_url(url):
    """Fix database URL format issues"""
    if not url:
        return "sqlite:///site.db"
    
    # Check if this is a Render PostgreSQL URL
    # Render uses postgres:// but SQLAlchemy requires postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    
    return url

def create_app(config_class=Config):
    """Create and configure the Flask application"""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    
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
    app.config["SESSION_COOKIE_SECURE"] = False  # Set to False to allow both HTTP and HTTPS
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = None  # Allow cross-site cookies during OAuth flow
    
    # CSRF protection configuration
    app.config["WTF_CSRF_ENABLED"] = True
    app.config["WTF_CSRF_TIME_LIMIT"] = 3600  # 1 hour
    
    # Discord OAuth2 configuration
    app.config["DISCORD_CLIENT_ID"] = os.getenv("DISCORD_CLIENT_ID")
    app.config["DISCORD_CLIENT_SECRET"] = os.getenv("DISCORD_CLIENT_SECRET")
    app.config["DISCORD_REDIRECT_URI"] = os.getenv("DISCORD_REDIRECT_URI")
    app.config["DISCORD_BOT_TOKEN"] = os.getenv("DISCORD_BOT_TOKEN")
    
    # --- Default Upload Configuration (for local development) --- 
    # Adjust these paths as needed for your local setup
    # Use commas, os.path.join handles separators
    default_upload_folder = os.path.join(app.root_path, '..', 'uploads', 'achievements') 
    app.config.setdefault('UPLOAD_FOLDER', default_upload_folder)
    app.config.setdefault('UPLOAD_URL_BASE', '/uploads/achievements/')
    app.config.setdefault('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif', 'webp'})
    # Ensure the default local upload folder exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        try:
            os.makedirs(app.config['UPLOAD_FOLDER'])
            app.logger.info(f"Created default local upload directory: {app.config['UPLOAD_FOLDER']}")
        except OSError as e:
            app.logger.error(f"Error creating default local upload directory {app.config['UPLOAD_FOLDER']}: {e}")

    # Override with instance config if it exists
    app.config.from_pyfile('config.py', silent=True)
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    Session(app)
    csrf.init_app(app)
    discord.init_app(app)
    migrate.init_app(app, db)
    
    # Create flask_session directory if it doesn't exist
    os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
    
    # Add CSRF token to all templates
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf)
    
    # Add custom Jinja filters
    @app.template_filter('datetime')
    def format_datetime(value):
        """Format a datetime string to a readable format"""
        if not value:
            return ""
        try:
            if isinstance(value, str):
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            else:
                dt = value
            return dt.strftime('%b %d, %Y %I:%M %p')
        except Exception as e:
            print(f"Error formatting datetime: {e}")
            return value
    
    # Configure logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/cldashboard.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('CLDashboard startup')
    
    # Register blueprints
    from .routes.main import main
    from .routes.auth import auth
    from .routes.dashboard import dashboard
    from .routes.admin import admin
    from .routes.api import api
    
    app.register_blueprint(main)
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(dashboard)
    app.register_blueprint(admin)
    app.register_blueprint(api)
    
    # Create database tables
    with app.app_context():
        try:
            # Create tables that SQLAlchemy knows about (for new installations)
            # db.create_all() # Comment this out or remove, let migrations handle it
            
            # Let the app know migrations are disabled
            # app.logger.info('Database migrations disabled')
            app.logger.info('Database migrations enabled via Flask-Migrate')
                
        except Exception as e:
            app.logger.error(f'Database initialization error: {str(e)}')
            # Don't raise the error, allow the app to start even if tables exist
    
    # Configure error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()  # Roll back db session in case of errors
        app.logger.error(f'Internal server error: {str(error)}')
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(502)
    def bad_gateway_error(error):
        app.logger.error(f'Bad gateway error: {str(error)}')
        return render_template('errors/502.html'), 502
    
    @app.before_request
    def before_request():
        # Only test connection for non-static routes
        if not request.path.startswith('/static/'):
            try:
                # Use a lightweight connection test
                db.session.execute(text('SELECT 1')).scalar()
            except Exception as e:
                app.logger.error(f'Database connection error: {str(e)}')
                db.session.rollback()
                # Don't raise the error, let the request continue
    
    @app.after_request
    def after_request(response):
        # Only commit for non-static routes
        if not request.path.startswith('/static/'):
            try:
                db.session.commit()
            except Exception as e:
                app.logger.error(f'Database commit error: {str(e)}')
                db.session.rollback()
        return response
    
    # Add request timeout handling
    @app.before_request
    def timeout_handler():
        # Set a timeout for the request
        request.timeout = app.config['WORKER_TIMEOUT']
    
    # Add memory cleanup
    @app.teardown_appcontext
    def cleanup(error):
        # Clean up any resources
        db.session.remove()
        if error:
            db.session.rollback()
    
    return app 