from flask import Blueprint, redirect, url_for, session, flash, request, Response
from flask_login import login_user, logout_user, current_user, login_required
from cldashboard import discord, db
from cldashboard.models.user import User, Guild, user_guild
import os
import requests
import json
from datetime import datetime
from sqlalchemy import text, delete, insert

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
        
        # Format Discord data (IDs are strings)
        discord_data = {
            'id': str(discord_user_data['id']), # Ensure ID is string
            'username': discord_user_data['username'],
            'discriminator': discord_user_data.get('discriminator', '0'),
            'email': discord_user_data.get('email', ''),
            'avatar': f"https://cdn.discordapp.com/avatars/{discord_user_data['id']}/{discord_user_data['avatar']}.png" if discord_user_data.get('avatar') else None
        }
        
        # Get or create user (PK is now String)
        user = User.get_or_create(discord_data) 
        db_user_id = user.discord_id # This is already a string

        # --- Start of Guild Filtering Logic ---
        
        # 1. Get User's Admin Guild IDs from Discord (as strings)
        user_admin_discord_guild_ids = set()
        has_admin_in_any_mutual = False
        try:
            guilds_response = requests.get(guilds_url, headers=headers)
            guilds_response.raise_for_status()
            ADMINISTRATOR_PERMISSION = 0x8
            for guild_data in guilds_response.json():
                permissions = int(guild_data.get('permissions', 0))
                if (permissions & ADMINISTRATOR_PERMISSION) == ADMINISTRATOR_PERMISSION:
                    # Store IDs as strings
                    user_admin_discord_guild_ids.add(str(guild_data['id']))
        except requests.RequestException as e:
            flash(f'Could not fetch guild information from Discord: {e}', 'warning')
            
        # 2. Get Bot's Guild IDs from DB (they are TEXT/String now)
        bot_present_guild_ids = set()
        try:
            result = db.session.execute(text("SELECT guild_id FROM guilds"))
            # IDs are already strings
            bot_present_guild_ids = {row[0] for row in result}
        except Exception as e:
            db.session.rollback()
            flash(f'Database error fetching bot guilds: {e}', 'danger')
            print(f"DB Error fetching bot guilds: {e}")
            return redirect(url_for('main.home')) 

        # 3. Find Mutual Guild IDs (intersection of strings)
        mutual_guild_ids = user_admin_discord_guild_ids.intersection(bot_present_guild_ids)
        
        # Check if user is admin in ANY of the *mutual* guilds
        if any(gid in user_admin_discord_guild_ids for gid in mutual_guild_ids):
             has_admin_in_any_mutual = True

        # 4. Synchronize user_guild Table (using string IDs)
        try:
            # Get current associations from DB (user_id is string)
            result = db.session.execute(
                text("SELECT guild_id FROM user_guild WHERE user_id = :user_id"),
                {'user_id': db_user_id}
            )
            # IDs are already strings
            current_db_associated_guild_ids = {row[0] for row in result}

            # Calculate differences (sets of strings)
            guilds_to_add = mutual_guild_ids - current_db_associated_guild_ids
            guilds_to_remove = current_db_associated_guild_ids - mutual_guild_ids

            # Remove old associations (using string IDs)
            if guilds_to_remove:
                # Use the imported user_guild Table object directly
                delete_stmt = delete(user_guild).where(
                    user_guild.c.user_id == db_user_id
                ).where(
                    user_guild.c.guild_id.in_(list(guilds_to_remove)) # Use .in_() for list comparison
                )
                db.session.execute(delete_stmt) # Parameters are implicitly handled by where clause
                print(f"Removed guilds {guilds_to_remove} for user {db_user_id}")

            # Add new associations (using string IDs)
            if guilds_to_add:
                insert_values = [{'user_id': db_user_id, 'guild_id': gid} for gid in guilds_to_add]
                for values in insert_values:
                     # Using text here is fine for simple INSERT ON CONFLICT
                     db.session.execute(
                         text('INSERT INTO user_guild (user_id, guild_id) VALUES (:user_id, :guild_id) ON CONFLICT DO NOTHING'),
                         values
                     )
                print(f"Added guilds {guilds_to_add} for user {db_user_id}")

            # --- Assign Dashboard Role --- 
            bot_owner_id_str = os.getenv('BOT_OWNER_ID')
            target_role = ['user']

            # Compare strings
            if bot_owner_id_str and db_user_id == bot_owner_id_str:
                target_role = ['owner']
            elif has_admin_in_any_mutual:
                 target_role = ['admin']
                 
            # Update role (user_id is string)
            update_role_stmt = text("UPDATE users SET role = :role WHERE discord_id = :user_id")
            db.session.execute(update_role_stmt, {'role': json.dumps(target_role), 'user_id': db_user_id})
            print(f"Set dashboard role for user {db_user_id} to {target_role}")
            # --- End Assign Dashboard Role --- 

            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            flash(f'Database error updating user guild access or role: {e}', 'danger')
            print(f"DB Error updating user_guild or role: {e}")
            return redirect(url_for('main.home'))

        # --- End of Guild Filtering Logic ---
        
        # Login user
        login_user(user)
        user.update_last_login() # Assumes this method commits its own changes or is handled by login_user's session management
        
        # Redirect to next page or dashboard
        next_page = session.get('next')
        if next_page:
            session.pop('next')
            return redirect(next_page)
        
        flash('Successfully logged in!', 'success')
        return redirect(url_for('dashboard.index'))
    
    except Exception as e:
        db.session.rollback() # Rollback any potential changes from get_or_create or earlier steps
        flash(f'Authentication failed during callback processing: {str(e)}', 'danger')
        # Log the detailed error server-side
        import traceback
        print(f"Error in discord_callback: {e}")
        traceback.print_exc()
        return redirect(url_for('main.home')) 