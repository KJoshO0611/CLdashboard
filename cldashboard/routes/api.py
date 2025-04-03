from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user
from cldashboard import db
from cldashboard.models.user import Guild, GuildSettings, GuildMember, User
from cldashboard.middleware.auth import owner_required, admin_required, guild_admin_required
from datetime import datetime, timedelta
import json
import uuid

api = Blueprint('api', __name__)

# API response helpers
def api_success(data=None, message="Success"):
    return jsonify({
        "success": True,
        "message": message,
        "data": data
    })

def api_error(message="Error", code=400):
    return jsonify({
        "success": False,
        "message": message
    }), code

# Guild Stats API
@api.route('/api/guilds/<guild_id>/stats')
@login_required
def get_guild_stats(guild_id):
    """Get statistics for a specific guild"""
    if not current_user.can_view_guild(guild_id):
        return api_error("You do not have permission to view this guild", 403)
    
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    if not guild:
        return api_error("Guild not found", 404)
    
    # Get member count from GuildMember table
    member_count = GuildMember.query.filter_by(guild_id=guild_id).count()
    
    # Get active users (users who have earned XP in the last 24 hours)
    active_users = GuildMember.query.filter_by(guild_id=guild_id).count()  # TODO: Implement actual active user tracking
    
    # Get total XP and levels (placeholder data for now)
    total_xp = 0  # TODO: Implement XP tracking
    total_levels = 0  # TODO: Implement level tracking
    
    return api_success({
        "member_count": member_count,
        "active_users": active_users,
        "total_xp": total_xp,
        "total_levels": total_levels
    })

# Guild Info API
@api.route('/api/guilds/<guild_id>/info')
@login_required
def get_guild_info(guild_id):
    """Get detailed information about a specific guild"""
    if not current_user.can_view_guild(guild_id):
        return api_error("You do not have permission to view this guild", 403)
    
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    if not guild:
        return api_error("Guild not found", 404)
    
    # Get owner information
    owner = User.query.filter_by(discord_id=guild.owner_id).first()
    owner_name = owner.username if owner else "Unknown"
    
    # Get member count
    member_count = GuildMember.query.filter_by(guild_id=guild_id).count()
    
    return api_success({
        "owner": owner_name,
        "created_at": guild.created_at.isoformat() if hasattr(guild, 'created_at') else None,
        "region": "US East",  # TODO: Implement actual region tracking
        "channels": member_count,  # TODO: Implement actual channel count
        "member_count": member_count
    })

# Guild Activity API
@api.route('/api/guilds/<guild_id>/activity')
@login_required
def get_guild_activity(guild_id):
    """Get recent activity for a specific guild"""
    if not current_user.can_view_guild(guild_id):
        return api_error("You do not have permission to view this guild", 403)
    
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    if not guild:
        return api_error("Guild not found", 404)
    
    # TODO: Implement actual activity tracking
    # For now, return placeholder data
    activities = [
        {
            "description": "Server settings updated",
            "time": "2 hours ago",
            "details": "XP settings modified"
        },
        {
            "description": "New achievement added",
            "time": "1 day ago",
            "details": "First Level achievement created"
        },
        {
            "description": "Member joined",
            "time": "2 days ago",
            "details": "Welcome to the server!"
        }
    ]
    
    return api_success(activities)

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
    
    # TODO: Implement actual leaderboard data
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

# Guild Achievements API
@api.route('/api/guilds/<guild_id>/achievements', methods=['GET'])
@login_required
def get_guild_achievements(guild_id):
    """Get achievements for a specific guild"""
    if not current_user.can_view_guild(guild_id):
        return api_error("You do not have permission to view this guild", 403)
    
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    if not guild:
        return api_error("Guild not found", 404)
    
    # Get achievements from the database
    achievements = db.session.execute('''
        SELECT 
            a.id,
            a.name,
            a.description,
            a.requirement_type,
            a.requirement_value,
            a.icon_path,
            COALESCE(ua.progress, 0) as progress,
            ua.completed,
            ua.completed_at
        FROM achievements a
        LEFT JOIN user_achievements ua ON a.id = ua.achievement_id 
            AND ua.guild_id = :guild_id 
            AND ua.user_id = :user_id
        WHERE a.guild_id = :guild_id
        ORDER BY a.created_at DESC
    ''', {
        'guild_id': guild_id,
        'user_id': current_user.discord_id
    }).fetchall()
    
    # Format achievements for the frontend
    formatted_achievements = []
    for achievement in achievements:
        formatted_achievements.append({
            "id": achievement.id,
            "name": achievement.name,
            "description": achievement.description,
            "category": achievement.requirement_type,  # Map requirement_type to category
            "icon": achievement.icon_path or "medal",  # Default icon if none set
            "progress": achievement.progress,
            "requirement": achievement.requirement_value,
            "completed": achievement.completed,
            "completed_at": achievement.completed_at.isoformat() if achievement.completed_at else None
        })
    
    return api_success(formatted_achievements)

@api.route('/api/guilds/<guild_id>/achievements', methods=['POST'])
@login_required
@guild_admin_required
def create_guild_achievement(guild_id):
    """Create a new achievement for a guild"""
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    if not guild:
        return api_error("Guild not found", 404)
    
    data = request.json
    if not data:
        return api_error("No data provided")
    
    # Validate required fields
    required_fields = ['name', 'description', 'requirement_type', 'requirement_value']
    for field in required_fields:
        if field not in data:
            return api_error(f"Missing required field: {field}")
    
    # Insert the new achievement
    try:
        result = db.session.execute('''
            INSERT INTO achievements (
                guild_id, name, description, requirement_type, 
                requirement_value, icon_path
            ) VALUES (
                :guild_id, :name, :description, :requirement_type,
                :requirement_value, :icon_path
            ) RETURNING id
        ''', {
            'guild_id': guild_id,
            'name': data['name'],
            'description': data['description'],
            'requirement_type': data['requirement_type'],
            'requirement_value': data['requirement_value'],
            'icon_path': data.get('icon_path')
        })
        
        achievement_id = result.scalar()
        db.session.commit()
        
        return api_success({
            "id": achievement_id,
            "message": "Achievement created successfully"
        })
    except Exception as e:
        db.session.rollback()
        return api_error(f"Failed to create achievement: {str(e)}")

