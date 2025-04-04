"""
Local development server script with local environment variables.
"""
import os
from dotenv import load_dotenv
from cldashboard import create_app

# Load local environment variables
if os.path.exists('.env.local'):
    load_dotenv('.env.local')
else:
    load_dotenv()

app = create_app()

if __name__ == '__main__':
    print("Starting local development server...")
    print(f"Access the site at: http://localhost:5000")
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    ) 