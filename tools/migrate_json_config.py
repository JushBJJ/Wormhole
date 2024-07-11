import json
import os
import psycopg2
from psycopg2.extras import Json

from dotenv import load_dotenv
load_dotenv()

DB_PARAMS = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

def connect_to_db():
    return psycopg2.connect(**DB_PARAMS)

def migrate_json_to_postgresql(json_file_path):
    with open(json_file_path, 'r') as file:
        data = json.load(file)

    conn = connect_to_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO wormhole_config (admins, servers, channel_list, banned_servers, banned_users, banned_words, max_difficulty)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            data.get('admins', []),
            data.get('servers', []),
            data.get('channel_list', []),
            data.get('banned_servers', []),
            data.get('banned_users', []),
            data.get('banned_words', []),
            data.get('max_difficulty', 10)
        ))

        cur.execute("""
            INSERT INTO content_filter (enabled, sensitivity)
            VALUES (%s, %s)
        """, (
            data['content_filter']['enabled'],
            data['content_filter']['sensitivity']
        ))

        for channel_name, channel_data in data.get('channels', {}).items():
            for channel_id, channel_config in channel_data.items():
                cur.execute("""
                    INSERT INTO channels (channel_id, name, react)
                    VALUES (%s, %s, %s)
                """, (
                    int(channel_id),
                    channel_name,
                    channel_config.get('react', False)
                ))

        for role_name, role_data in data.get('roles', {}).items():
            cur.execute("""
                INSERT INTO roles (name, color, permissions)
                VALUES (%s, %s, %s)
            """, (
                role_name,
                role_data['color'],
                role_data.get('permissions', [])
            ))

        for user_id, user_data in data.get('users', {}).items():
            cur.execute("""
                INSERT INTO users (discord_id, hash, role, names, profile_picture, difficulty, difficulty_penalty, can_send_message, nonce)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                int(user_id),
                user_data['hash'],
                user_data['role'],
                user_data.get('names', []),
                user_data.get('profile_picture', ''),
                user_data.get('difficulty', 0),
                user_data.get('difficulty_penalty', 0),
                user_data.get('can_send_message', True),
                user_data.get('nonce', 0)
            ))

            cur.execute("SELECT id FROM users WHERE discord_id = %s", (int(user_id),))
            user_db_id = cur.fetchone()[0]

            for msg in user_data.get('message_history', []):
                cur.execute("""
                    INSERT INTO message_history (user_id, timestamp, hash)
                    VALUES (%s, %s, %s)
                """, (
                    user_db_id,
                    msg['timestamp'],
                    msg['hash']
                ))

            for msg in user_data.get('temp_command_message_history', []):
                cur.execute("""
                    INSERT INTO temp_command_message_history (user_id, role, content)
                    VALUES (%s, %s, %s)
                """, (
                    user_db_id,
                    msg['role'],
                    msg['content']
                ))

        conn.commit()
        print("Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"An error occurred during migration: {e}")

    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    json_file_path = "config.json"
    migrate_json_to_postgresql(json_file_path)