# Guild Events API
@api.route('/api/guilds/<guild_id>/events', methods=['GET'])
@login_required
def get_guild_events(guild_id):
    """Get events for a specific guild"""
    if not current_user.can_view_guild(guild_id):
        return api_error("You do not have permission to view this guild", 403)
    
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    if not guild:
        return api_error("Guild not found", 404)
    
    # Get events from the database
    events = db.session.execute('''
        SELECT 
            e.event_id,
            e.name,
            e.description,
            e.start_time,
            e.end_time,
            e.event_type,
            e.status,
            e.creator_id,
            e.associated_boost_id,
            COUNT(ea.id) as participant_count,
            EXISTS(
                SELECT 1 FROM event_attendance ea2 
                WHERE ea2.event_id = e.event_id 
                AND ea2.user_id = :user_id
            ) as is_participant
        FROM discord_scheduled_events e
        LEFT JOIN event_attendance ea ON e.event_id = ea.event_id
        WHERE e.guild_id = :guild_id
        GROUP BY e.event_id, e.name, e.description, e.start_time, e.end_time, 
                 e.event_type, e.status, e.creator_id, e.associated_boost_id
        ORDER BY e.start_time DESC
    ''', {
        'guild_id': guild_id,
        'user_id': current_user.discord_id
    }).fetchall()
    
    # Format events for the frontend
    formatted_events = []
    for event in events:
        # Determine status and color
        now = datetime.now().timestamp()
        if event.start_time > now:
            status = "upcoming"
            status_color = "success"
        elif event.end_time and event.end_time < now:
            status = "past"
            status_color = "secondary"
        else:
            status = "ongoing"
            status_color = "primary"
        
        formatted_events.append({
            "id": event.event_id,
            "name": event.name,
            "description": event.description,
            "type": event.event_type,
            "status": status,
            "status_color": status_color,
            "start_time": datetime.fromtimestamp(event.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(event.end_time).isoformat() if event.end_time else None,
            "participants": event.participant_count,
            "is_participant": event.is_participant,
            "creator_id": event.creator_id,
            "boost_id": event.associated_boost_id
        })
    
    return api_success(formatted_events)

@api.route('/api/guilds/<guild_id>/events', methods=['POST'])
@login_required
@guild_admin_required
def create_guild_event(guild_id):
    """Create a new event for a guild"""
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    if not guild:
        return api_error("Guild not found", 404)
    
    data = request.json
    if not data:
        return api_error("No data provided")
    
    # Validate required fields
    required_fields = ['name', 'description', 'start_time', 'end_time', 'event_type']
    for field in required_fields:
        if field not in data:
            return api_error(f"Missing required field: {field}")
    
    try:
        # Convert ISO format times to timestamps
        start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00')).timestamp()
        end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00')).timestamp()
        
        result = db.session.execute('''
            INSERT INTO discord_scheduled_events (
                event_id, guild_id, name, description, start_time,
                end_time, event_type, status, creator_id
            ) VALUES (
                :event_id, :guild_id, :name, :description, :start_time,
                :end_time, :event_type, 'scheduled', :creator_id
            ) RETURNING event_id
        ''', {
            'event_id': str(uuid.uuid4()),  # Generate a unique event ID
            'guild_id': guild_id,
            'name': data['name'],
            'description': data['description'],
            'start_time': start_time,
            'end_time': end_time,
            'event_type': data['event_type'],
            'creator_id': current_user.discord_id
        })
        
        event_id = result.scalar()
        db.session.commit()
        
        return api_success({
            "id": event_id,
            "message": "Event created successfully"
        })
    except Exception as e:
        db.session.rollback()
        return api_error(f"Failed to create event: {str(e)}")

@api.route('/api/guilds/<guild_id>/events/<event_id>/join', methods=['POST'])
@login_required
def join_guild_event(guild_id, event_id):
    """Join an event"""
    if not current_user.can_view_guild(guild_id):
        return api_error("You do not have permission to join this event", 403)
    
    try:
        # Check if event exists and is still open
        event = db.session.execute('''
            SELECT start_time, end_time, status
            FROM discord_scheduled_events
            WHERE event_id = :event_id AND guild_id = :guild_id
        ''', {
            'event_id': event_id,
            'guild_id': guild_id
        }).fetchone()
        
        if not event:
            return api_error("Event not found", 404)
        
        now = datetime.now().timestamp()
        if event.start_time > now:
            return api_error("Event hasn't started yet")
        if event.end_time and event.end_time < now:
            return api_error("Event has ended")
        if event.status != 'scheduled':
            return api_error("Event is not open for joining")
        
        # Add user to event attendance
        db.session.execute('''
            INSERT INTO event_attendance (event_id, user_id, guild_id, status)
            VALUES (:event_id, :user_id, :guild_id, 'going')
            ON CONFLICT (event_id, user_id) DO UPDATE
            SET status = 'going', joined_at = CURRENT_TIMESTAMP
        ''', {
            'event_id': event_id,
            'user_id': current_user.discord_id,
            'guild_id': guild_id
        })
        
        db.session.commit()
        return api_success(message="Successfully joined event")
    except Exception as e:
        db.session.rollback()
        return api_error(f"Failed to join event: {str(e)}") 