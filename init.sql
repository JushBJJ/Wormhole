-- Create Channels table
CREATE TABLE Channels (
    channel_id VARCHAR(255) PRIMARY KEY,
    server_id VARCHAR(255) NOT NULL,
    channel_category VARCHAR(255) NOT NULL,
    react BOOLEAN DEFAULT FALSE
);

-- Create Users table
CREATE TABLE Users (
    hash VARCHAR(255) NOT NULL PRIMARY KEY,
    user_id VARCHAR(255) DEFAULT '0' UNIQUE,
    role VARCHAR(50) DEFAULT 'user',
    profile_picture VARCHAR(255),
    difficulty FLOAT DEFAULT 0,
    difficulty_penalty FLOAT DEFAULT 0,
    can_send_message BOOLEAN DEFAULT TRUE,
    nonce INT DEFAULT 0
);

-- Create Usernames table
CREATE TABLE Usernames (
    id SERIAL PRIMARY KEY NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
    UNIQUE (user_id, name)
);

-- Create MessageHistory table
CREATE TABLE MessageHistory (
    hash VARCHAR(255) NOT NULL PRIMARY KEY,
    message_link VARCHAR(255)[],
    user_id VARCHAR(255),
    timestamp FLOAT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- Create AttachmentHistory table
CREATE TABLE AttachmentHistory (
    hash VARCHAR(255) NOT NULL PRIMARY KEY,
    attachment_link VARCHAR(255),
    user_id VARCHAR(255),
    timestamp FLOAT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- Create dataset table
CREATE TABLE dataset (
    id VARCHAR(255) PRIMARY KEY,
    predicted TEXT,
    actual TEXT
);

-- Create Roles table
CREATE TABLE Roles (
    name VARCHAR(50) PRIMARY KEY,
    color VARCHAR(7) NOT NULL
);

-- Create Admins table
CREATE TABLE Admins (
    user_id VARCHAR(255) PRIMARY KEY,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- Create Servers table
CREATE TABLE Servers (
    server_id INT PRIMARY KEY,
    server_name VARCHAR(255) NOT NULL
);

-- Create ChannelList table
CREATE TABLE ChannelList (
    channel_name VARCHAR(255) PRIMARY KEY
);

-- Create BannedServers table
CREATE TABLE BannedServers (
    server_id INT PRIMARY KEY
);

-- Create BannedUsers table
CREATE TABLE BannedUsers (
    user_id VARCHAR(255) PRIMARY KEY
);

-- Insert default roles
INSERT INTO Roles (name, color) VALUES 
('admin', '#FF0000'),
('user', '#0000FF')
ON CONFLICT (name) DO NOTHING;

-- Insert default channel names
INSERT INTO ChannelList (channel_name) VALUES 
('general'), 
('wormhole'), 
('happenings'), 
('qotd'), 
('memes'), 
('computers'), 
('finance'), 
('music'), 
('cats'), 
('spam-can'), 
('test')
ON CONFLICT (channel_name) DO NOTHING;