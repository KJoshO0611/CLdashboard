from flask import Blueprint, render_template, flash, redirect, url_for, request, abort
from flask_login import login_required
from .. import db
from ..models.user import Guild, ServerConfig, ServerXpSettings, GuildEventSettings
from ..middleware.auth import owner_required, admin_required, guild_admin_required
from .. import db
from ..models.user import Guild, ServerConfig, ServerXpSettings, GuildEventSettings
from ..middleware.auth import owner_required, admin_required, guild_admin_required

admin = Blueprint('admin', __name__)

# Bot Owner Routes
@admin.route('/admin')
@login_required
@owner_required
def index():
    """Admin dashboard for bot owners"""
    return render_template('admin/index.html', title='Admin Dashboard')

@admin.route('/admin/users')
@login_required
@owner_required
def users():
    """User management for bot owners"""
    return render_template('admin/users.html', title='User Management')

@admin.route('/admin/guilds')
@login_required
@owner_required
def guilds():
    """Guild management for bot owners"""
    return render_template('admin/guilds.html', title='Guild Management')

@admin.route('/admin/settings')
@login_required
@owner_required
def settings():
    """Global bot settings for bot owners"""
    return render_template('admin/settings.html', title='Bot Settings')

# Server Admin Routes
@admin.route('/dashboard/guilds/<guild_id>/settings')
@login_required
@guild_admin_required
def guild_settings(guild_id):
    """Settings for a specific guild"""
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    
    if not guild:
        abort(404)
    
    # Get or create guild settings
    settings = guild.settings
    if not settings:
        settings = ServerConfig(guild_id=guild.guild_id)
        db.session.add(settings)
        db.session.commit()
    
    return render_template(
        'admin/guild_settings.html', 
        title=f'{guild.name} - Settings', 
        guild=guild,
        settings=settings
    )

@admin.route('/dashboard/guilds/<guild_id>/xp')
@login_required
@guild_admin_required
def guild_xp_settings(guild_id):
    """XP settings for a specific guild"""
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    
    if not guild:
        abort(404)
    
    # Get or create XP settings
    xp_settings = guild.xp_settings
    if not xp_settings:
        xp_settings = ServerXpSettings(guild_id=guild.guild_id)
        db.session.add(xp_settings)
        db.session.commit()
    
    return render_template(
        'admin/guild_xp_settings.html', 
        title=f'{guild.name} - XP Settings', 
        guild=guild,
        xp_settings=xp_settings
    )

@admin.route('/dashboard/guilds/<guild_id>/level_roles')
@login_required
@guild_admin_required
def guild_roles(guild_id):
    """Role rewards settings for a specific guild"""
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    
    if not guild:
        abort(404)
    
    # Fetch level roles (already sorted by level due to relationship definition)
    level_roles = guild.level_roles 
    
    # Fetch server config for stack/announce settings
    settings = guild.settings
    if not settings:
        # Create settings if they don't exist (should ideally exist, but safety check)
        settings = ServerConfig(guild_id=guild.guild_id)
        db.session.add(settings)
        db.session.commit()
        # Re-fetch after commit if needed, or pass the new object
        settings = guild.settings # Re-fetch to ensure it's attached to the session properly

    return render_template(
        'admin/guild_roles.html', 
        title=f'{guild.name} - Role Rewards', 
        guild=guild,
        role_rewards=level_roles, # Pass the fetched level roles
        settings=settings # Pass the settings object
    )

@admin.route('/dashboard/guilds/<guild_id>/achievements/manage')
@login_required
@guild_admin_required
def manage_achievements(guild_id):
    """Achievement management for a specific guild"""
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    
    if not guild:
        abort(404)
        
    # Fetch server config for achievement settings
    settings = guild.settings
    if not settings:
        # Create settings if they don't exist (should ideally exist, but safety check)
        settings = ServerConfig(guild_id=guild.guild_id)
        db.session.add(settings)
        db.session.commit()
        settings = guild.settings # Re-fetch
        
    # Fetch server config for achievement settings
    settings = guild.settings
    if not settings:
        # Create settings if they don't exist (should ideally exist, but safety check)
        settings = ServerConfig(guild_id=guild.guild_id)
        db.session.add(settings)
        db.session.commit()
        settings = guild.settings # Re-fetch
    
    return render_template(
        'admin/manage_achievements.html', 
        title=f'{guild.name} - Manage Achievements', 
        guild=guild,
        settings=settings # Pass settings object
        guild=guild,
        settings=settings # Pass settings object
    )

@admin.route('/dashboard/guilds/<guild_id>/events/manage')
@login_required
@guild_admin_required
def manage_events(guild_id):
    """Event management for a specific guild"""
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    
    if not guild:
        abort(404)
        
    # Fetch server config for event channel settings
    settings = guild.settings # General settings (like event_channel)
    if not settings:
        settings = ServerConfig(guild_id=guild.guild_id)
        db.session.add(settings)
        db.session.commit()
        settings = guild.settings # Re-fetch
        
    # Fetch specific event settings (like bonus XP)
    event_settings = guild.event_settings
    if not event_settings:
        event_settings = GuildEventSettings(guild_id=guild.guild_id)
        db.session.add(event_settings)
        db.session.commit()
        event_settings = guild.event_settings # Re-fetch
        
    # Fetch server config for event channel settings
    settings = guild.settings # General settings (like event_channel)
    if not settings:
        settings = ServerConfig(guild_id=guild.guild_id)
        db.session.add(settings)
        db.session.commit()
        settings = guild.settings # Re-fetch
        
    # Fetch specific event settings (like bonus XP)
    event_settings = guild.event_settings
    if not event_settings:
        event_settings = GuildEventSettings(guild_id=guild.guild_id)
        db.session.add(event_settings)
        db.session.commit()
        event_settings = guild.event_settings # Re-fetch
    
    return render_template(
        'admin/manage_events.html', 
        title=f'{guild.name} - Manage Events', 
        guild=guild,
        settings=settings, # Pass general settings
        event_settings=event_settings # Pass event-specific settings
        guild=guild,
        settings=settings, # Pass general settings
        event_settings=event_settings # Pass event-specific settings
    ) 