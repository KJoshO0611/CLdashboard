# Local Development Database Setup

This guide explains how to set up a local database for development with the necessary sample data.

## Prerequisites

- PostgreSQL installed and running
- Python 3.6+
- psycopg2 package (`pip install psycopg2-binary`)
- python-dotenv package (`pip install python-dotenv`)

## Setup Steps

1. Make sure PostgreSQL is running on your machine
2. Create a new database in PostgreSQL (e.g., `lvlbot`)
3. Update your `.env` file to include the database connection string:

```
DATABASE_URL=postgresql://username:password@localhost:5432/lvlbot
```

Replace `username`, `password`, and `lvlbot` with your PostgreSQL credentials and database name.

## Running the Setup Script

### Basic Setup

Run the following command to create tables and populate them with sample data:

```
python setup_local_db.py
```

### Adding Your Own Discord Account

If you want to include your own Discord account for testing:

```
python setup_local_db.py YOUR_DISCORD_ID YOUR_USERNAME
```

For example:
```
python setup_local_db.py 123456789012345678 "John Doe"
```

This will add your Discord account to the database and grant it access to all test servers.

## What Gets Created

The setup script creates the following:

1. **Tables**:
   - users
   - guilds
   - guild_members 
   - user_guild (association table)

2. **Sample Data**:
   - 4 sample users
   - 3 sample Discord servers (guilds)
   - Guild membership data with varying XP levels
   - Dashboard access permissions

## Manual Database Inspection

You can connect to your local database using any PostgreSQL client:

```
psql -U your_username -d lvlbot
```

Example queries:
```sql
-- List all users
SELECT * FROM users;

-- List all guilds 
SELECT * FROM guilds;

-- Show XP progression
SELECT u.username, g.name, gm.level, gm.xp 
FROM guild_members gm
JOIN users u ON gm.user_id = u.discord_id
JOIN guilds g ON gm.guild_id = g.guild_id
ORDER BY g.name, gm.level DESC;
```

## Troubleshooting

If you encounter any issues:

1. Verify PostgreSQL is running
2. Check your database connection string
3. Make sure you have appropriate permissions to create tables
4. Ensure you have installed the required Python packages 