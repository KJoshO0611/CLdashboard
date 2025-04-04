from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user
from cldashboard import db
from cldashboard.models.user import Guild, ServerConfig, ServerXpSettings, GuildMember, User
from cldashboard.middleware.auth import owner_required, admin_required, guild_admin_required
from datetime import datetime, timedelta
import json
import uuid
from sqlalchemy import text

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

# Utility function to ensure ID type consistency
def ensure_string_id(id_value):
    """Convert any ID to string format to ensure consistency across the application"""
    return str(id_value) if id_value is not None else None

# Utility function to ensure integer ID type for database operations
def ensure_int_id(id_value):
    """Convert any ID to integer format for database operations"""
    if id_value is None:
        return None
    return int(id_value) if isinstance(id_value, str) else id_value

# Guild Stats API
@api.route('/api/guilds/<guild_id>/stats')
@login_required
def get_guild_stats(guild_id):
    """Get statistics for a specific guild"""
    # Get string ID for permission checks and integer ID for database queries
    guild_id_str = ensure_string_id(guild_id)
    guild_id_int = ensure_int_id(guild_id)
    
    if not current_user.can_view_guild(guild_id_str):
        return api_error("You do not have permission to view this guild", 403)
    
    guild = Guild.query.filter_by(guild_id=guild_id_int).first()
    if not guild:
        return api_error("Guild not found", 404)
    
    # Get member count from GuildMember table
    member_count = GuildMember.query.filter_by(guild_id=guild_id_int).count()
    
    # Get active users (users who have earned XP in the last 24 hours)
    one_day_ago = (datetime.now() - timedelta(days=1)).timestamp()
    active_users = db.session.execute(
        text('SELECT COUNT(DISTINCT user_id) FROM guild_members WHERE guild_id = :guild_id AND last_xp_gain >= :time_limit'),
        {'guild_id': str(guild_id_int), 'time_limit': one_day_ago}
    ).scalar() or 0
    
    # Get total XP for the guild
    total_xp_result = db.session.execute(
        text('SELECT SUM(xp) FROM guild_members WHERE guild_id = :guild_id'),
        {'guild_id': str(guild_id_int)}
    ).scalar() or 0
    total_xp = int(total_xp_result)
    
    # Get sum of all levels (for levels earned metric)
    total_levels_result = db.session.execute(
        text('SELECT SUM(level) FROM guild_members WHERE guild_id = :guild_id'),
        {'guild_id': str(guild_id_int)}
    ).scalar() or 0
    total_levels = int(total_levels_result)
    
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
    # Convert to appropriate ID types for different operations
    guild_id_str = ensure_string_id(guild_id)
    guild_id_int = ensure_int_id(guild_id)
    
    if not current_user.can_view_guild(guild_id_str):
        return api_error("You do not have permission to view this guild", 403)
    
    guild = Guild.query.filter_by(guild_id=guild_id_int).first()
    if not guild:
        return api_error("Guild not found", 404)
    
    # Get owner information
    owner = User.query.filter_by(discord_id=guild.owner_id).first()
    owner_name = owner.username if owner else "Unknown"
    
    # Get member count
    member_count = GuildMember.query.filter_by(guild_id=guild_id_int).count()
    
    # Get channel count (using discord API integration or a channels table if available)
    # For now, estimate based on a channels table or fallback to default
    try:
        channel_count = db.session.execute(
            text('SELECT COUNT(*) FROM channels WHERE guild_id = :guild_id'),
            {'guild_id': str(guild_id_int)}
        ).scalar() or 0
    except:
        # If channels table doesn't exist, estimate based on guild size
        channel_count = min(10 + (member_count // 20), 50)  # Rough estimate
    
    # Get region information if available, otherwise default
    region = "Unknown"
    if hasattr(guild, 'region') and guild.region:
        region = guild.region
    else:
        # Default based on common Discord regions
        region = "US East"
    
    # Format creation date
    created_at = None
    if hasattr(guild, 'created_at') and guild.created_at:
        if isinstance(guild.created_at, datetime):
            created_at = guild.created_at.isoformat()
        else:
            created_at = guild.created_at
    
    return api_success({
        "owner": owner_name,
        "created_at": created_at,
        "region": region,
        "channels": channel_count,
        "member_count": member_count
    })

# Guild Activity API
@api.route('/api/guilds/<guild_id>/activity')
@login_required
def get_guild_activity(guild_id):
    """Get recent activity for a specific guild"""
    # Convert to appropriate ID types for different operations
    guild_id_str = ensure_string_id(guild_id)
    guild_id_int = ensure_int_id(guild_id)
    user_id_int = ensure_int_id(current_user.discord_id)
    
    if not current_user.can_view_guild(guild_id_str):
        return api_error("You do not have permission to view this guild", 403)
    
    guild = Guild.query.filter_by(guild_id=guild_id_int).first()
    if not guild:
        return api_error("Guild not found", 404)
    
    # Get recent XP gains
    try:
        recent_xp = db.session.execute(
            text('''
            SELECT 
                u.username, 
                gm.xp - gm.previous_xp as xp_gained,
                gm.last_xp_gain
            FROM guild_members gm
            JOIN users u ON gm.user_id = u.discord_id
            WHERE gm.guild_id = CAST(:guild_id AS BIGINT) 
            AND gm.last_xp_gain IS NOT NULL
            ORDER BY gm.last_xp_gain DESC
            LIMIT 5
            '''), 
            {'guild_id': guild_id_int}
        ).fetchall()
    except Exception as e:
        print(f"Error fetching recent XP: {e}")
        recent_xp = []
    
    # Get recent achievements
    try:
        recent_achievements = db.session.execute(
            text('''
            SELECT 
                u.username,
                a.name as achievement_name,
                ua.completed_at
            FROM user_achievements ua
            JOIN users u ON ua.user_id = u.discord_id
            JOIN achievements a ON ua.achievement_id = a.id
            WHERE ua.guild_id = CAST(:guild_id AS BIGINT) 
            AND ua.completed = TRUE
            AND ua.completed_at IS NOT NULL
            ORDER BY ua.completed_at DESC
            LIMIT 5
            '''),
            {'guild_id': guild_id_int}
        ).fetchall()
    except Exception as e:
        print(f"Error fetching recent achievements: {e}")
        recent_achievements = []
    
    # Format activities
    activities = []
    
    # Add recent XP gains
    for xp in recent_xp:
        if hasattr(xp, 'last_xp_gain') and xp.last_xp_gain:
            time_ago = format_time_ago((datetime.now() - datetime.fromtimestamp(xp.last_xp_gain)).total_seconds())
            activities.append({
                "description": f"{xp.username} gained XP",
                "time": time_ago,
                "details": f"+{xp.xp_gained} XP"
            })
    
    # Add recent achievements
    for achievement in recent_achievements:
        if hasattr(achievement, 'completed_at') and achievement.completed_at:
            time_ago = format_time_ago((datetime.now() - achievement.completed_at).total_seconds())
            activities.append({
                "description": f"{achievement.username} earned achievement",
                "time": time_ago,
                "details": achievement.achievement_name
            })
    
    # Sort all activities by recency (approximated by the time_ago string)
    activities = sorted(activities, key=lambda x: parse_time_ago(x["time"]))[:5]
    
    # If we don't have enough activity, add some default items
    if len(activities) == 0:
        return api_success([{
            "description": "No recent activity",
            "time": "just now",
            "details": "Actions will appear here as members earn XP and achievements"
        }])
    
    return api_success(activities)

# Helper functions for time formatting
def format_time_ago(seconds):
    """Format a time difference in seconds to a human-readable string"""
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"

def parse_time_ago(time_str):
    """Convert a time_ago string back to approximate seconds for sorting"""
    if time_str == "just now":
        return 0
    parts = time_str.split()
    if len(parts) < 3:
        return 99999999  # Default high value for unknown format
    
    value = int(parts[0])
    unit = parts[1]
    
    if unit.startswith("minute"):
        return value * 60
    elif unit.startswith("hour"):
        return value * 3600
    elif unit.startswith("day"):
        return value * 86400
    else:
        return 99999999  # Default high value for unknown unit

# Guild Settings API
@api.route('/api/guilds/<guild_id>/settings', methods=['GET'])
@login_required
@guild_admin_required
def get_guild_settings(guild_id):
    """Get settings for a specific guild"""
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    
    if not guild:
        return api_error("Guild not found", 404)
    
    # Get or create server config settings
    settings = guild.settings
    if not settings:
        settings = ServerConfig(guild_id=guild.guild_id)
        db.session.add(settings)
        db.session.commit()
    
    # Get or create XP settings
    xp_settings = guild.xp_settings
    if not xp_settings:
        xp_settings = ServerXpSettings(guild_id=guild.guild_id)
        db.session.add(xp_settings)
        db.session.commit()
    
    return api_success({
        "min_xp": xp_settings.min_xp,
        "max_xp": xp_settings.max_xp,
        "xp_cooldown": xp_settings.cooldown,
        "level_up_channel_id": settings.level_up_channel,
        "event_announcement_channel_id": settings.event_channel,
        "achievement_channel_id": settings.achievement_channel
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
    
    # Get or create general settings
    settings = guild.settings
    if not settings:
        settings = ServerConfig(guild_id=guild.guild_id)
        db.session.add(settings)
    
    # Get or create XP settings
    xp_settings = guild.xp_settings
    if not xp_settings:
        xp_settings = ServerXpSettings(guild_id=guild.guild_id)
        db.session.add(xp_settings)
    
    # Update settings with provided values
    if 'min_xp' in data:
        xp_settings.min_xp = int(data['min_xp'])
    if 'max_xp' in data:
        xp_settings.max_xp = int(data['max_xp'])
    if 'xp_cooldown' in data:
        xp_settings.cooldown = int(data['xp_cooldown'])
    if 'level_up_channel_id' in data:
        settings.level_up_channel = data['level_up_channel_id']
    if 'event_announcement_channel_id' in data:
        settings.event_channel = data['event_announcement_channel_id']
    if 'achievement_channel_id' in data:
        settings.achievement_channel = data['achievement_channel_id']
    
    db.session.commit()
    
    return api_success(message="Settings updated successfully")

# Leaderboard API
@api.route('/api/guilds/<guild_id>/leaderboard', methods=['GET'])
@login_required
def get_guild_leaderboard(guild_id):
    """Get leaderboard for a specific guild"""
    # Convert to appropriate ID types for different operations
    guild_id_str = ensure_string_id(guild_id)
    guild_id_int = ensure_int_id(guild_id)
    
    if not current_user.can_view_guild(guild_id_str) and not current_user.is_owner:
        return api_error("You do not have permission to view this guild", 403)
    
    guild = Guild.query.filter_by(guild_id=guild_id_int).first()
    
    if not guild:
        return api_error("Guild not found", 404)
    
    # Get actual leaderboard data from database
    # Get the time period filter if specified (default to all time)
    period = request.args.get('period', 'all')
    
    # Build the query to get leaderboard data with proper ranking
    try:
        # Base query targeting the 'levels' table
        # Assuming levels.xp represents the total XP for ranking.
        # Adjust if levels.xp is only XP towards the next level.
        query_text = '''
            SELECT 
                l.user_id as discord_id_str, -- Keep as string from levels table
                u.discord_id, -- Get the BigInt ID from users table
                u.username,
                u.avatar,
                l.level,
                l.xp,
                ROW_NUMBER() OVER (ORDER BY l.level DESC, l.xp DESC) as rank -- Rank primarily by level, then XP
            FROM levels l
            JOIN users u ON l.user_id = CAST(u.discord_id AS TEXT) -- Join on TEXT representation
            WHERE l.guild_id = :guild_id -- Assuming guild_id in levels is TEXT
        '''
        
        # Add time period filter if needed
        # Note: levels.last_xp_time is DOUBLE PRECISION (epoch seconds)
        params = {'guild_id': guild_id_str} # Use string guild_id for levels table
        now_epoch = datetime.now().timestamp()
        if period == 'week':
            query_text += ' AND l.last_xp_time >= :start_epoch'
            params['start_epoch'] = now_epoch - (7 * 24 * 60 * 60) # 7 days in seconds
        elif period == 'month':
            query_text += ' AND l.last_xp_time >= :start_epoch'
            params['start_epoch'] = now_epoch - (30 * 24 * 60 * 60) # 30 days in seconds
        
        # Add ordering and limit
        query_text += '''
            ORDER BY rank ASC -- Use the calculated rank
            LIMIT 100
        '''
        
        # Execute the query
        leaderboard_data = db.session.execute(text(query_text), params).fetchall()
        
        # Format the leaderboard data
        formatted_leaderboard = []
        for entry in leaderboard_data:
            formatted_leaderboard.append({
                'rank': entry.rank,
                # Use the BigInt discord_id from the users table for consistency elsewhere
                'discord_id': entry.discord_id, 
                'username': entry.username,
                'avatar': entry.avatar,
                'level': entry.level,
                'xp': entry.xp
            })
        
        return api_success(formatted_leaderboard)
    except Exception as e:
        # Log the error
        print(f"Error fetching leaderboard: {e}")
        return api_error(f"Failed to fetch leaderboard data: {str(e)}")

# User Stats API
@api.route('/api/users/me/stats', methods=['GET'])
@login_required
def get_user_stats():
    """Get stats for the current user"""
    try:
        # Ensure user ID is an integer for database operations
        user_id = ensure_int_id(current_user.discord_id)
        
        # Get total XP across all guilds
        total_xp = db.session.execute(
            text('SELECT SUM(xp) FROM guild_members WHERE user_id = :user_id'),
            {'user_id': str(user_id)}
        ).scalar() or 0
        
        # Count total achievements
        try:
            # Try with direct query using string ID
            total_achievements_result = db.session.execute(
                text('SELECT COUNT(*) FROM user_achievements WHERE user_id = :user_id AND completed = TRUE'),
                {'user_id': str(user_id)}
            ).scalar() or 0
        except Exception as achievement_error:
            print(f"Error fetching achievements with string ID: {achievement_error}")
            # Fallback to 0 if query fails
            total_achievements_result = 0
            
        total_achievements = int(total_achievements_result)
        
        # Get total guilds (from relationship)
        try:
            total_guilds = len(current_user.guilds)
        except Exception as guild_error:
            print(f"Error fetching guilds: {guild_error}")
            # Query directly if relationship fails
            total_guilds = db.session.execute(
                text('SELECT COUNT(*) FROM user_guild WHERE user_id = :user_id'),
                {'user_id': str(user_id)}
            ).scalar() or 0
        
        # Get average level across guilds
        avg_level_result = db.session.execute(
            text('SELECT COALESCE(AVG(level), 0) FROM guild_members WHERE user_id = :user_id'),
            {'user_id': str(user_id)}
        ).scalar() or 0
        avg_level = round(float(avg_level_result), 1)
        
        return api_success({
            "username": current_user.username,
            "total_xp": total_xp,
            "total_guilds": total_guilds,
            "achievements": total_achievements,
            "average_level": avg_level
        })
    except Exception as e:
        print(f"Error fetching user stats: {e}")
        # Fallback to basic information if database query fails
        return api_success({
        "username": current_user.username,
            "total_xp": 0,
            "total_guilds": 0,  # Avoid relationship access in error state
            "achievements": 0,
            "average_level": 0
        })

# Admin APIs
@api.route('/api/admin/stats', methods=['GET'])
@login_required
@owner_required
def get_admin_stats():
    """Get admin stats (bot owner only)"""
    try:
        # Get total users count
        total_users = db.session.execute(
            text('SELECT COUNT(*) FROM users')
        ).scalar() or 0
        
        # Get total guilds count
        total_guilds = db.session.execute(
            text('SELECT COUNT(*) FROM guilds')
        ).scalar() or 0
        
        # Get total XP across all guilds
        total_xp = db.session.execute(
            text('SELECT SUM(xp) FROM guild_members')
        ).scalar() or 0
        
        # Get total achievements completed
        total_achievements = db.session.execute(
            text('SELECT COUNT(*) FROM user_achievements WHERE completed = TRUE')
        ).scalar() or 0
        
        # Calculate the application uptime (or use a placeholder)
        # In a real implementation, you might store the bot start time in a database or a file
        uptime_days = 30  # Placeholder
        
        return api_success({
            "total_users": int(total_users),
            "total_guilds": int(total_guilds),
            "total_xp_earned": int(total_xp),
            "total_achievements": int(total_achievements),
            "uptime_days": uptime_days
        })
    except Exception as e:
        print(f"Error fetching admin stats: {e}")
        return api_error(f"Failed to fetch admin stats: {str(e)}")

# Guild Achievements API
@api.route('/api/guilds/<guild_id>/achievements', methods=['GET'])
@login_required
def get_guild_achievements(guild_id):
    """Get achievements for a specific guild"""
    if not current_user.can_view_guild(guild_id):
        return api_error("You do not have permission to view this guild", 403)
    
    # Convert IDs to integers for database operations
    guild_id_int = ensure_int_id(guild_id)
    user_id_int = ensure_int_id(current_user.discord_id)
    
    guild = Guild.query.filter_by(guild_id=guild_id_int).first()
    if not guild:
        return api_error("Guild not found", 404)
    
    # Get total member count for the guild
    member_count = GuildMember.query.filter_by(guild_id=guild_id_int).count()
    
    # Get achievements from the database
    achievements = db.session.execute(text('''
        SELECT 
            a.id,
            a.name,
            a.description,
            a.requirement_type,
            a.requirement_value,
            a.icon_path,
            COALESCE(ua.progress, 0) as progress,
            ua.completed,
            ua.completed_at,
            (SELECT COUNT(*) FROM user_achievements ua2 
             WHERE ua2.achievement_id = a.id 
             AND ua2.guild_id = :guild_id
             AND ua2.completed = TRUE) as members_completed
        FROM achievements a
        LEFT JOIN user_achievements ua ON a.id = ua.achievement_id 
            AND ua.guild_id = :guild_id
            AND ua.user_id = :user_id
        WHERE a.guild_id = :guild_id
        ORDER BY a.created_at DESC
    '''), {
        'guild_id': str(guild_id_int),
        'user_id': str(user_id_int)
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
            "completed_at": achievement.completed_at.isoformat() if achievement.completed_at else None,
            "members_completed": achievement.members_completed or 0,
            "member_count": member_count
        })
    
    return api_success(formatted_achievements)

@api.route('/api/guilds/<guild_id>/achievements', methods=['POST'])
@login_required
@guild_admin_required
def create_guild_achievement(guild_id):
    """Create a new achievement for a guild"""
    # Convert to integer ID for database operations
    guild_id_int = ensure_int_id(guild_id)
    
    guild = Guild.query.filter_by(guild_id=guild_id_int).first()
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
        result = db.session.execute(text('''
            INSERT INTO achievements (
                guild_id, name, description, requirement_type, 
                requirement_value, icon_path
            ) VALUES (
                :guild_id, :name, :description, :requirement_type,
                :requirement_value, :icon_path
            ) RETURNING id
        '''), {
            'guild_id': guild_id_int,
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
    # Convert to appropriate ID types for different operations
    guild_id_str = ensure_string_id(guild_id)
    guild_id_int = ensure_int_id(guild_id)
    user_id_int = ensure_int_id(current_user.discord_id)
    
    if not current_user.can_view_guild(guild_id_str):
        return api_error("You do not have permission to view this guild", 403)
    
    guild = Guild.query.filter_by(guild_id=guild_id_int).first()
    if not guild:
        return api_error("Guild not found", 404)
    
    # Get events from the database
    events = db.session.execute(text('''
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
    '''), {
        'guild_id': str(guild_id_int),
        'user_id': str(user_id_int)
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
        
        result = db.session.execute(text('''
            INSERT INTO discord_scheduled_events (
                event_id, guild_id, name, description, start_time,
                end_time, event_type, status, creator_id
            ) VALUES (
                :event_id, :guild_id, :name, :description, :start_time,
                :end_time, :event_type, 'scheduled', :creator_id
            ) RETURNING event_id
        '''), {
            'event_id': str(uuid.uuid4()),  # Generate a unique event ID
            'guild_id': str(guild_id),
            'name': data['name'],
            'description': data['description'],
            'start_time': start_time,
            'end_time': end_time,
            'event_type': data['event_type'],
            'creator_id': str(current_user.discord_id)
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
        event = db.session.execute(text('''
            SELECT start_time, end_time, status
            FROM discord_scheduled_events
            WHERE event_id = :event_id AND guild_id = :guild_id
        '''), {
            'event_id': event_id,
            'guild_id': str(ensure_int_id(guild_id))
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
        db.session.execute(text('''
            INSERT INTO event_attendance (event_id, user_id, guild_id, status)
            VALUES (:event_id, :user_id, :guild_id, 'going')
            ON CONFLICT (event_id, user_id) DO UPDATE
            SET status = 'going', joined_at = CURRENT_TIMESTAMP
        '''), {
            'event_id': event_id,
            'user_id': str(ensure_int_id(current_user.discord_id)),
            'guild_id': str(ensure_int_id(guild_id))
        })
        
        db.session.commit()
        return api_success(message="Successfully joined event")
    except Exception as e:
        db.session.rollback()
        return api_error(f"Failed to join event: {str(e)}")

# Activity Chart API
@api.route('/api/guilds/<guild_id>/activity-chart')
@login_required
def get_guild_activity_chart(guild_id):
    """Get activity chart data for a specific guild"""
    # Convert to appropriate ID types for different operations
    guild_id_str = ensure_string_id(guild_id)
    guild_id_int = ensure_int_id(guild_id)
    
    if not current_user.can_view_guild(guild_id_str):
        return api_error("You do not have permission to view this guild", 403)
    
    guild = Guild.query.filter_by(guild_id=guild_id_int).first()
    if not guild:
        return api_error("Guild not found", 404)
    
    # Get activity data for the past 7 days
    days = 7
    today = datetime.now().date()
    labels = []
    data = []
    
    try:
        for i in range(days - 1, -1, -1):
            date = today - timedelta(days=i)
            day_start = datetime.combine(date, datetime.min.time()).timestamp()
            day_end = datetime.combine(date, datetime.max.time()).timestamp()
            
            # Count messages or activity for this day
            count = db.session.execute(
                text('''
                SELECT COUNT(*) 
                FROM guild_members 
                WHERE guild_id = :guild_id
                AND last_xp_gain >= :day_start 
                AND last_xp_gain <= :day_end
                '''),
                {
                    'guild_id': str(guild_id_int),
                    'day_start': day_start,
                    'day_end': day_end
                }
            ).scalar() or 0
            
            # Format the date label
            label = date.strftime('%a')  # Short day name (Mon, Tue, etc.)
            
            labels.append(label)
            data.append(count)
    except Exception as e:
        print(f"Error fetching activity chart data: {e}")
        # Return default data in case of error
        return api_success({
            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "data": [0, 0, 0, 0, 0, 0, 0]
        })
    
    return api_success({
        "labels": labels,
        "data": data
    })

# Function to assist with database BIGINT to string conversions
def query_with_string_ids(query_text, params):
    """Execute SQL query with string ID parameters, ensuring proper type conversion"""
    # Cast string IDs to match BIGINT in database if needed
    updated_params = params.copy()
    
    # Prepare parameters for execution - convert string IDs to integers
    if 'guild_id' in updated_params and updated_params['guild_id'] is not None:
        if isinstance(updated_params['guild_id'], str):
            updated_params['guild_id'] = int(updated_params['guild_id'])
        
    if 'user_id' in updated_params and updated_params['user_id'] is not None:
        if isinstance(updated_params['user_id'], str):
            updated_params['user_id'] = int(updated_params['user_id'])
    
    return db.session.execute(text(query_text), updated_params) 