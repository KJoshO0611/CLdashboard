# Local Testing Guide

## Discord OAuth Configuration

The OAuth redirect issue occurs because after authentication, Discord redirects back to the URL specified in your Discord Developer Portal, which is currently set to the Render URL.

## Files to Check/Edit

### 1. Check OAuth Callback in `cldashboard/routes/auth.py`

```python
@auth.route('/auth/discord/callback')
def discord_callback():
    # ... existing code ...
    # Check if there are any hardcoded redirect URLs here
```

### 2. Modify Discord Configuration in `cldashboard/__init__.py`

Look for the Discord OAuth2 setup and ensure it uses environment variables:

```python
# Discord setup
app.config["DISCORD_CLIENT_ID"] = os.getenv("DISCORD_CLIENT_ID")
app.config["DISCORD_CLIENT_SECRET"] = os.getenv("DISCORD_CLIENT_SECRET")
app.config["DISCORD_REDIRECT_URI"] = os.getenv("DISCORD_REDIRECT_URI")
app.config["DISCORD_BOT_TOKEN"] = os.getenv("DISCORD_BOT_TOKEN") 
```

### 3. Update `.env.local` for Local Testing

The `.env.local` file should have this configuration:
```
DISCORD_REDIRECT_URI=http://localhost:5000/auth/discord/callback
```

## Local Testing Procedure

1. **Start the Local Server**:
   ```bash
   python run_local.py
   ```

2. **Monitor Requests**:
   - Check the console output for redirect URLs
   - Watch for any hardcoded URLs in the application

3. **Discord Developer Portal Setup**:
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Add `http://localhost:5000/auth/discord/callback` as a redirect URI

## Debugging OAuth Flow

If still having issues:

1. **Temporary Debugging**:
   Add print statements in the auth routes to see what URLs are being used

2. **Check Session Storage**:
   Ensure the session is working properly locally

3. **Check Environment Variables**:
   Verify the environment variables are loaded correctly

## Switching Between Local and Production

When switching between local development and production deployment:

1. **Local Development**:
   - Use `run_local.py` which loads `.env.local`
   - Ensure Discord Developer Portal has local redirect URI

2. **Production Deployment**:
   - Use original `.env` file
   - Ensure Discord Developer Portal has production redirect URI 