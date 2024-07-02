import redis
import json
from bot.config import WormholeConfig
from bot.utils.logging import setup_logging

class ToxService:
    def __init__(self, config: WormholeConfig):
        self.config = config
        self.logger = setup_logging()
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.pubsub = self.redis_client.pubsub()

    async def start(self):
        self.logger.info("Starting Tox service")
        self.pubsub.subscribe('wormhole_channel')
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                await self.handle_message(message['data'])

    async def stop(self):
        self.logger.info("Stopping Tox service")
        self.pubsub.unsubscribe()
        self.redis_client.close()

    async def handle_message(self, message):
        try:
            data = json.loads(message)
            if 'message' in data:
                await self.send_to_tox(data['message'])
        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode message: {message}")

    async def send_to_tox(self, message):
        self.redis_client.publish('tox_node', message)

    def receive_from_tox(self):
        message = self.redis_client.get('tox_node')
        if message:
            return json.loads(message)
        return None