"""
Local development server script.
DO NOT USE IN PRODUCTION - This file is for local development only.
On Render, the application is served by Gunicorn using the production config.
"""

from cldashboard import create_app

app = create_app()

if __name__ == '__main__':
    print("Starting local development server...")
    print("WARNING: This script is for local testing only. Do not use in production.")
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    ) 