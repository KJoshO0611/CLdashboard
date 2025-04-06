from flask import Blueprint, render_template, abort, flash, redirect, url_for, request
from flask_login import login_required, current_user
from cldashboard import db
from cldashboard.models.user import Guild
from cldashboard.middleware.auth import guild_view_required
import requests
from sqlalchemy import text # Import text for raw SQL

dashboard = Blueprint('dashboard', __name__)

@dashboard.route('/dashboard')
@login_required
def index():
    """User dashboard home"""
    
    # --- Fetch Guilds with Member Counts for the main dashboard page --- 
    guilds_with_counts = []
    user_guilds = current_user.guilds
    
    if user_guilds:
        try:
            # Fetch limited number of guilds for display on main dashboard (e.g., 3 or 5)
            guilds_to_display = sorted(user_guilds, key=lambda g: g.name)[:3] # Limit to 3 for example
            
            for guild in guilds_to_display:
                member_count_result = db.session.execute(
                    text("SELECT COUNT(DISTINCT user_id) FROM levels WHERE guild_id = :guild_id"),
                    {'guild_id': guild.guild_id}
                ).scalar() or 0
                
                guilds_with_counts.append({
                    'guild_object': guild,
                    'member_count': member_count_result
                })
            # No need to sort again if already sliced and sorted
            
        except Exception as e:
            # Don't flash error on main dashboard, just log and maybe show N/A
            print(f"Error in dashboard index fetching counts: {e}")
            # Fallback: Render list without counts if query fails
            guilds_with_counts = [{'guild_object': g, 'member_count': 'N/A'} for g in sorted(user_guilds, key=lambda x: x.name)[:3]]
    # --- End Fetch Guilds --- 

    return render_template('dashboard/index.html', 
                           title='Dashboard', 
                           guild_items=guilds_with_counts # Pass the enhanced list
                           )

@dashboard.route('/dashboard/guilds')
@login_required
def guild_list():
    """List of user's Discord guilds with member counts"""
    
    guilds_with_counts = []
    # current_user.guilds provides the list of Guild objects associated via user_guild table
    user_guilds = current_user.guilds
    
    if user_guilds:
        try:
            for guild in user_guilds:
                # Query the 'levels' table to count members the bot knows about
                member_count_result = db.session.execute(
                    text("SELECT COUNT(DISTINCT user_id) FROM levels WHERE guild_id = :guild_id"),
                    {'guild_id': guild.guild_id} # guild_id is already String
                ).scalar() or 0
                
                guilds_with_counts.append({
                    'guild_object': guild,
                    'member_count': member_count_result
                })
            # Sort guilds alphabetically by name (optional)
            guilds_with_counts.sort(key=lambda x: x['guild_object'].name)
            
        except Exception as e:
            flash("Error fetching member counts for servers.", "danger")
            print(f"Error in guild_list fetching counts: {e}")
            # Fallback: Render list without counts if query fails
            guilds_with_counts = [{'guild_object': g, 'member_count': 'N/A'} for g in sorted(user_guilds, key=lambda x: x.name)]

    return render_template('dashboard/guild_list.html', 
                           title='My Servers', 
                           guild_items=guilds_with_counts # Pass the enhanced list
                           )

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