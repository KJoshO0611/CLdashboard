from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user
from cldashboard import db
from cldashboard.models.user import Guild, GuildSettings
from cldashboard.middleware.auth import owner_required, admin_required, guild_admin_required
import json

api = Blueprint('api', __name__)

# API response helpers
def api_success(data=None, message="Success"):
    return jsonify({
        "success": True,
        "message": message,
        "data": data
    })

def api_error(message="An error occurred", status_code=400):
    response = jsonify({
        "success": False,
        "message": message
    })
    response.status_code = status_code
    return response

# Guild Settings API
@api.route('/api/guilds/<guild_id>/settings', methods=['GET'])
@login_required
@guild_admin_required
def get_guild_settings(guild_id):
    """Get settings for a specific guild"""
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    
    if not guild:
        return api_error("Guild not found", 404)
    
    settings = guild.settings
    if not settings:
        settings = GuildSettings(guild_id=guild.id)
        db.session.add(settings)
        db.session.commit()
    
    return api_success({
        "min_xp": settings.min_xp,
        "max_xp": settings.max_xp,
        "xp_cooldown": settings.xp_cooldown,
        "level_up_channel_id": settings.level_up_channel_id,
        "event_announcement_channel_id": settings.event_announcement_channel_id
    })

@api.route('/api/guilds/<guild_id>/settings', methods=['POST'])
@login_required
@guild_admin_required
def update_guild_settings(guild_id):
    """Update settings for a specific guild"""
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    
    if not guild:
        return api_error("Guild not found", 404)
    
    data = request.json
    if not data:
        return api_error("No data provided")
    
    settings = guild.settings
    if not settings:
        settings = GuildSettings(guild_id=guild.id)
        db.session.add(settings)
    
    # Update settings with provided values
    if 'min_xp' in data:
        settings.min_xp = int(data['min_xp'])
    if 'max_xp' in data:
        settings.max_xp = int(data['max_xp'])
    if 'xp_cooldown' in data:
        settings.xp_cooldown = int(data['xp_cooldown'])
    if 'level_up_channel_id' in data:
        settings.level_up_channel_id = data['level_up_channel_id']
    if 'event_announcement_channel_id' in data:
        settings.event_announcement_channel_id = data['event_announcement_channel_id']
    
    db.session.commit()
    
    return api_success(message="Settings updated successfully")

# Leaderboard API
@api.route('/api/guilds/<guild_id>/leaderboard', methods=['GET'])
@login_required
def get_guild_leaderboard(guild_id):
    """Get leaderboard for a specific guild"""
    if not current_user.can_view_guild(guild_id) and not current_user.is_owner:
        return api_error("You do not have permission to view this guild", 403)
    
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    
    if not guild:
        return api_error("Guild not found", 404)
    
    # In a real implementation, you would fetch leaderboard data from the database
    # This is a placeholder returning mock data
    mock_leaderboard = [
        {"rank": 1, "username": "User1", "level": 30, "xp": 9000},
        {"rank": 2, "username": "User2", "level": 25, "xp": 7500},
        {"rank": 3, "username": "User3", "level": 20, "xp": 6000}
    ]
    
    return api_success(mock_leaderboard)

# User Stats API
@api.route('/api/users/me/stats', methods=['GET'])
@login_required
def get_user_stats():
    """Get stats for the current user"""
    # In a real implementation, you would fetch user stats from the database
    # This is a placeholder returning mock data
    mock_stats = {
        "username": current_user.username,
        "total_xp": 12345,
        "total_guilds": len(current_user.guilds),
        "achievements": 42
    }
    
    return api_success(mock_stats)

# Admin APIs
@api.route('/api/admin/stats', methods=['GET'])
@login_required
@owner_required
def get_admin_stats():
    """Get admin stats (bot owner only)"""
    # In a real implementation, you would fetch admin stats from the database
    # This is a placeholder returning mock data
    mock_admin_stats = {
        "total_users": 1000,
        "total_guilds": 50,
        "total_messages_processed": 1000000,
        "uptime_days": 30
    }
    
    return api_success(mock_admin_stats) 