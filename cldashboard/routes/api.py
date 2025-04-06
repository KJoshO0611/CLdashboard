from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user
from cldashboard import db
from cldashboard.models.user import Guild, ServerConfig, ServerXpSettings, GuildMember, User
from cldashboard.middleware.auth import owner_required, admin_required, guild_admin_required
from cldashboard.utils.xp_utils import calculate_cumulative_xp, total_xp_for_level
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

# Guild Stats API
@api.route('/api/guilds/<string:guild_id>/stats')
@login_required
def get_guild_stats(guild_id):
    """Get statistics for a specific guild using the levels table"""
    if not current_user.can_view_guild(guild_id):
        return api_error("You do not have permission to view this guild", 403)
    
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    if not guild:
        return api_error("Guild not found or bot is not in this guild", 404)

    try:
        member_count = db.session.execute(
            text("SELECT COUNT(DISTINCT user_id) FROM levels WHERE guild_id = :guild_id"),
            {'guild_id': guild_id}
        ).scalar() or 0
        
        one_day_ago_ts = (datetime.now() - timedelta(days=1)).timestamp()
        active_users = db.session.execute(
            text("""SELECT COUNT(DISTINCT user_id) FROM levels 
                    WHERE guild_id = :guild_id AND last_xp_time >= :time_limit"""
                 ),
            {'guild_id': guild_id, 'time_limit': one_day_ago_ts}
        ).scalar() or 0
        
        xp_levels_data = db.session.execute(
            text("SELECT level, xp FROM levels WHERE guild_id = :guild_id"),
            {'guild_id': guild_id}
        ).fetchall()
        
        total_cumulative_xp = sum(calculate_cumulative_xp(row.level, row.xp) for row in xp_levels_data)
        
        total_levels_earned = db.session.execute(
            text("SELECT SUM(level) FROM levels WHERE guild_id = :guild_id"),
            {'guild_id': guild_id}
        ).scalar() or 0
        
        return api_success({
            "member_count": member_count,
            "active_users": active_users,
            "total_xp": int(total_cumulative_xp),
            "total_levels": int(total_levels_earned)
        })
    except Exception as e:
        print(f"Error fetching guild stats for {guild_id}: {e}")
        return api_error("Failed to fetch guild statistics.")

# Guild Info API
@api.route('/api/guilds/<string:guild_id>/info')
@login_required
def get_guild_info(guild_id):
    """Get detailed information about a specific guild"""
    if not current_user.can_view_guild(guild_id):
        return api_error("You do not have permission to view this guild", 403)
    
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    if not guild:
        return api_error("Guild not found", 404)
    
    owner_name = "Unknown"
    if guild.owner_id:
        owner = User.query.filter_by(discord_id=guild.owner_id).first()
        if owner:
            owner_name = owner.username
    
    created_at_iso = None
    if guild.created_at:
        created_at_iso = guild.created_at.isoformat()
    
    region = guild.preferred_locale or "Unknown"
    channel_count = guild.channel_count if guild.channel_count is not None else "N/A"
    
    try:
        member_count = db.session.execute(
            text("SELECT COUNT(DISTINCT user_id) FROM levels WHERE guild_id = :guild_id"),
            {'guild_id': guild_id}
        ).scalar() or 0
    except Exception as e:
        print(f"Error fetching member count for guild info {guild_id}: {e}")
        member_count = "Error"

    return api_success({
        "owner": owner_name,
        "created_at": created_at_iso,
        "region": region,
        "channels": channel_count,
        "member_count": member_count
    })

