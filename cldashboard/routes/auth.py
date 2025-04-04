from flask import Blueprint, redirect, url_for, session, flash, request, Response
from flask_login import login_user, logout_user, current_user, login_required
from cldashboard import discord, db
from cldashboard.models.user import User, Guild
import os
import requests
import json
from datetime import datetime
from sqlalchemy import text

auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    """Redirect to Discord OAuth login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    # Generate state token for CSRF protection
    state = os.urandom(16).hex()
    session['oauth2_state'] = state
    session.modified = True  # Ensure session is saved
    
    # Get Discord authorization URL with required scopes
    auth_url = discord.create_session(
        scope=['identify', 'email', 'guilds'],
        state=state,
        prompt='consent'
    )
    
    # Extract URL if a Response object is returned
    if isinstance(auth_url, Response):
        # If it's a redirect response, extract the Location header
        if auth_url.status_code == 302 and 'Location' in auth_url.headers:
            auth_url = auth_url.headers['Location']
        # If it's not a redirect or doesn't have Location, use the string value
        else:
            auth_url = str(auth_url.get_data(as_text=True))
    
    # Now auth_url should be a string URL
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
    # Log state values for debugging
    req_state = request.args.get('state', 'no-state-in-request')
    sess_state = session.get('oauth2_state', 'no-state-in-session')
    
    # Debug logging for local testing
    print("=" * 50)
    print(f"Discord callback received - Host: {request.host}")
    print(f"Redirect URI from env: {os.getenv('DISCORD_REDIRECT_URI')}")
    print(f"State from request: {req_state}")
    print(f"State from session: {sess_state}")
    print("=" * 50)
    
    # Get the authorization code from the callback
    code = request.args.get('code')
    if not code:
        flash('No authorization code received from Discord.', 'danger')
        return redirect(url_for('main.home'))
    
    try:
        # Implement our own token exchange to bypass Flask-Discord's state check
        client_id = os.getenv('DISCORD_CLIENT_ID')
        client_secret = os.getenv('DISCORD_CLIENT_SECRET')
        redirect_uri = os.getenv('DISCORD_REDIRECT_URI')
        
        # For local testing: Override redirect URI based on request host if localhost
        if 'localhost' in request.host:
            redirect_uri = f"http://{request.host}/auth/discord/callback"
            print(f"Local testing detected. Updated redirect URI: {redirect_uri}")
        
        # Exchange code for token
        token_url = 'https://discord.com/api/oauth2/token'
        token_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri
        }
        token_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        token_response = requests.post(token_url, data=token_data, headers=token_headers)
        
        if token_response.status_code != 200:
            flash(f'Failed to exchange code for token: {token_response.text}', 'danger')
            return redirect(url_for('main.home'))
        
        token_json = token_response.json()
        access_token = token_json['access_token']
        
        # Get user info from Discord
        user_url = 'https://discord.com/api/users/@me'
        guilds_url = 'https://discord.com/api/users/@me/guilds'
        headers = {'Authorization': f'Bearer {access_token}'}
        
        user_response = requests.get(user_url, headers=headers)
        if user_response.status_code != 200:
            flash(f'Failed to get user info: {user_response.text}', 'danger')
            return redirect(url_for('main.home'))
        
        discord_user_data = user_response.json()
        
        # Format Discord data
        discord_data = {
            'id': discord_user_data['id'],
            'username': discord_user_data['username'],
            'discriminator': discord_user_data.get('discriminator', '0'),
            'email': discord_user_data.get('email', ''),
            'avatar': f"https://cdn.discordapp.com/avatars/{discord_user_data['id']}/{discord_user_data['avatar']}.png" if discord_user_data.get('avatar') else None
        }
        
        # Get or create user
        user = User.get_or_create(discord_data)
        
        # Get user's guilds 
        guilds_response = requests.get(guilds_url, headers=headers)
        if guilds_response.status_code != 200:
            flash(f'Failed to get guild info: {guilds_response.text}', 'warning')
            # Continue anyway since we have the user
        else:
            # Process guild data
            for guild_data in guilds_response.json():
                # Skip guilds where the user doesn't have admin permissions
                if not guild_data.get('owner') and not guild_data.get('permissions', 0) & 0x8:  # 0x8 is ADMINISTRATOR permission
                    continue
                
                guild_info = {
                    'guild_id': str(guild_data['id']),
                    'name': guild_data['name'],
                    'icon': f"https://cdn.discordapp.com/icons/{guild_data['id']}/{guild_data['icon']}.png" if guild_data.get('icon') else None,
                    'owner_id': str(guild_data.get('owner_id', user.discord_id)),  # Use user's ID as fallback if owner_id is not provided
                    'created_at': datetime.utcnow()
                }
                
                # Update or create the guild in the database
                db_guild = Guild.query.filter_by(guild_id=guild_info['guild_id']).first()
                
                if not db_guild:
                    db_guild = Guild(**guild_info)
                    db.session.add(db_guild)
                else:
                    # Update guild data
                    db_guild.name = guild_info['name']
                    db_guild.icon = guild_info['icon']
                    db_guild.owner_id = guild_info['owner_id']  # Update owner_id as well
                
                # Add guild to user's guilds if not already added
                if db_guild not in user.guilds:
                    # Insert into user_guild table with integer conversion
                    db.session.execute(
                        text('INSERT INTO user_guild (user_id, guild_id) VALUES (:user_id, :guild_id) ON CONFLICT DO NOTHING'),
                        {'user_id': int(user.discord_id), 'guild_id': int(db_guild.guild_id)}
                    )
        
        db.session.commit()
        
        # Login user
        login_user(user)
        user.update_last_login()
        
        # Redirect to next page or dashboard
        next_page = session.get('next')
        if next_page:
            session.pop('next')
            return redirect(next_page)
        
        flash('Successfully logged in!', 'success')
        return redirect(url_for('dashboard.index'))
    
    except Exception as e:
        flash(f'Authentication failed: {str(e)}', 'danger')
        return redirect(url_for('main.home')) 