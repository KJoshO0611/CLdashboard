# Discord Bot Dashboard

A powerful web dashboard for Discord bots with user management, XP/leveling systems, and custom features based on role-based permissions.

## Features

- **Discord OAuth Integration**: Secure login via Discord OAuth2
- **Role-Based Access Control**:
  - Bot Owner: Full access to all functionality
  - Server Admin: Full access to their server settings
  - Server Moderator: Limited admin abilities (configurable)
  - Regular User: Can view their own stats and public data
- **Server Management**:
  - XP and leveling system
  - Role rewards
  - Custom achievements
  - Server events
  - Leaderboards
- **Admin Features**:
  - Global settings
  - User management
  - Bot statistics
  - Server monitoring
- **Customization**:
  - Channel settings
  - Command permissions
  - Prefix customization
  - Multilingual support

## Technology Stack

- **Backend**: Python with Flask
- **Database**: PostgreSQL (hosted on AWS EC2)
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5
- **Security**: Server-side sessions, CSRF protection, Discord OAuth
- **Deployment**: Render (or similar web hosting)

## Installation

### Prerequisites

- Python 3.9+
- PostgreSQL database
- Discord application with OAuth2 setup

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/discord-bot-dashboard.git
   cd discord-bot-dashboard
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Copy `.env.example` to `.env` and update with your values:
   ```bash
   cp .env.example .env
   ```

5. Initialize the database:
   ```bash
   flask shell
   >>> from cldashboard import db, create_app
   >>> app = create_app()
   >>> with app.app_context():
   >>>     db.create_all()
   >>> exit()
   ```

## Discord Application Setup

1. Create a Discord application at [Discord Developer Portal](https://discord.com/developers/applications)
2. Set up the OAuth2 redirect URI to `https://your-domain.com/auth/discord/callback`
3. Get the Client ID, Client Secret, and Bot Token for your `.env` file

## Running the Application

### Development

```bash
# Run the development server
flask run --debug
```

### Production

For production deployment, use Gunicorn:

```bash
gunicorn 'app:app' --bind 0.0.0.0:8000
```

## Deployment on Render

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Use the following settings:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Add Environment Variables**: Add all variables from your `.env` file

## Connecting to AWS EC2 PostgreSQL

1. Create an EC2 instance with PostgreSQL
2. Configure your security groups to allow traffic from your web app
3. Update the `DATABASE_URL` in your environment variables

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Discord API
- Flask framework
- Bootstrap 5
- All the contributors who have helped to improve this project 