# Guild Activity API
@api.route('/api/guilds/<string:guild_id>/activity')
@login_required
def get_guild_activity(guild_id):
    """Get recent activity (XP gains, achievements) for a specific guild"""
    if not current_user.can_view_guild(guild_id):
        return api_error("You do not have permission to view this guild", 403)
    
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    if not guild:
        return api_error("Guild not found", 404)
    
    activities = []
    
    try:
        recent_xp_users = db.session.execute(
            text('''
            SELECT u.username, lvl.level, lvl.last_xp_time
            FROM levels lvl
            JOIN users u ON lvl.user_id = u.discord_id
            WHERE lvl.guild_id = :guild_id 
            AND lvl.last_xp_time IS NOT NULL
            ORDER BY lvl.last_xp_time DESC
            LIMIT 5 
            '''), 
            {'guild_id': guild_id}
        ).fetchall()
        
        for xp_user in recent_xp_users:
            if xp_user.last_xp_time:
                time_ago = format_time_ago((datetime.now() - datetime.fromtimestamp(xp_user.last_xp_time)).total_seconds())
                activities.append({
                    "description": f"{xp_user.username} recently gained XP",
                    "time": time_ago,
                    "details": f"Reached Level {xp_user.level}"
                })

    except Exception as e:
        print(f"Error fetching recent XP activity for {guild_id}: {e}")
    
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
            WHERE ua.guild_id = :guild_id 
            AND ua.completed = TRUE
            AND ua.completed_at IS NOT NULL
            ORDER BY ua.completed_at DESC
            LIMIT 5 
            '''),
            {'guild_id': guild_id}
        ).fetchall()
        
        for achievement in recent_achievements:
            if achievement.completed_at:
                time_ago = format_time_ago((datetime.now() - achievement.completed_at).total_seconds())
                activities.append({
                    "description": f"{achievement.username} earned achievement",
                    "time": time_ago,
                    "details": achievement.achievement_name
                })
                
    except Exception as e:
        print(f"Error fetching recent achievements for {guild_id}: {e}")

    try:
        activities = sorted(activities, key=lambda x: parse_time_ago_seconds(x["time"]))[:5]
    except Exception as sort_e:
        print(f"Error sorting activities for {guild_id}: {sort_e}")
    
    if not activities:
        return api_success([{
            "description": "No recent activity tracked",
            "time": "just now",
            "details": "Level ups and achievements will appear here."
        }])
    
    return api_success(activities)

def parse_time_ago_seconds(time_str):
    if "just now" in time_str: return 0
    parts = time_str.split()
    if len(parts) < 3: return 999999
    value = int(parts[0])
    unit = parts[1]
    if "minute" in unit: return value * 60
    if "hour" in unit: return value * 3600
    if "day" in unit: return value * 86400
    return 999999

# Helper function for time formatting
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

# Guild Settings API
@api.route('/api/guilds/<string:guild_id>/settings', methods=['GET'])
@login_required
@guild_admin_required
def get_guild_settings(guild_id):
    """Get settings for a specific guild"""
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    
    if not guild:
        return api_error("Guild not found", 404)
    
    settings = guild.settings
    if not settings:
        settings = ServerConfig(guild_id=guild.guild_id)
        db.session.add(settings)
        db.session.commit()
    
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

@api.route('/api/guilds/<string:guild_id>/settings', methods=['POST'])
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
        settings = ServerConfig(guild_id=guild.guild_id)
        db.session.add(settings)
    
    xp_settings = guild.xp_settings
    if not xp_settings:
        xp_settings = ServerXpSettings(guild_id=guild.guild_id)
        db.session.add(xp_settings)
    
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

# Guild Leaderboard API
@api.route('/api/guilds/<string:guild_id>/leaderboard')
@login_required
def get_guild_leaderboard(guild_id):
    """Get leaderboard data for a specific guild with cumulative XP."""
    if not current_user.can_view_guild(guild_id):
        return api_error("You do not have permission to view this guild", 403)
    
    try:
        # Fetch necessary data from DB, limit to potential top users
        # Order by level/xp as a pre-filter, we will re-sort later by cumulative XP
        query_text = '''
            SELECT 
                u.discord_id, 
                u.username, 
                u.avatar, 
                lvl.level, 
                lvl.xp 
            FROM levels lvl
            JOIN users u ON lvl.user_id = u.discord_id
            WHERE lvl.guild_id = :guild_id
            ORDER BY lvl.level DESC, lvl.xp DESC -- Pre-sort to get likely top candidates
            LIMIT 100 -- Fetch top 100 based on pre-sort
        '''
        
        params = {'guild_id': guild_id}
        
        leaderboard_raw = db.session.execute(text(query_text), params).fetchall()
        
        # Calculate cumulative XP and store in a list of dicts
        leaderboard_processed = []
        for user_data in leaderboard_raw:
            cumulative_xp = calculate_cumulative_xp(user_data.level, user_data.xp)
            leaderboard_processed.append({
                "user_id": user_data.discord_id,
                "username": user_data.username,
                "avatar": user_data.avatar,
                "level": user_data.level,
                "xp": user_data.xp, # Keep current level XP if needed
                "cumulative_xp": cumulative_xp
            })
            
        # Sort the processed list by cumulative XP
        leaderboard_sorted = sorted(leaderboard_processed, key=lambda x: x['cumulative_xp'], reverse=True)
        
        # Format final data with ranks based on the sorted list
        formatted_leaderboard = [
            {
                "rank": idx + 1,
                "user_id": user['user_id'],
                "username": user['username'],
                "avatar": user['avatar'],
                "level": user['level'],
                "xp": int(user['cumulative_xp']) # Cast cumulative XP to int here
            }
            for idx, user in enumerate(leaderboard_sorted)
        ]
        
        return api_success(formatted_leaderboard)
    except Exception as e:
        # Log the detailed error
        print(f"Error fetching leaderboard for guild {guild_id}: {e}")
        # Also print the query and params for debugging
        # print(f"Failed Query: {query_text}") # Be careful logging raw SQL
        # print(f"Failed Params: {params}")
        return api_error(f"Failed to fetch leaderboard data: {str(e)}")

# User Stats API
@api.route('/api/users/me/stats', methods=['GET'])
@login_required
def get_user_stats():
    """Get stats for the current user, including cumulative XP and total voice time"""
    try:
        user_id = current_user.discord_id # String ID
        
        # Fetch level, xp, and voice time from the 'levels' table for all user's guilds
        query = text("""
            SELECT level, xp, voice_time_seconds 
            FROM levels 
            WHERE user_id = :user_id
        """)
        results = db.session.execute(query, {'user_id': user_id}).fetchall()
        
        total_cumulative_xp = 0
        total_voice_seconds = 0
        total_guilds_with_levels = 0
        total_level_sum = 0
        
        for record in results:
            total_cumulative_xp += calculate_cumulative_xp(record.level, record.xp)
            total_voice_seconds += record.voice_time_seconds or 0
            total_guilds_with_levels += 1
            total_level_sum += record.level
            
        avg_level = round(total_level_sum / total_guilds_with_levels, 1) if total_guilds_with_levels > 0 else 0

        # Count total achievements (as before)
        try:
            total_achievements_result = db.session.execute(
                text('SELECT COUNT(*) FROM user_achievements WHERE user_id = :user_id AND completed = TRUE'),
                {'user_id': user_id}
            ).scalar() or 0
        except Exception as achievement_error:
            print(f"Error fetching achievements: {achievement_error}")
            total_achievements_result = 0
        total_achievements = int(total_achievements_result)
        
        # Get total guilds count from relationship
        total_guilds = len(current_user.guilds)
        
        return api_success({
            "username": current_user.username,
            "total_xp": int(total_cumulative_xp),
            "total_guilds": total_guilds,
            "achievements": total_achievements,
            "average_level": avg_level, 
            "total_voice_seconds": total_voice_seconds
        })
    except Exception as e:
        print(f"Error fetching user stats: {e}")
        # Fallback
        return api_success({
            "username": current_user.username,
            "total_xp": 0,
            "total_guilds": len(current_user.guilds), # Still show guilds if possible 
            "achievements": 0,
            "average_level": 0,
            "total_voice_seconds": 0
        })

# Admin APIs
@api.route('/api/admin/stats', methods=['GET'])
@login_required
@owner_required
def get_admin_stats():
    """Get admin stats (bot owner only)"""
    try:
        total_users = db.session.execute(
            text('SELECT COUNT(*) FROM users')
        ).scalar() or 0
        
        total_guilds = db.session.execute(
            text('SELECT COUNT(*) FROM guilds')
        ).scalar() or 0
        
        total_xp = db.session.execute(
            text('SELECT SUM(xp) FROM guild_members')
        ).scalar() or 0
        
        total_achievements = db.session.execute(
            text('SELECT COUNT(*) FROM user_achievements WHERE completed = TRUE')
        ).scalar() or 0
        
        uptime_days = 30
        
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
@api.route('/api/guilds/<string:guild_id>/achievements', methods=['GET'])
@login_required
def get_guild_achievements(guild_id):
    """Get achievements for a specific guild"""
    if not current_user.can_view_guild(guild_id):
        return api_error("You do not have permission to view this guild", 403)
    
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    if not guild:
        return api_error("Guild not found", 404)
    
    # Get total member count for the guild from the levels table
    try:
        member_count = db.session.execute(
            text("SELECT COUNT(DISTINCT user_id) FROM levels WHERE guild_id = :guild_id"),
            {'guild_id': guild_id}
        ).scalar() or 0
    except Exception as e:
        print(f"Error fetching member count for achievements page (guild {guild_id}): {e}")
        member_count = 0 # Default to 0 on error
    
    # Get achievements from the database (The rest of this query seems okay)
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
            "category": achievement.requirement_type,
            "icon": achievement.icon_path or "medal",
            "progress": achievement.progress,
            "requirement": achievement.requirement_value,
            "completed": achievement.completed,
            "completed_at": achievement.completed_at.isoformat() if achievement.completed_at else None,
            "members_completed": achievement.members_completed or 0,
            "member_count": member_count # Use the count fetched from levels
        })
    
    return api_success(formatted_achievements)

@api.route('/api/guilds/<string:guild_id>/achievements', methods=['POST'])
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
    
    required_fields = ['name', 'description', 'requirement_type', 'requirement_value']
    for field in required_fields:
        if field not in data:
            return api_error(f"Missing required field: {field}")
    
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
@api.route('/api/guilds/<string:guild_id>/events', methods=['GET'])
@login_required
def get_guild_events(guild_id):
    """Get events for a specific guild"""
    if not current_user.can_view_guild(guild_id):
        return api_error("You do not have permission to view this guild", 403)
    
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    if not guild:
        return api_error("Guild not found", 404)
    
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
        'guild_id': guild_id,
        'user_id': current_user.discord_id
    }).fetchall()
    
    formatted_events = []
    for event in events:
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

@api.route('/api/guilds/<string:guild_id>/events', methods=['POST'])
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
    
    required_fields = ['name', 'description', 'start_time', 'end_time', 'event_type']
    for field in required_fields:
        if field not in data:
            return api_error(f"Missing required field: {field}")
    
    try:
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
            'event_id': str(uuid.uuid4()),
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

@api.route('/api/guilds/<string:guild_id>/events/<event_id>/join', methods=['POST'])
@login_required
def join_guild_event(guild_id, event_id):
    """Join an event"""
    if not current_user.can_view_guild(guild_id):
        return api_error("You do not have permission to join this event", 403)
    
    try:
        event = db.session.execute(text('''
            SELECT start_time, end_time, status
            FROM discord_scheduled_events
            WHERE event_id = :event_id AND guild_id = :guild_id
        '''), {
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
        
        db.session.execute(text('''
            INSERT INTO event_attendance (event_id, user_id, guild_id, status)
            VALUES (:event_id, :user_id, :guild_id, 'going')
            ON CONFLICT (event_id, user_id) DO UPDATE
            SET status = 'going', joined_at = CURRENT_TIMESTAMP
        '''), {
            'event_id': event_id,
            'user_id': current_user.discord_id,
            'guild_id': guild_id
        })
        
        db.session.commit()
        return api_success(message="Successfully joined event")
    except Exception as e:
        db.session.rollback()
        return api_error(f"Failed to join event: {str(e)}")

# Activity Chart API
@api.route('/api/guilds/<string:guild_id>/activity-chart')
@login_required
def get_guild_activity_chart(guild_id):
    """Get activity chart data (users gaining XP) for a specific guild"""
    if not current_user.can_view_guild(guild_id):
        return api_error("You do not have permission to view this guild", 403)
    
    guild = Guild.query.filter_by(guild_id=guild_id).first()
    if not guild:
        return api_error("Guild not found", 404)
    
    # Get activity data for the past 7 days
    days = 7
    labels = []
    xp_data = [] # Renamed from 'data'
    message_data = [] # Placeholder data for messages
    
    try:
        for i in range(days - 1, -1, -1):  # Go from 6 days ago to today
            target_date = datetime.now().date() - timedelta(days=i)
            # Convert date to start/end epoch timestamps for the day
            day_start = datetime.combine(target_date, datetime.min.time()).timestamp()
            day_end = datetime.combine(target_date, datetime.max.time()).timestamp()
            
            # Count users who gained XP on this day
            count = db.session.execute(
                text('''
                    SELECT COUNT(DISTINCT user_id) 
                    FROM levels 
                    WHERE guild_id = :guild_id 
                    AND last_xp_time >= :day_start 
                    AND last_xp_time < :day_end
                '''),
                {
                    'guild_id': guild_id,
                    'day_start': day_start,
                    'day_end': day_end
                }
            ).scalar() or 0
            
            label = target_date.strftime('%a') # Short day name (Mon, Tue, etc.)
            labels.append(label)
            xp_data.append(count)
            # Add placeholder message data (e.g., scaling with XP users)
            message_data.append(count * 10 + 50 if count > 0 else 0) 
            
    except Exception as e:
        print(f"Error fetching activity chart data for guild {guild_id}: {e}")
        # Return default data in case of error
        default_labels = [(datetime.now().date() - timedelta(days=i)).strftime('%a') for i in range(days - 1, -1, -1)]
        return api_success({
            "labels": default_labels,
            "datasets": [
                {"label": "Active Users (XP Gain)", "data": [0]*days},
                {"label": "Messages Sent", "data": [0]*days} # Placeholder
            ]
        })
        
    # Structure data for Chart.js
    chart_data = {
        "labels": labels,
        "datasets": [
            {
                "label": "Active Users (XP Gain)",
                "data": xp_data,
                "borderColor": "rgba(255, 102, 102, 1)", # Red
                "backgroundColor": "rgba(255, 102, 102, 0.2)",
                "fill": True,
                "tension": 0.4
            },
            {
                "label": "Messages Sent (Est.)", # Indicate it's an estimate/placeholder
                "data": message_data,
                "borderColor": "rgba(0, 204, 204, 1)", # Cyan
                "backgroundColor": "rgba(0, 204, 204, 0.2)",
                "fill": True,
                "tension": 0.4
            }
        ]
    }
    
    return api_success(chart_data)

# Helper function (ensure it exists or move if needed)
def query_with_string_ids(query_text, params):
    """Execute SQL query with string ID parameters, ensuring proper type conversion"""
    updated_params = params.copy()
    # No longer needed as all IDs are strings
    return db.session.execute(text(query_text), updated_params) 