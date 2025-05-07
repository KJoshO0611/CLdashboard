from .. import db, login_manager
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import Column, String, DateTime, func, ForeignKey, Integer, Boolean, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

@login_manager.user_loader
def load_user(user_id):
    # Primary key is now String
    return User.query.get(str(user_id))

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    # Change ID to String
    discord_id = Column(String, primary_key=True)
    username = Column(String(255), nullable=False)
    discriminator = Column(String(4))
    email = Column(String(255))
    avatar = Column(String(255))
    # Changed role column to JSONB, allowing a list of roles
    role = Column(JSONB, default=lambda: ["user"], nullable=False) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Flask-Login get_id should return the PK as is (String)
    def get_id(self):
        return self.discord_id
    
    guilds = relationship('Guild', secondary='user_guild', backref='users')
    
    def __repr__(self):
        return f"User('{self.username}', '{self.discord_id}')"
    
    @property
    def is_owner(self):
        return isinstance(self.role, list) and 'owner' in self.role
        
    @property
    def is_admin(self):
        return isinstance(self.role, list) and 'admin' in self.role
    
    @property
    def is_moderator(self):
        return isinstance(self.role, list) and ('moderator' in self.role or self.is_admin)
    
    def update_last_login(self):
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def can_view_guild(self, guild_id):
        """Check if user can view a specific guild"""
        # IDs are now strings, compare directly.
        # Ensure input guild_id is treated as string.
        target_guild_id = str(guild_id) 
            
        for guild in self.guilds:
            # Both guild.guild_id and target_guild_id are strings
            if guild.guild_id == target_guild_id:
                return True
        return False
    
    def can_manage_guild(self, guild_id):
        """Check if user can manage a specific guild based on their dashboard role"""
        # Bot owner can manage any guild visible to the bot
        if self.is_owner:
            return True
        
        # Check if user has the global admin role from the dashboard perspective
        if not self.is_admin: # is_admin checks for 'admin' in self.role list
            return False
            
        # If they are an admin, check if they actually have access to this specific guild
        # (i.e., is it one of the mutual guilds determined during login?)
        # This uses the corrected can_view_guild logic
        return self.can_view_guild(guild_id)
        
    @staticmethod
    def get_or_create(discord_user):
        """Get existing user or create a new one from Discord user data"""
        # ID from Discord is string, model PK is String
        user_id = str(discord_user['id'])
        user = User.query.filter_by(discord_id=user_id).first()
        
        if not user:
            # Create new user
            user = User(
                discord_id=user_id,
                username=discord_user['username'],
                discriminator=discord_user.get('discriminator'),
                email=discord_user.get('email'),
                avatar=discord_user.get('avatar')
            )
            db.session.add(user)
            db.session.commit()
        else:
            # Update existing user data
            user.username = discord_user['username']
            user.discriminator = discord_user.get('discriminator')
            user.email = discord_user.get('email')
            user.avatar = discord_user.get('avatar')
            user.last_login = datetime.utcnow()
            db.session.commit()
            
        return user

# New RoleReward Model - Moved before Guild
class LevelRole(db.Model):
    __tablename__ = 'level_roles'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(String, db.ForeignKey('guilds.guild_id'), nullable=False)
    level = Column(Integer, nullable=False)
    role_id = Column(String, nullable=False)
    role_name = Column(String, nullable=True) # For easier display in dashboard
    behavior = Column(String, default='add', nullable=False) # 'add' or 'remove'
    
    # Relationship defined here, back_populates connects to Guild.role_rewards
    guild = relationship('Guild', back_populates='level_roles') 
    
    def __repr__(self):
        return f"LevelRole(guild={self.guild_id}, level={self.level}, role={self.role_id})" 

class Guild(db.Model):
    __tablename__ = 'guilds'
    
    # Change IDs to String
    guild_id = Column(String, primary_key=True)
    name = Column(String(255), nullable=False)
    icon = Column(String(255))
    owner_id = Column(String) # Nullable if owner info isn't always present
    created_at = Column(DateTime(timezone=True))
    # Add channel_count and preferred_locale columns
    channel_count = Column(Integer)
    preferred_locale = Column(String(10))
    
    # Relationships - No cast needed as both sides are now String
    settings = relationship('ServerConfig', backref='guild', uselist=False, 
                             foreign_keys="ServerConfig.guild_id",
                             primaryjoin="Guild.guild_id == ServerConfig.guild_id") 
    xp_settings = relationship('ServerXpSettings', backref='guild', uselist=False,
                                foreign_keys="ServerXpSettings.guild_id",
                                primaryjoin="Guild.guild_id == ServerXpSettings.guild_id")
    # Relationship defined here, connects to LevelRole.guild
    level_roles = relationship('LevelRole', back_populates='guild', cascade='all, delete-orphan', order_by="LevelRole.level") 
    event_settings = relationship('GuildEventSettings', backref='guild', uselist=False)
    
    def __repr__(self):
        return f"Guild('{self.name}', '{self.guild_id}')"
        
    def user_has_permission(self, user_discord_id, required_roles):
        """Check if a user has any of the required roles in this guild"""
        # user_discord_id is already string
        user_id = str(user_discord_id)
        
        # guild_id is already string
        membership = GuildMember.query.filter_by(
            guild_id=self.guild_id, 
            user_id=user_id
        ).first()
        
        if not membership:
            return False
        
        # Since the bot uses a different role system, we'll consider anyone in guild_members to have basic access
        # You may need to adjust this based on your specific permissions system
        return True


