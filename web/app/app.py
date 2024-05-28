import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import json
import redis
import os
import re

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

# Get current directory
current_dir = os.path.dirname(os.path.realpath(__file__))
static_dir = os.path.join(current_dir, "static")

# Ensure static directory exists
os.makedirs(static_dir, exist_ok=True)

print(f"Current directory: {current_dir}")

# Load config.json
with open(os.path.join(current_dir, "../../config.json")) as f:
    config = json.load(f)

@app.route("/")
def index():
    return render_template("index.html", data=config)

@app.route("/config")
def get_config():
    return jsonify(config)

@app.route("/send", methods=['POST'])
def send_message():
    r = redis.Redis(host='localhost', port=6379)
    data = request.json
    message = data.get('message')
    category = data.get('category')
    
    print(f"Data received: {data}")

    if not message:
        return jsonify({"error": "Message content is required"}), 400

    # Extract media links and Tenor GIFs
    media_links = extract_media_links(message)
    tenor_gifs = extract_tenor_gifs(message)

    message_payload = {
        "embed": {
            "description": message,
            "media_paths": media_links if media_links else [],  # Ensure media_paths is always a list
            "tenor_gifs": tenor_gifs if tenor_gifs else [],    # Ensure tenor_gifs is always a list
            "color": 0x32CD32,
            "author": {
                "name": "Wormhole Operator",
                "icon_url": "https://images-ext-1.discordapp.net/external/htCkg7phTr6Hvlf_vFRQsX9eYLFSvTHTQzFSTP9paKM/%3Fsize%3D4096/https/cdn.discordapp.com/avatars/562526615062577152/ee560da01a95c667dd2eb614f3812b41.png?format=webp&quality=lossless&width=50&height=50",
            }
        },
        "category": category  # You can change the category dynamically if needed
    }

    r.publish('wormhole_channel', json.dumps(message_payload))
    return jsonify({"message": "Message sent successfully"})

def extract_media_links(text):
    media_regex = r'(https?:\/\/[^\s]+\.(?:png|jpg|gif|mp4)(?:\?[^\s]*)?)'
    return re.findall(media_regex, text)

def extract_tenor_gifs(text):
    tenor_regex = r'https:\/\/tenor\.com\/view\/[a-zA-Z0-9\-]+\-gif-(\d+)'
    return re.findall(tenor_regex, text)

def listen_to_redis():
    print("Listening to Redis")
    r = redis.Redis(host='localhost', port=6379)
    pubsub = r.pubsub()
    pubsub.subscribe('tox_node')

    for message in pubsub.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'].decode('utf-8'))
            print(f"Received message: {data}")
            description = data['embed'].get('description', ' ')
            media_links = extract_media_links(data["message"])
            tenor_gifs = extract_tenor_gifs(data["message"])
            data['embed']['media_paths'] = media_links if media_links else []
            data['embed']['tenor_gifs'] = tenor_gifs if tenor_gifs else []

            socketio.emit('message', json.dumps(data))
            print("Emitted message to clients")

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == "__main__":
    # Run the Redis listener in a separate thread using eventlet
    eventlet.spawn(listen_to_redis)

    # Start the SocketIO server
    socketio.run(app, debug=True, host='localhost')
