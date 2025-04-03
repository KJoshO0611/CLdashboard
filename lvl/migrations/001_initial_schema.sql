-- Create users table
CREATE TABLE IF NOT EXISTS users (
    discord_id BIGINT PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    avatar VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create guilds table
CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    icon VARCHAR(255),
    owner_id BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create guild_members table
CREATE TABLE IF NOT EXISTS guild_members (
    guild_id BIGINT REFERENCES guilds(guild_id),
    user_id BIGINT REFERENCES users(discord_id),
    level INTEGER DEFAULT 1,
    xp INTEGER DEFAULT 0,
    last_xp_gain TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (guild_id, user_id)
);

-- Create achievements table
CREATE TABLE IF NOT EXISTS achievements (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT REFERENCES guilds(guild_id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    requirement_type VARCHAR(50) NOT NULL,
    requirement_value INTEGER NOT NULL,
    icon_path VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create user_achievements table
CREATE TABLE IF NOT EXISTS user_achievements (
    user_id BIGINT REFERENCES users(discord_id),
    achievement_id INTEGER REFERENCES achievements(id),
    guild_id BIGINT REFERENCES guilds(guild_id),
    progress INTEGER DEFAULT 0,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (user_id, achievement_id, guild_id)
);

-- Create events table
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT REFERENCES guilds(guild_id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    event_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'upcoming',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create event_participants table
CREATE TABLE IF NOT EXISTS event_participants (
    event_id INTEGER REFERENCES events(id),
    user_id BIGINT REFERENCES users(discord_id),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (event_id, user_id)
); 