# Association table - Use String for keys
user_guild = db.Table('user_guild',
    db.Column('user_id', db.String, db.ForeignKey('users.discord_id'), primary_key=True),
    db.Column('guild_id', db.String, db.ForeignKey('guilds.guild_id'), primary_key=True)
)


class GuildMember(db.Model):
    __tablename__ = 'guild_members' # Assuming bot manages this, check bot schema
    
    # Change IDs to String (if this model is used by dashboard)
    guild_id = Column(String, db.ForeignKey('guilds.guild_id'), primary_key=True)
    user_id = Column(String, db.ForeignKey('users.discord_id'), primary_key=True)
    
    # Fields from the bot's database
    level = Column(db.Integer, default=1)
    xp = Column(db.Integer, default=0)
    last_xp_gain = Column(db.DateTime)
    previous_xp = Column(db.Integer, default=0)
    
    # Additional fields for our dashboard
    roles = Column(db.JSON, default=["user"])  # ["owner", "admin", "moderator", "user"]
    
    def __repr__(self):
        return f"GuildMember('{self.guild_id}', '{self.user_id}')"


class ServerConfig(db.Model):
    __tablename__ = 'server_config'
    
    # ID is already String, ForeignKey points to Guild.guild_id (now String)
    guild_id = Column(String, db.ForeignKey('guilds.guild_id'), primary_key=True)
    
    # Channel Settings
    level_up_channel = Column(db.String(20), nullable=True)
    event_channel = Column(db.String(20), nullable=True)
    achievement_channel = Column(db.String(20), nullable=True)
    announce_achievements = Column(Boolean, default=True)

    # Role Reward Settings
    stack_roles = Column(Boolean, default=True)
    announce_roles = Column(Boolean, default=True)
    announce_achievements = Column(Boolean, default=True)

    # Role Reward Settings
    stack_roles = Column(Boolean, default=True)
    announce_roles = Column(Boolean, default=True)
    
    # Other settings can be added as needed
    
    def __repr__(self):
        return f"ServerConfig(guild_id={self.guild_id})"


class ServerXpSettings(db.Model):
    __tablename__ = 'server_xp_settings'
    
    # ID is already String, ForeignKey points to Guild.guild_id (now String)
    guild_id = Column(String, db.ForeignKey('guilds.guild_id'), primary_key=True)
    
    # XP Settings
    min_xp = Column(db.Integer, default=5)
    max_xp = Column(db.Integer, default=15)
    cooldown = Column(db.Integer, default=60)  # in seconds
    
    def __repr__(self):
        return f"ServerXpSettings(guild_id={self.guild_id})" 

# Add relationship to Guild Model (if needed, though likely querying events directly)
# Guild.events = relationship('Event', backref='guild', lazy=True) 

# --- New Event Model ---
class Event(db.Model):
    __tablename__ = 'discord_scheduled_events'

    internal_id = Column(Integer, primary_key=True) # Auto-incrementing PK
    event_id = Column(String, nullable=True, index=True) # Discord Event ID (can be null for non-Discord events?)
    guild_id = Column(String, db.ForeignKey('guilds.guild_id'), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(1000))
    start_time = Column(db.Float, nullable=False) # Unix timestamp (double precision)
    end_time = Column(db.Float, nullable=True)    # Unix timestamp (double precision)
    event_type = Column(String(50)) # e.g., 'VOICE', 'STAGE', 'EXTERNAL'
    status = Column(String(50), index=True) # e.g., 'SCHEDULED', 'ACTIVE', 'COMPLETED', 'CANCELLED'
    creator_id = Column(String) 
    associated_boost_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=False), server_default=func.now()) # Ensure timezone matches DB
    updated_at = Column(DateTime(timezone=False), onupdate=func.now()) # Ensure timezone matches DB
    
    guild = relationship('Guild')

    def __repr__(self):
        return f"<Event {self.internal_id}: {self.name} ({self.guild_id})>"

# Add relationship to Guild Model (if needed, though likely querying events directly)
# Guild.events = relationship('Event', backref='guild', lazy=True) 

# --- New Guild Event Settings Model ---
class GuildEventSettings(db.Model):
    __tablename__ = 'guild_event_settings'

    guild_id = Column(String, db.ForeignKey('guilds.guild_id'), primary_key=True)
    attendance_bonus_xp = Column(Integer, default=100, nullable=False)
    # Add other event-specific settings here if needed in the future

    def __repr__(self):
        return f"<GuildEventSettings {self.guild_id}: BonusXP={self.attendance_bonus_xp}>" 

# --- New Event Attendance Model ---
class EventAttendance(db.Model):
    __tablename__ = 'event_attendance'

    id = Column(Integer, primary_key=True)
    event_id = Column(String, nullable=False, index=True) # Link to Event.event_id (Discord ID)
    user_id = Column(String, db.ForeignKey('users.discord_id'), nullable=False, index=True)
    status = Column(String(50)) # e.g., 'active', 'completed', 'absent'?
    joined_at = Column(DateTime(timezone=False)) # Use timezone=False if DB doesn't store timezone
    guild_id = Column(String, db.ForeignKey('guilds.guild_id'), nullable=False, index=True)
    
    # Relationships (Optional, depending on query needs)
    user = relationship('User') 
    # Event relationship might be tricky if using event_id string directly
    # Instead, usually query attendance based on event_id

    def __repr__(self):
        return f"<EventAttendance event={self.event_id} user={self.user_id} status={self.status}>"

# Add relationship to Guild Model (if needed, though likely querying events directly)
# Guild.events = relationship('Event', backref='guild', lazy=True) 