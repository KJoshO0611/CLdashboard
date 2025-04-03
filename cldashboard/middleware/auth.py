from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def owner_required(f):
    """Decorator to restrict access to bot owners only"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_owner:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to restrict access to admins and owners"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

def moderator_required(f):
    """Decorator to restrict access to moderators, admins, and owners"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_moderator:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

def guild_admin_required(f):
    """Decorator to restrict access to guild admins"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        guild_id = kwargs.get('guild_id')
        if not guild_id:
            flash('Invalid guild.', 'danger')
            return redirect(url_for('main.home'))
            
        if not current_user.is_authenticated:
            flash('You must be logged in to access this page.', 'danger')
            return redirect(url_for('auth.login'))
            
        # Check if the user is a bot owner or has admin permissions for this guild
        if not current_user.is_owner and not current_user.can_manage_guild(guild_id):
            flash('You do not have permission to manage this server.', 'danger')
            return redirect(url_for('dashboard.guild_overview', guild_id=guild_id))
            
        return f(*args, **kwargs)
    return decorated_function

def guild_view_required(f):
    """Decorator to restrict access to guild members"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        guild_id = kwargs.get('guild_id')
        if not guild_id:
            flash('Invalid guild.', 'danger')
            return redirect(url_for('main.home'))
            
        if not current_user.is_authenticated:
            flash('You must be logged in to access this page.', 'danger')
            return redirect(url_for('auth.login'))
            
        # Check if the user is a bot owner or has access to this guild
        if not current_user.is_owner and not current_user.can_view_guild(guild_id):
            flash('You do not have access to this server.', 'danger')
            return redirect(url_for('dashboard.guild_list'))
            
        return f(*args, **kwargs)
    return decorated_function 