import re
import threading
import subprocess
import time
import json
import redis.asyncio as aioredis
import asyncio

from bot.utils.file import read_config
from bot.utils.logging import configure_logging

class SignalBot:
    def __init__(self, command, args):
        """
        Initializes the SignalBot with a command and its arguments.
        :param command: The command to execute.
        :param args: A list of arguments for the command.
        """
        self.command = command
        self.args = args
        self.running = True
        self.logger = configure_logging()
    
    def start_wormhole(self):
        self.redis = aioredis.from_url("redis://localhost", decode_responses=True)
        self.logger.info("Starting subscriber thread...")
        thread = threading.Thread(target=self.receive_loop_func, daemon=True)
        thread.start()
        self.logger.info("Starting Signal bot...")
        self.receive_thread = threading.Thread(target=self.listen, daemon=True)
        self.receive_thread.start()
        thread.join()
        self.receive_thread.join()

        
    def receive_loop_func(self):
        # Create loop
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.receive_loop())
        except Exception as e:
            self.logger.error(f"[LOOP CLOSED] Error in receive_loop_func: {e}")
            time.sleep(5)
            self.receive_loop_func()
    
    async def receive_loop(self):
        sub = self.redis.pubsub()
        await sub.subscribe("signal_channel")
        
        async for message in sub.listen():
            self.logger.info(message)
            if message["type"] == "message":
                data = json.loads(message["data"])
                msg = data.get("message", "")
                await self.global_msg(msg, signal_only=True)

    def parse_message(self, data):
        lines = data.split('\n')

        envelopes = []
        current = {}
        
        group_info_keys = ["Id", "Name", "Revision", "Type"]
        pattern = r'“([^”]+)” ([a-z0-9+\-]+) \(device: (\d+)\) to (\+\d+)'

        try:
            lines = data.splitlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("Envelope from:"):
                    if current:
                        envelopes.append(current)
                    
                    match = re.search(pattern, line)
                    current = {
                        "sender": match.group(1),
                        "uuid": match.group(2),
                        "device": int(match.group(3)),
                    }
                elif ": " in line:         
                    key, value = line.split(": ", 1)        
                    if type(current.get("Group info", False))==dict:
                        if not current.get("Group info", {}).get(key, False) and key in group_info_keys:
                            current["Group info"][key] = value
                            continue      
                    elif key.strip() in current:
                        if isinstance(current[key.strip()], dict):
                            current[key.strip()]["additional"] = value.strip()
                        else:
                            current[key.strip()] = [current[key.strip()], value.strip()]
                    else:
                        current[key.strip()] = value.strip()
                elif "Group info:" in line and "Body" in current.keys():
                    current["Group info"] = dict({})
                    continue        
                elif line.startswith("- "):
                    # Handle list entries
                    key = line[1:].strip()
                    if 'Timestamps' in current:
                        current['Timestamps'].append(key)
                    else:
                        current['Timestamps'] = [key]
            if current:
                envelopes.append(current)

        except Exception as e:
            self.logger.error(f"Error parsing message: {e}")
            return []
        
        if len(envelopes) == 0:
            envelopes.append({})

        return envelopes
    
    def process_message(self, sender, body):
        msg_signal = f"[SIGNAL] {sender} says:\n{body}"
        msg_telegram = f"<b>[SIGNAL] {sender} says:</b>\n{body}"
        msg_discord = f"```[SIGNAL] {sender} says:```{body}"
        
        return msg_signal, msg_telegram, msg_discord
    
    async def global_msg(self, messages, signal_only=False):
        config = await read_config()

        if not signal_only:
            for message in messages:  
                if message.get("Group info", False):
                    sender_group = message["Group info"]["Id"]
                    if sender_group not in list(config.get("signal", {}).get("groups", [])):
                        self.logger.info(f"Skipping message because group {group} is not in the config.")
                        continue
                else:
                    self.logger.info("Skipping message because it is not a group message.")
                    continue
                
                if message.get("Body", False):
                    sender = message["sender"]
                    body = message["Body"]

                    msg_signal, msg_telegram, msg_discord = self.process_message(sender, body)

                    for group in config.get("signal", {}).get("groups", []):
                        if sender_group!=group:
                            self.logger.info(f"Sending message to Signal group {group}: {msg_signal}")
                            p = subprocess.Popen(["signal-cli", "send", "-m", msg_signal, "-g", group])
                            p.wait()
                    
                    try:
                        await self.redis.publish("wormhole_channel", json.dumps({"message": msg_signal, "discord_only": True}))
                    except Exception as e:
                        self.logger.error(f"Error sending message to Discord: {e}")
                    
                    try:
                        await self.redis.publish("telegram_channel", json.dumps({"message": msg_telegram, "telegram_only": True}))
                    except Exception as e:
                        self.logger.error(f"Error sending message to Telegram: {e}")
                        
        else:
            # Usually means that it is a plain string message
            for group in config.get("signal", {}).get("groups", []):
                self.logger.info(f"Sending message to Signal group {group}: {messages}")
                p = subprocess.Popen(["signal-cli", "send", "-m", messages, "-g", group])
                p.wait()
                
    def listen(self):
        """Executes the given command and prints output in real-time."""
        try:
            while True:
                full_command = ['stdbuf', '-oL'] + [self.command] + self.args
                process = subprocess.Popen(full_command,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        text=True)

                output = process.stdout.read()
                if output:
                    message = self.parse_message(output)
                    self.logger.info(f"Raw message: {output}")
                    
                    if len(message) > 0:
                        self.logger.info(f"Message received: {message}")
                        asyncio.run(self.global_msg(message))
                        
                stderr = process.communicate()[1]
                if stderr:
                    self.logger.error(f"Error: {stderr}")

        except Exception as e:
            self.logger.error(f"Error: {e}")