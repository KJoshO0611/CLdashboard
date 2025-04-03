from flask import Blueprint, redirect, url_for, session, flash, request, Response
from flask_login import login_user, logout_user, current_user, login_required
from cldashboard import discord, db
from cldashboard.models.user import User, Guild
import os

auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    """Redirect to Discord OAuth login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    # Generate state token for CSRF protection
    state = os.urandom(16).hex()
    session['oauth2_state'] = state
    
    # Get Discord authorization URL with required scopes
    auth_url = discord.create_session(
        scope=['identify', 'email', 'guilds'],
        state=state,
        prompt='consent'
    )
    
    # Return the URL directly instead of the Response object
    return redirect(auth_url)

@auth.route('/logout')
@login_required
def logout():
    """Logout the current user"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))

@auth.route('/discord/callback')
def discord_callback():
    """Handle Discord OAuth callback"""
    # Verify state token to protect against CSRF
    if 'oauth2_state' not in session or request.args.get('state') != session['oauth2_state']:
        flash('Authentication failed. Please try again.', 'danger')
        return redirect(url_for('main.home'))
    
    try:
        # Exchange code for token
        discord.callback()
        
        # Get authenticated user from Discord
        discord_user = discord.fetch_user()
        discord_data = {
            'id': discord_user.id,
            'username': discord_user.name,
            'discriminator': discord_user.discriminator,
            'email': discord_user.email,
            'avatar': discord_user.avatar_url
        }
        
        # Get or create user
        user = User.get_or_create(discord_data)
        
        # Get user's guilds
        discord_guilds = discord.fetch_guilds()
        
        # Store guilds in database
        for guild in discord_guilds:
            # Check if guild has the bot
            guild_data = {
                'guild_id': str(guild.id),
                'name': guild.name,
                'icon': guild.icon_url,
                'owner_id': str(guild.owner_id) if hasattr(guild, 'owner_id') else None
            }
            
            # Update or create the guild in the database
            db_guild = Guild.query.filter_by(guild_id=str(guild.id)).first()
            
            if not db_guild:
                db_guild = Guild(**guild_data)
                db.session.add(db_guild)
            else:
                # Update guild data
                db_guild.name = guild.name
                db_guild.icon = guild.icon_url
            
            # Add guild to user's guilds if not already added
            if db_guild not in user.guilds:
                user.guilds.append(db_guild)
        
        db.session.commit()
        
        # Login user
        login_user(user)
        user.update_last_login()
        
        # Redirect to next page or dashboard
        next_page = session.get('next')
        if next_page:
            session.pop('next')
            return redirect(next_page)
        
        # Ensure we're returning a string URL, not a Response object
        return redirect(url_for('dashboard.index'))
    
    except Exception as e:
        flash(f'Authentication failed: {str(e)}', 'danger')
        return redirect(url_for('main.home')) 