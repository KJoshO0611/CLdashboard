from flask import Blueprint, render_template, flash, redirect, url_for, request, abort
from flask_login import login_required
from cldashboard import db
from cldashboard.models.user import Guild, GuildSettings
from cldashboard.middleware.auth import owner_required, admin_required, guild_admin_required

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
        settings = GuildSettings(guild_id=guild.id)
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
    
    return render_template(
        'admin/guild_xp_settings.html', 
        title=f'{guild.name} - XP Settings', 
        guild=guild
    )

@admin.route('/dashboard/guilds/<guild_id>/roles')
@login_required
@guild_admin_required
def guild_roles(guild_id):
    """Role rewards settings for a specific guild"""
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    
    if not guild:
        abort(404)
    
    return render_template(
        'admin/guild_roles.html', 
        title=f'{guild.name} - Role Rewards', 
        guild=guild
    )

@admin.route('/dashboard/guilds/<guild_id>/achievements/manage')
@login_required
@guild_admin_required
def manage_achievements(guild_id):
    """Achievement management for a specific guild"""
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    
    if not guild:
        abort(404)
    
    return render_template(
        'admin/manage_achievements.html', 
        title=f'{guild.name} - Manage Achievements', 
        guild=guild
    )

@admin.route('/dashboard/guilds/<guild_id>/events/manage')
@login_required
@guild_admin_required
def manage_events(guild_id):
    """Event management for a specific guild"""
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    
    if not guild:
        abort(404)
    
    return render_template(
        'admin/manage_events.html', 
        title=f'{guild.name} - Manage Events', 
        guild=guild
    ) 