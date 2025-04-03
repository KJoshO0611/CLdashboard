from cldashboard import db, login_manager
from flask_login import UserMixin
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(20), unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=False)
    discriminator = db.Column(db.String(4), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    avatar = db.Column(db.String(150), nullable=True)
    role = db.Column(db.String(20), default='user')  # 'owner', 'admin', 'moderator', 'user'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    
    # User's guilds (Discord servers)
    guilds = db.relationship('Guild', secondary='user_guild', backref='users')
    
    def __repr__(self):
        return f"User('{self.username}', '{self.discord_id}')"
    
    @property
    def is_owner(self):
        return self.role == 'owner'
        
    @property
    def is_admin(self):
        return self.role == 'admin' or self.role == 'owner'
    
    @property
    def is_moderator(self):
        return self.role == 'moderator' or self.is_admin
    
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
        user = User.query.filter_by(discord_id=str(discord_user['id'])).first()
        
        if not user:
            # Create new user
            user = User(
                discord_id=str(discord_user['id']),
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


class Guild(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guild_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(150), nullable=True)
    owner_id = db.Column(db.String(20), nullable=False)
    
    # Guild settings
    settings = db.relationship('GuildSettings', backref='guild', uselist=False)
    
    def __repr__(self):
        return f"Guild('{self.name}', '{self.guild_id}')"
        
    def user_has_permission(self, user_discord_id, required_roles):
        """Check if a user has any of the required roles in this guild"""
        membership = GuildMember.query.filter_by(
            guild_id=self.guild_id, 
            user_discord_id=user_discord_id
        ).first()
        
        if not membership:
            return False
        
        if any(role in required_roles for role in membership.roles):
            return True
            
        return False


# Association table for User-Guild many-to-many relationship
user_guild = db.Table('user_guild',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('guild_id', db.Integer, db.ForeignKey('guild.id'), primary_key=True)
)


class GuildMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guild_id = db.Column(db.String(20), nullable=False)
    user_discord_id = db.Column(db.String(20), nullable=False)
    roles = db.Column(db.JSON, default=["user"])  # ["owner", "admin", "moderator", "user"]
    
    __table_args__ = (
        db.UniqueConstraint('guild_id', 'user_discord_id', name='unique_guild_member'),
    )
    
    def __repr__(self):
        return f"GuildMember('{self.guild_id}', '{self.user_discord_id}')"


class GuildSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guild_id = db.Column(db.Integer, db.ForeignKey('guild.id'), nullable=False)
    
    # XP Settings
    min_xp = db.Column(db.Integer, default=5)
    max_xp = db.Column(db.Integer, default=15)
    xp_cooldown = db.Column(db.Integer, default=60)  # in seconds
    
    # Channel Settings
    level_up_channel_id = db.Column(db.String(20), nullable=True)
    event_announcement_channel_id = db.Column(db.String(20), nullable=True)
    
    # Other settings can be added as needed
    
    def __repr__(self):
        return f"GuildSettings(guild_id={self.guild_id})" 