from cldashboard import db, login_manager
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import cast, BigInteger, Column, String, DateTime, func, ForeignKey, Integer, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

@login_manager.user_loader
def load_user(user_id):
    # Convert string user_id from session to integer for database lookup
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    # Using BigInteger to match the BIGINT type in PostgreSQL
    discord_id = Column(BigInteger, primary_key=True)
    username = Column(String(255), nullable=False)
    discriminator = Column(String(4))
    email = Column(String(255))
    avatar = Column(String(255))
    # Changed role column to JSONB, allowing a list of roles
    role = Column(JSONB, default=lambda: ["user"], nullable=False) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # This is needed for Flask-Login to work correctly with a non-integer id
    def get_id(self):
        return str(self.discord_id)
    
    # User's guilds (Discord servers)
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
        for guild in self.guilds:
            if str(guild.guild_id) == str(guild_id):
                return True
        return False
    
    def can_manage_guild(self, guild_id):
        """Check if user can manage a specific guild"""
        if self.is_owner:
            return True
            
        for guild in self.guilds:
            if str(guild.guild_id) == str(guild_id):
                # Check if user is admin or owner of the guild
                return guild.user_has_permission(self.discord_id, ['admin', 'owner'])
        return False
        
    @staticmethod
    def get_or_create(discord_user):
        """Get existing user or create a new one from Discord user data"""
        user_id = int(discord_user['id'])
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

    def get_int_id(self):
        """Return the discord_id as an integer for database queries"""
        return self.discord_id


class Guild(db.Model):
    __tablename__ = 'guilds'
    
    # Using BigInteger to match the BIGINT type in PostgreSQL
    guild_id = Column(BigInteger, primary_key=True)
    name = Column(String(255), nullable=False)
    icon = Column(String(255))
    owner_id = Column(BigInteger) # Nullable if owner info isn't always present
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Guild settings - use SQLAlchemy's cast directly
    settings = relationship('ServerConfig', backref='guild', uselist=False, 
                             foreign_keys="ServerConfig.guild_id",
                             primaryjoin="Guild.guild_id == cast(ServerConfig.guild_id, BigInteger)")
    xp_settings = relationship('ServerXpSettings', backref='guild', uselist=False,
                                foreign_keys="ServerXpSettings.guild_id",
                                primaryjoin="Guild.guild_id == cast(ServerXpSettings.guild_id, BigInteger)")
    
    def __repr__(self):
        return f"Guild('{self.name}', '{self.guild_id}')"
        
    def user_has_permission(self, user_discord_id, required_roles):
        """Check if a user has any of the required roles in this guild"""
        # Convert string ID to integer if needed
        user_id = int(user_discord_id) if isinstance(user_discord_id, str) else user_discord_id
        
        membership = GuildMember.query.filter_by(
            guild_id=self.guild_id, 
            user_id=user_id
        ).first()
        
        if not membership:
            return False
        
        # Since the bot uses a different role system, we'll consider anyone in guild_members to have basic access
        # You may need to adjust this based on your specific permissions system
        return True


# Association table for User-Guild many-to-many relationship
user_guild = db.Table('user_guild',
    db.Column('user_id', db.BigInteger, db.ForeignKey('users.discord_id'), primary_key=True),
    db.Column('guild_id', db.BigInteger, db.ForeignKey('guilds.guild_id'), primary_key=True)
)


class GuildMember(db.Model):
    __tablename__ = 'guild_members'
    
    # Composite primary key matching the bot database using BigInteger
    guild_id = Column(BigInteger, db.ForeignKey('guilds.guild_id'), primary_key=True)
    user_id = Column(BigInteger, db.ForeignKey('users.discord_id'), primary_key=True)
    
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
    
    guild_id = Column(BigInteger, db.ForeignKey('guilds.guild_id', ondelete='CASCADE'), primary_key=True)
    
    # Channel Settings
    level_up_channel = Column(db.String(20), nullable=True)
    event_channel = Column(db.String(20), nullable=True)
    achievement_channel = Column(db.String(20), nullable=True)
    
    # Other settings can be added as needed
    
    def __repr__(self):
        return f"ServerConfig(guild_id={self.guild_id})"


class ServerXpSettings(db.Model):
    __tablename__ = 'server_xp_settings'
    
    guild_id = Column(BigInteger, db.ForeignKey('guilds.guild_id', ondelete='CASCADE'), primary_key=True)
    
    # XP Settings
    min_xp = Column(db.Integer, default=5)
    max_xp = Column(db.Integer, default=15)
    cooldown = Column(db.Integer, default=60)  # in seconds
    
    def __repr__(self):
        return f"ServerXpSettings(guild_id={self.guild_id})" 