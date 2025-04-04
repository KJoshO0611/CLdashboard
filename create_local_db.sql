-- Create base tables needed for the dashboard

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    discord_id BIGINT PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    discriminator VARCHAR(4),
    avatar VARCHAR(255),
    email VARCHAR(255),
    role JSONB DEFAULT '["user"]'::jsonb,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create guilds table
CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    icon VARCHAR(255),
    owner_id BIGINT -- Can be NULL if owner info isn't fetched/relevant
);

-- Create association table for dashboard access
CREATE TABLE IF NOT EXISTS user_guild (
    user_id BIGINT,
    guild_id BIGINT,
    PRIMARY KEY (user_id, guild_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_guild_members_guild_id ON guild_members(guild_id);
CREATE INDEX IF NOT EXISTS idx_guild_members_user_id ON guild_members(user_id);
CREATE INDEX IF NOT EXISTS idx_user_guild_user_id ON user_guild(user_id);
CREATE INDEX IF NOT EXISTS idx_user_guild_guild_id ON user_guild(guild_id);

-- Insert sample data

-- Sample user (developer account)
INSERT INTO users (discord_id, username, discriminator, avatar, role, created_at)
VALUES 
    (123456789012345678, 'TestUser', '1234', 'https://cdn.discordapp.com/embed/avatars/0.png', '["owner"]'::jsonb, NOW()),
    (234567890123456789, 'GuildOwner', '5678', 'https://cdn.discordapp.com/embed/avatars/1.png', '["user"]'::jsonb, NOW()),
    (345678901234567890, 'Member1', '4321', 'https://cdn.discordapp.com/embed/avatars/2.png', '["user"]'::jsonb, NOW()),
    (456789012345678901, 'Member2', '8765', 'https://cdn.discordapp.com/embed/avatars/3.png', '["user"]'::jsonb, NOW())
ON CONFLICT (discord_id) DO NOTHING;

-- Sample guilds
INSERT INTO guilds (guild_id, name, icon, owner_id, created_at)
VALUES 
    (111111111111111111, 'Test Server 1', 'https://cdn.discordapp.com/icons/111111111111111111/server1.png', 234567890123456789, NOW()),
    (222222222222222222, 'Test Server 2', 'https://cdn.discordapp.com/icons/222222222222222222/server2.png', 234567890123456789, NOW()),
    (333333333333333333, 'Development Server', 'https://cdn.discordapp.com/icons/333333333333333333/server3.png', 123456789012345678, NOW())
ON CONFLICT (guild_id) DO NOTHING;

-- Give dashboard access to the dev user for all servers
INSERT INTO user_guild (user_id, guild_id)
VALUES
    (123456789012345678, 111111111111111111),
    (123456789012345678, 222222222222222222),
    (123456789012345678, 333333333333333333),
    (234567890123456789, 111111111111111111),
    (234567890123456789, 222222222222222222),
    (234567890123456789, 333333333333333333)
ON CONFLICT (user_id, guild_id) DO NOTHING;

-- Now add your own Discord ID for testing (replace with your actual Discord ID)
-- INSERT INTO users (discord_id, username, discriminator, avatar, role, created_at)
-- VALUES (YOUR_DISCORD_ID, 'YourUsername', '0000', 'https://cdn.discordapp.com/embed/avatars/4.png', '["owner"]'::jsonb, NOW())
-- ON CONFLICT (discord_id) DO NOTHING;

-- INSERT INTO user_guild (user_id, guild_id)
-- VALUES
--     (YOUR_DISCORD_ID, 111111111111111111),
--     (YOUR_DISCORD_ID, 222222222222222222),
--     (YOUR_DISCORD_ID, 333333333333333333)
-- ON CONFLICT (user_id, guild_id) DO NOTHING; 