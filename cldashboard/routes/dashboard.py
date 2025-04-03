from flask import Blueprint, render_template, abort, flash, redirect, url_for, request
from flask_login import login_required, current_user
from cldashboard import db
from cldashboard.models.user import Guild
from cldashboard.middleware.auth import guild_view_required

dashboard = Blueprint('dashboard', __name__)

@dashboard.route('/dashboard')
@login_required
def index():
    """User dashboard home"""
    return render_template('dashboard/index.html', title='Dashboard')

@dashboard.route('/dashboard/guilds')
@login_required
def guild_list():
    """List of user's Discord guilds"""
    return render_template('dashboard/guild_list.html', title='My Servers')

@dashboard.route('/dashboard/guilds/<guild_id>')
@login_required
@guild_view_required
def guild_overview(guild_id):
    """Overview of a specific guild"""
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    
    if not guild:
        abort(404)
    
    return render_template('dashboard/guild_overview.html', title=f'{guild.name}', guild=guild)

@dashboard.route('/dashboard/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('dashboard/profile.html', title='My Profile')

@dashboard.route('/dashboard/guilds/<guild_id>/leaderboard')
@login_required
@guild_view_required
def guild_leaderboard(guild_id):
    """Leaderboard for a specific guild"""
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    
    if not guild:
        abort(404)
    
    # In a real implementation, you would fetch leaderboard data from the database
    # This is a placeholder
    leaderboard_data = []
    
    return render_template(
        'dashboard/guild_leaderboard.html', 
        title=f'{guild.name} - Leaderboard', 
        guild=guild,
        leaderboard=leaderboard_data
    )

@dashboard.route('/dashboard/guilds/<guild_id>/achievements')
@login_required
@guild_view_required
def guild_achievements(guild_id):
    """Achievements for a specific guild"""
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    
    if not guild:
        abort(404)
    
    # In a real implementation, you would fetch achievement data from the database
    # This is a placeholder
    achievements_data = []
    
    return render_template(
        'dashboard/guild_achievements.html', 
        title=f'{guild.name} - Achievements', 
        guild=guild,
        achievements=achievements_data
    )

@dashboard.route('/dashboard/guilds/<guild_id>/events')
@login_required
@guild_view_required
def guild_events(guild_id):
    """Events for a specific guild"""
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    
    if not guild:
        abort(404)
    
    # In a real implementation, you would fetch event data from the database
    # This is a placeholder
    events_data = []
    
    return render_template(
        'dashboard/guild_events.html', 
        title=f'{guild.name} - Events', 
        guild=guild,
        events=events_data
    ) 