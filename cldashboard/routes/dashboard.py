from flask import Blueprint, render_template, abort, flash, redirect, url_for, request
from flask_login import login_required, current_user
from cldashboard import db
from cldashboard.models.user import Guild
from cldashboard.middleware.auth import guild_view_required
import requests

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

@dashboard.route('/guilds/<guild_id>/leaderboard')
@login_required
def guild_leaderboard(guild_id):
    """Display the leaderboard for a specific guild"""
    if not current_user.can_view_guild(guild_id):
        flash('You do not have permission to view this guild.', 'error')
        return redirect(url_for('dashboard.guild_list'))
    
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    if not guild:
        flash('Guild not found.', 'error')
        return redirect(url_for('dashboard.guild_list'))
    
    # Get leaderboard data from API
    response = requests.get(f"{request.host_url}api/guilds/{guild_id}/leaderboard", 
                            cookies=request.cookies)
    if response.status_code == 200:
        leaderboard_data = response.json()['data']
    else:
        leaderboard_data = []
    
    return render_template('dashboard/guild_leaderboard.html', 
                         guild=guild,
                         leaderboard=leaderboard_data)

@dashboard.route('/guilds/<guild_id>/achievements')
@login_required
def guild_achievements(guild_id):
    """Display achievements for a specific guild"""
    if not current_user.can_view_guild(guild_id):
        flash('You do not have permission to view this guild.', 'error')
        return redirect(url_for('dashboard.guild_list'))
    
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    if not guild:
        flash('Guild not found.', 'error')
        return redirect(url_for('dashboard.guild_list'))
    
    # Get achievements data from API
    response = requests.get(f"{request.host_url}api/guilds/{guild_id}/achievements",
                           cookies=request.cookies)
    if response.status_code == 200:
        achievements_data = response.json()['data']
    else:
        achievements_data = []
    
    return render_template('dashboard/guild_achievements.html', 
                         guild=guild,
                         achievements=achievements_data)

@dashboard.route('/guilds/<guild_id>/events')
@login_required
def guild_events(guild_id):
    """Display events for a specific guild"""
    if not current_user.can_view_guild(guild_id):
        flash('You do not have permission to view this guild.', 'error')
        return redirect(url_for('dashboard.guild_list'))
    
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    if not guild:
        flash('Guild not found.', 'error')
        return redirect(url_for('dashboard.guild_list'))
    
    # Get events data from API
    response = requests.get(f"{request.host_url}api/guilds/{guild_id}/events",
                           cookies=request.cookies)
    if response.status_code == 200:
        events_data = response.json()['data']
    else:
        events_data = []
    
    return render_template('dashboard/guild_events.html', 
                         guild=guild,
                         events=events_data) 