import asyncio
from datetime import datetime
import hashlib
import json
import math
import time
from typing import Dict, List, Optional
from functools import wraps

import asyncpg
import dotenv
import os
import re

dotenv.load_dotenv()

def auto_configure_user(func):
    @wraps(func)
    async def wrapper(self, user_id: str, *args, **kwargs):
        await self.get_user(user_id)
        return await func(self, user_id, *args, **kwargs)
    return wrapper

def classify_user_id(user_id):
    if not isinstance(user_id, str):
        return "Invalid: Not a string"
    
    try:
        int(user_id)
        return "Digit"
    except ValueError:
        if re.match(r'^[a-fA-F0-9]{64}$', user_id):
            return "SHA256 hash"
        else:
            return "Other"

class WormholeConfig:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        self.global_salt = os.getenv("global_salt") or "else your cluster is compromised"
        self.pool = None

    async def initialize(self):
        self.pool = await asyncpg.create_pool(self.db_url)

    # User Management
    # ---------------

    async def get_user(self, user_id: str) -> Dict:
        async with self.pool.acquire() as conn:
            user = await conn.fetchrow(
                """
                SELECT * FROM Users WHERE user_id = $1
                """,
                user_id
            )
            if not user:
                user_hash = await self.compute_user_hash(user_id)
                user = await conn.fetchrow(
                    """
                    INSERT INTO Users (user_id, hash) VALUES ($1, $2)
                    ON CONFLICT (user_id) DO UPDATE SET hash = $2
                    RETURNING *
                    """,
                    user_id, user_hash
                )
            return dict(user)

    async def get_user_usernames(self, user_id: str) -> List[str]:
        async with self.pool.acquire() as conn:
            usernames = await conn.fetch(
                """
                SELECT name FROM Usernames WHERE user_id = $1
                """,
                user_id
            )
            return usernames

    async def update_user_config(self, user_id: str, **kwargs):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE Users SET 
                    role = COALESCE($1, role),
                    profile_picture = COALESCE($2, profile_picture),
                    difficulty = COALESCE($3, difficulty),
                    difficulty_penalty = COALESCE($4, difficulty_penalty),
                    can_send_message = COALESCE($5, can_send_message)
                WHERE user_id = $6
                """,
                kwargs.get('role'),
                kwargs.get('profile_picture'),
                kwargs.get('difficulty'),
                kwargs.get('difficulty_penalty'),
                kwargs.get('can_send_message'),
                user_id
            )

    async def get_user_by_hash(self, user_hash: str) -> Dict:
        async with self.pool.acquire() as conn:
            if classify_user_id(user_hash) == "Digit":
                user_hash = hashlib.sha256(f"{self.global_salt}{user_hash}".encode()).hexdigest()
            user = await conn.fetchrow(
                """
                SELECT * FROM Users 
                WHERE hash LIKE $1 || '%'
                ORDER BY LENGTH(hash)
                LIMIT 1
                """,
                user_hash
            )
            return dict(user) if user else {}

    async def get_user_id_by_hash(self, user_hash: str) -> Optional[str]:
        async with self.pool.acquire() as conn:
            user_id = await conn.fetchval(
                """
                SELECT user_id FROM Users 
                WHERE hash LIKE $1 || '%'
                ORDER BY LENGTH(hash)
                LIMIT 1
                """,
                user_hash
            )
            return user_id
    
    async def get_user_hash_by_id(self, user_id: str) -> Optional[str]:
        async with self.pool.acquire() as conn:
            user_hash = await conn.fetchval(
                """
                SELECT hash FROM Users WHERE user_id = $1
                """,
                user_id
            )
            return user_hash
    
    async def get_user_hash(self, user_id: str) -> str:
        user = await self.get_user(user_id)
        return user['hash']

    async def change_user_role(self, user_hash: str, role: str) -> None:
        async with self.pool.acquire() as conn:
            if classify_user_id(user_hash) == "Digit":
                user_hash = hashlib.sha256(f"{self.global_salt}{user_hash}".encode()).hexdigest()

            await conn.execute(
                """
                UPDATE Users SET role = $1 WHERE user_id = (
                    SELECT user_id FROM Users 
                    WHERE hash LIKE $2 || '%'
                    ORDER BY LENGTH(hash)
                    LIMIT 1
                )
                """,
                role, user_hash
            )

    async def add_username(self, user_id: str, name: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO Usernames (user_id, name) VALUES ($1, $2)
                ON CONFLICT (user_id, name) DO NOTHING
                """,
                user_id, name
            )

    async def is_user_banned(self, user_id: str) -> bool:
        async with self.pool.acquire() as conn:
            is_banned = await conn.fetchval(
                """
                SELECT EXISTS(SELECT 1 FROM BannedUsers WHERE user_id = $1)
                """,
                user_id
            )
            
            is_banned_2 = False
            if not is_banned:
                user_id = await self.get_user_id_by_hash(user_id)
                is_banned_2 = await conn.fetchval(
                    """
                    SELECT EXISTS(SELECT 1 FROM BannedUsers WHERE user_id = $1)
                    """,
                    user_id
                )
            return is_banned or is_banned_2

    async def ban_user(self, user_id: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO BannedUsers (user_id) VALUES ($1)
                ON CONFLICT (user_id) DO NOTHING
                """,
                user_id
            )

    async def unban_user(self, user_id: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM BannedUsers WHERE user_id = $1
                """,
                user_id
            )
    
    async def update_user_avatar(self, user_id: str, avatar: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE Users SET profile_picture = $1 WHERE user_id = $2
                """,
                avatar, user_id
            )

    async def user_exists(self, user_id: str) -> bool:
        async with self.pool.acquire() as conn:
            user = await conn.fetchval(
                """
                SELECT EXISTS(SELECT 1 FROM Users WHERE hash LIKE $1 || '%')
                ORDER BY LENGTH(hash)
                LIMIT 1
                """,
                user_id
            )
            
            user2 = False
            if classify_user_id(user_id) == "Digit":
                user_hash = hashlib.sha256(f"{self.global_salt}{user_id}".encode()).hexdigest()
                user2 = await conn.fetchval(
                    """
                    SELECT EXISTS(SELECT 1 FROM Users WHERE hash = $1)
                    """,
                    user_hash
                )
            return user or user2

    # Message and Attachment History
    # ------------------------------

    def hash_message(self, user_hash, message_content, nonce):
        return hashlib.sha256((self.global_salt + user_hash + message_content + str(nonce)).encode()).hexdigest()

    @auto_configure_user
    async def update_user_message_history(self, user_id: str, message_link: str, message_hash: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO MessageHistory (hash, message_link, user_id, timestamp)
                VALUES ($1, ARRAY[$2], $3, $4)
                ON CONFLICT (hash) DO NOTHING
                """,
                message_hash, message_link, user_id, time.time()
            )

    async def append_link(self, message_hash: str, message_links: list):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE MessageHistory 
                SET message_link = array_cat(message_link, $1::varchar[])
                WHERE hash = $2
                """,
                message_links, message_hash
            )

    async def add_attachment_history(self, user_id: str, attachment_link: str):
        async with self.pool.acquire() as conn:
            hashed_content = hashlib.sha256((self.global_salt + user_id + attachment_link).encode()).hexdigest()
            await conn.execute(
                """
                INSERT INTO AttachmentHistory (hash, attachment_link, user_id, timestamp)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (hash) DO NOTHING
                """,
                hashed_content, attachment_link, user_id, time.time()
            )

    async def add_data(self, hash: str, predicted: str, actual: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO dataset (id, predicted, actual)
                VALUES ($1, $2, $3)
                ON CONFLICT (id) DO UPDATE SET
                predicted = $2,
                actual = $3
                """,
                hash, predicted, actual
            )

    async def get_message_hash_by_link(self, message_link):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                SELECT hash FROM MessageHistory
                WHERE $1 = ANY(message_link)
                """,
                message_link
            )

    async def get_message_links(self, message_hash):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                SELECT message_link FROM MessageHistory
                WHERE hash = $1
                """,
                message_hash
            )

    @staticmethod
    def parse_message_link(link):
        parts = link.split('/')
        return parts[-2], parts[-1]

    # Channel Management
    # ------------------

    async def add_channel(self, channel_name: str, channel_id: str, server_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO Channels (channel_id, server_id, channel_category)
                VALUES ($1, $2, $3)
                ON CONFLICT (channel_id) DO UPDATE SET
                    server_id = $2,
                    channel_category = $3
                """,
                channel_id, server_id, channel_name
            )
            
    async def remove_channel(self, channel_id: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM Channels WHERE channel_id = $1
                """,
                channel_id
            )
    
    async def join_channel(self, channel_name: str, channel_id: str, server_id: str) -> bool:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO Channels (channel_id, channel_category, server_id)
                VALUES ($1, $2, $3)
                ON CONFLICT (channel_id) DO NOTHING
                """,
                channel_id, channel_name, server_id
            )
            return True
    
    async def leave_channel(self, channel_id: str) -> bool:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM Channels WHERE channel_id = $1
                """,
                channel_id
            )
            return True
    
    async def get_channel_category_by_id(self, channel_id: str) -> Optional[str]:
        async with self.pool.acquire() as conn:
            channel = await conn.fetchval(
                """
                SELECT channel_category FROM Channels WHERE channel_id = $1
                """,
                channel_id
            )
            return channel

    async def get_channel_by_id(self, channel_id: str) -> Dict:
        async with self.pool.acquire() as conn:
            channel = await conn.fetchrow(
                """
                SELECT * FROM Channels WHERE channel_id = $1
                """,
                channel_id
            )
            return dict(channel) if channel else None

    async def get_channel_name_by_id(self, channel_id: str) -> Optional[str]:
        async with self.pool.acquire() as conn:
            channel = await conn.fetchval(
                """
                SELECT channel_category FROM Channels WHERE channel_id = $1
                """,
                channel_id
            )
            return channel

    async def get_all_channels(self) -> List[Dict]:
        async with self.pool.acquire() as conn:
            channels = await conn.fetch(
                """
                SELECT * FROM ChannelList
                """
            )
            return [dict(channel) for channel in channels]

    async def channel_exists(self, channel_id: str) -> bool:
        async with self.pool.acquire() as conn:
            channel = await conn.fetchval(
                """
                SELECT EXISTS(SELECT 1 FROM Channel WHERE channel_id = $1)
                """,
                channel_id
            )
            return channel

    async def category_exists(self, category: str) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                """
                SELECT EXISTS(SELECT 1 FROM ChannelList WHERE channel_name = $1)
                """,
                category
            )
            return result

    async def get_channels_by_category(self, category: str) -> List[Dict]:
        async with self.pool.acquire() as conn:
            channels = await conn.fetch(
                """
                SELECT * FROM Channels WHERE channel_category = $1
                """,
                category
            )
            return [dict(channel) for channel in channels]
    
    async def get_all_channels_in_category_by_id(self, channel_id: str) -> List[str]:
        async with self.pool.acquire() as conn:
            channels = await conn.fetch(
                """
                SELECT channel_id FROM Channels WHERE channel_category = (
                    SELECT channel_category FROM Channels WHERE channel_id = $1
                )
                """,
                channel_id
            )
            return [channel['channel_id'] for channel in channels]

    # Server Management
    # -----------------

    async def add_server(self, server_id: int, server_name: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO Servers (server_id, server_name)
                VALUES ($1, $2)
                ON CONFLICT (server_id) DO UPDATE SET server_name = $2
                """,
                server_id, server_name
            )

    async def get_server(self, server_id: int) -> Dict:
        async with self.pool.acquire() as conn:
            server = await conn.fetchrow(
                """
                SELECT * FROM Servers WHERE server_id = $1
                """,
                server_id
            )
            return dict(server) if server else None

    async def is_server_banned(self, server_id: int) -> bool:
        async with self.pool.acquire() as conn:
            is_banned = await conn.fetchval(
                """
                SELECT COUNT(*) FROM BannedServers WHERE server_id = $1
                """,
                server_id
            )
            return is_banned > 0

    async def ban_server(self, server_id: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO BannedServers (server_id) VALUES ($1)
                ON CONFLICT (server_id) DO NOTHING
                """,
                server_id
            )

    async def unban_server(self, server_id: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM BannedServers WHERE server_id = $1
                """,
                server_id
            )

    # Role Management
    # ---------------

    async def get_user_color(self, user_id: str) -> int:
        async with self.pool.acquire() as conn:
            user = await self.get_user(user_id)
            role = await conn.fetchrow(
                """
                SELECT color FROM Roles WHERE name = $1
                """,
                user['role']
            )
            return int(role['color'][1:], 16) if role else 0

    async def get_role_color(self, role: str) -> int:
        async with self.pool.acquire() as conn:
            role_data = await conn.fetchrow(
                """
                SELECT color FROM Roles WHERE name = $1
                """,
                role
            )
            return int(role_data['color'][1:], 16) if role_data else 0

    async def get_user_role(self, user_id: str) -> str:
        async with self.pool.acquire() as conn:
            if classify_user_id(user_id) != "Digit":
                user_id = await self.get_user_id_by_hash(user_id)
            role = await conn.fetchval(
                """
                SELECT role FROM Users WHERE user_id = $1
                """,
                user_id
            )
            return role

    # Utility Functions
    # -----------------

    async def compute_user_hash(self, user_id: str) -> str:
        return hashlib.sha256(f"{self.global_salt}{user_id}".encode()).hexdigest()

    async def update_user_nonce(self, user_id: str, nonce: int):
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE Users SET nonce = $1 WHERE user_id = $2
                    """,
                    nonce, user_id
            )

    # Admin Management
    # ----------------

    async def add_admin(self, user_id: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO Admins (user_id) VALUES ($1)
                ON CONFLICT (user_id) DO NOTHING
                """,
                user_id
            )

    async def remove_admin(self, user_id: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM Admins WHERE user_id = $1
                """,
                user_id
            )

    async def is_admin(self, user_id: str) -> bool:
        async with self.pool.acquire() as conn:
            is_admin = await conn.fetchval(
                """
                SELECT COUNT(*) FROM Admins WHERE user_id = $1
                """,
                user_id
            )
            return is_admin > 0

    # Channel List Management
    # -----------------------

    async def add_channel_to_list(self, channel_name: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO ChannelList (channel_name) VALUES ($1)
                ON CONFLICT (channel_name) DO NOTHING
                """,
                channel_name
            )

    async def remove_channel_from_list(self, channel_name: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM ChannelList WHERE channel_name = $1
                """,
                channel_name
            )

    async def get_channel_list(self) -> List[str]:
        async with self.pool.acquire() as conn:
            channels = await conn.fetch(
                """
                SELECT channel_name FROM ChannelList
                """
            )
            return [channel['channel_name'] for channel in channels]

    # React Feature Management
    # ------------------------

    async def set_channel_react(self, channel_id: str, react: bool) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE Channels SET react = $1 WHERE channel_id = $2
                """,
                react, channel_id
            )

    async def get_channel_react(self, channel_id: str) -> bool:
        async with self.pool.acquire() as conn:
            react = await conn.fetchval(
                """
                SELECT react FROM Channels WHERE channel_id = $1
                """,
                channel_id
            )
            return react if react is not None else False

    # Batch Operations
    # ----------------

    async def get_all_users(self) -> List[Dict]:
        async with self.pool.acquire() as conn:
            users = await conn.fetch(
                """
                SELECT * FROM Users
                """
            )
            return [dict(user) for user in users]

    async def get_all_banned_users(self) -> List[str]:
        async with self.pool.acquire() as conn:
            banned_users = await conn.fetch(
                """
                SELECT user_id FROM BannedUsers
                """
            )
            return [user['user_id'] for user in banned_users]

    async def get_all_banned_servers(self) -> List[int]:
        async with self.pool.acquire() as conn:
            banned_servers = await conn.fetch(
                """
                SELECT server_id FROM BannedServers
                """
            )
            return [server['server_id'] for server in banned_servers]

    # Statistics and Analytics
    # ------------------------

    async def get_user_message_count(self, user_id: str, time_range: Optional[int] = None) -> int:
        async with self.pool.acquire() as conn:
            if time_range:
                count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM MessageHistory
                    WHERE user_id = $1 AND timestamp > $2
                    """,
                    user_id, time.time() - time_range
                )
            else:
                count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM MessageHistory
                    WHERE user_id = $1
                    """,
                    user_id
                )
            return count

    async def get_active_users(self, time_range: int) -> List[Dict]:
        async with self.pool.acquire() as conn:
            active_users = await conn.fetch(
                """
                SELECT user_id, COUNT(*) as message_count
                FROM MessageHistory
                WHERE timestamp > $1
                GROUP BY user_id
                ORDER BY message_count DESC
                LIMIT 10
                """,
                time.time() - time_range
            )
            return [dict(user) for user in active_users]

    async def get_channel_activity(self, channel_id: str, time_range: Optional[int] = None) -> int:
        async with self.pool.acquire() as conn:
            if time_range:
                count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM MessageHistory
                    WHERE message_link LIKE $1 AND timestamp > $2
                    """,
                    f"%{channel_id}%", time.time() - time_range
                )
            else:
                count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM MessageHistory
                    WHERE message_link LIKE $1
                    """,
                    f"%{channel_id}%"
                )
            return count

    # Cleanup and Maintenance
    # -----------------------

    async def clear_old_messages(self, days: int) -> int:
        async with self.pool.acquire() as conn:
            deleted = await conn.fetchval(
                """
                DELETE FROM MessageHistory
                WHERE timestamp < $1
                RETURNING COUNT(*)
                """,
                time.time() - (days * 24 * 60 * 60)
            )
            return deleted

    async def optimize_database(self):
        async with self.pool.acquire() as conn:
            await conn.execute("VACUUM ANALYZE")

    # Configuration Management
    # ------------------------

    async def get_database_size(self) -> int:
        async with self.pool.acquire() as conn:
            size = await conn.fetchval(
                """
                SELECT pg_database_size(current_database())
                """
            )
            return size

# Additional utility functions outside the class

async def create_tables(pool):
    async with pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS Users (
                user_id VARCHAR(255) PRIMARY KEY,
                hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) DEFAULT 'user',
                profile_picture VARCHAR(255),
                difficulty FLOAT DEFAULT 0,
                difficulty_penalty FLOAT DEFAULT 0,
                can_send_message BOOLEAN DEFAULT TRUE,
                nonce INT DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS Channels (
                channel_id VARCHAR(255) PRIMARY KEY,
                server_id INT NOT NULL,
                channel_category VARCHAR(255) NOT NULL,
                react BOOLEAN DEFAULT FALSE
            );

            CREATE TABLE IF NOT EXISTS Usernames (
                user_id VARCHAR(255) PRIMARY KEY,
                name VARCHAR(255),
                FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS MessageHistory (
                hash VARCHAR(255) NOT NULL PRIMARY KEY,
                message_link VARCHAR(255),
                user_id VARCHAR(255),
                timestamp FLOAT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS AttachmentHistory (
                hash VARCHAR(255) NOT NULL PRIMARY KEY,
                attachment_link VARCHAR(255),
                user_id VARCHAR(255),
                timestamp FLOAT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS TempCommandMessageHistory (
                message_id SERIAL PRIMARY KEY,
                user_id VARCHAR(255),
                content TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS Roles (
                name VARCHAR(50) PRIMARY KEY,
                color VARCHAR(7) NOT NULL
            );

            CREATE TABLE IF NOT EXISTS Admins (
                user_id VARCHAR(255) PRIMARY KEY,
                FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS Servers (
                server_id INT PRIMARY KEY,
                server_name VARCHAR(255) NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ChannelList (
                channel_name VARCHAR(255) PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS BannedServers (
                server_id INT PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS BannedUsers (
                user_id VARCHAR(255) PRIMARY KEY
            );

        ''')

async def initialize_database(config: WormholeConfig):
    await config.initialize()
    await create_tables(config.pool)

    # Initialize roles
    async with config.pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO Roles (name, color) VALUES ('admin', '#FF0000'), ('user', '#0000FF')
            ON CONFLICT (name) DO NOTHING
        ''')
        
        # Create users
        jush = await config.compute_user_hash('706702251812716595')
        jush_2 = await config.compute_user_hash('1190028762998378627')
        gary = await config.compute_user_hash('1183924794593378360')
        
        await conn.execute('''
            INSERT INTO Users (user_id, hash, role) VALUES ('706702251812716595', $1, 'admin')
            ON CONFLICT (user_id) DO UPDATE SET role = 'admin'
        ''', jush)
        await conn.execute('''
            INSERT INTO Users (user_id, hash, role) VALUES ('1190028762998378627', $1, 'admin')
            ON CONFLICT (user_id) DO UPDATE SET role = 'admin'
        ''', jush_2)
        await conn.execute('''
            INSERT INTO Users (user_id, hash, role) VALUES ('1183924794593378360', $1, 'admin')
            ON CONFLICT (user_id) DO UPDATE SET role = 'admin'
        ''', gary)
        
        await conn.execute('''
            INSERT INTO Admins (user_id) 
            VALUES 
                ('706702251812716595'),
                ('1190028762998378627'),
                ('1183924794593378360')
            ON CONFLICT (user_id) DO NOTHING
        ''')

        # Initialize channel list
        channel_list = ['general', 'wormhole', 'happenings', 'qotd', 'memes', 'computers', 'finance', 'music', 'cats', 'spam-can', 'test']
        for channel in channel_list:
            await conn.execute('''
                INSERT INTO ChannelList (channel_name) VALUES ($1)
                ON CONFLICT (channel_name) DO NOTHING
            ''', channel)

if __name__ == "__main__":
    config = WormholeConfig()
    asyncio.run(initialize_database(config))
