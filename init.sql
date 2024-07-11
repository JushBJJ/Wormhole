CREATE TABLE Channels (
    channel_id VARCHAR(255) PRIMARY KEY,
    server_id VARCHAR(255) NOT NULL,
    channel_category VARCHAR(255) NOT NULL,
    react BOOLEAN DEFAULT FALSE
);

CREATE TABLE Users (
    hash VARCHAR(255) NOT NULL PRIMARY KEY,
    user_id VARCHAR(255) DEFAULT 0,
    role VARCHAR(50) DEFAULT 'user',
    profile_picture VARCHAR(255),
    difficulty FLOAT DEFAULT 0,
    difficulty_penalty FLOAT DEFAULT 0,
    can_send_message BOOLEAN DEFAULT TRUE,
    nonce INT DEFAULT 0
);

CREATE TABLE Usernames (
    user_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

CREATE TABLE MessageHistory (
    hash VARCHAR(255) NOT NULL PRIMARY KEY,
    message_link VARCHAR(255)[],
    user_id VARCHAR(255),
    timestamp FLOAT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

CREATE TABLE AttachmentHistory (
    hash VARCHAR(255) NOT NULL PRIMARY KEY,
    attachment_link VARCHAR(255),
    user_id VARCHAR(255),
    timestamp FLOAT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

CREATE TABLE TempCommandMessageHistory (
    message_id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    content TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

CREATE TABLE Roles (
    name VARCHAR(50) NOT NULL PRIMARY,
    color VARCHAR(7) NOT NULL
);

CREATE TABLE Admins (
    user_id INT PRIMARY KEY,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

CREATE TABLE Servers (
    server_id INT PRIMARY KEY,
    server_name VARCHAR(255) NOT NULL,
);

CREATE TABLE ChannelList (
    channel_name VARCHAR(255) PRIMARY KEY
);

CREATE TABLE BannedServers (
    server_id INT PRIMARY KEY
);

CREATE TABLE BannedUsers (
    user_id VARCHAR(255) PRIMARY KEY
);

INSERT INTO Roles (name, color) VALUES ('admin', '#FF0000') 
ON CONFLICT (name) DO NOTHING;

INSERT INTO Roles (name, color) VALUES ('user', '#0000FF') 
ON CONFLICT (name) DO NOTHING;

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
