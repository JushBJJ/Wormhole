import logging
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
        current_envelope = {}
        attachment = {}
        
        # ! Lol thanks GPT-4
        try:
            for line in lines:
                if line.startswith("Envelope from:"):
                    if current_envelope:
                        envelopes.append(current_envelope)
                        current_envelope = {}
                    parts = line.split(" to ")
                    sender_info = parts[0].split(" ")[2:]
                    sender_name = sender_info[0].strip('“”')
                    sender_id = sender_info[1]
                    device_info = sender_info[2]
                    recipient = parts[1].strip()
                    current_envelope["sender"] = {"name": sender_name, "id": sender_id, "device": device_info}
                    current_envelope["recipient"] = recipient

                elif line.startswith("  Timestamp:"):
                    timestamp = line.split(": ")[1].strip()
                    current_envelope["timestamp"] = timestamp

                elif line.startswith("Server timestamps:"):
                    received = line.split("received: ")[1].split(" ")[0]
                    delivered = line.split("delivered: ")[1].strip()
                    current_envelope["server_timestamps"] = {"received": received, "delivered": delivered}

                elif line.startswith("Sent by unidentified/sealed sender"):
                    current_envelope["sender_type"] = "unidentified/sealed"

                elif line.startswith("Received a typing message"):
                    current_envelope["typing_message"] = {}

                elif line.startswith("  Action:"):
                    action = line.split(": ")[1].strip()
                    
                    try:
                        current_envelope["typing_message"]["action"] = action
                    except:
                        current_envelope["action"] = action

                elif line.startswith("  Timestamp:"):
                    typing_timestamp = line.split(": ")[1].strip()
                    try:
                        current_envelope["typing_message"]["timestamp"] = typing_timestamp
                    except:
                        current_envelope["timestamp"] = typing_timestamp

                elif line.startswith("  Body:"):
                    body = line.split(": ")[1].strip()
                    current_envelope["body"] = body

                elif line.startswith("  With profile key"):
                    current_envelope["with_profile_key"] = True

                elif line.startswith("- Attachment:"):
                    if "attachments" not in current_envelope:
                        current_envelope["attachments"] = []
                        attachment = {}
                        
                elif line.startswith("  Content-Type:"):
                    content_type = line.split(": ")[1].strip()
                    attachment["content_type"] = content_type

                elif line.startswith("  Type:"):
                    attachment_type = line.split(": ")[1].strip()
                    attachment["type"] = attachment_type

                elif line.startswith("  Id:"):
                    attachment_id = line.split(": ")[1].strip()
                    attachment["id"] = attachment_id

                elif line.startswith("  Upload timestamp:"):
                    upload_timestamp = line.split(": ")[1].strip()
                    attachment["upload_timestamp"] = upload_timestamp

                elif line.startswith("  Filename:"):
                    filename = line.split(": ")[1].strip()
                    attachment["filename"] = filename

                elif line.startswith("  Size:"):
                    size = line.split(": ")[1].strip()
                    attachment["size"] = size

                elif line.startswith("  Dimensions:"):
                    dimensions = line.split(": ")[1].strip()
                    attachment["dimensions"] = dimensions

                elif line.startswith("  Stored plaintext in:"):
                    stored_in = line.split(": ")[1].strip()
                    attachment["stored_in"] = stored_in
                    current_envelope["attachments"].append(attachment)
                elif line.startswith("Received a sync message"):
                    current_envelope["sync_message"] = {}

                elif line.startswith("Received sync sent message"):
                    current_envelope["sync_sent_message"] = {}

                elif line.startswith("  To:"):
                    to_list = line.split(":")[1].strip()
                    current_envelope["sync_sent_message"]["to"] = to_list

                elif line.startswith("  Message timestamp:"):
                    message_timestamp = line.split(":")[1].strip()
                    current_envelope["sync_sent_message"]["message_timestamp"] = message_timestamp

                elif line.startswith("  Body:"):
                    body = line.split(":")[1].strip()
                    current_envelope["sync_sent_message"]["body"] = body

                elif line.startswith("  Group info:"):
                    current_envelope["sync_sent_message"]["group_info"] = {}

                elif line.startswith("    Id:"):
                    group_id = line.split(":")[1].strip()
                    current_envelope["sync_sent_message"]["group_info"]["id"] = group_id

                elif line.startswith("    Name:"):
                    group_name = line.split(":")[1].strip()
                    current_envelope["sync_sent_message"]["group_info"]["name"] = group_name

                elif line.startswith("    Revision:"):
                    revision = line.split(":")[1].strip()
                    current_envelope["sync_sent_message"]["group_info"]["revision"] = revision

                elif line.startswith("    Type:"):
                    group_type = line.split(":")[1].strip()
                    current_envelope["sync_sent_message"]["group_info"]["type"] = group_type

                elif line.startswith("With profile key"):
                    current_envelope["with_profile_key"] = True

        except Exception as e:
            self.logger.error(f"Error parsing message: {e}")
            return []
        
        if len(envelopes) == 0:
            envelopes.append(current_envelope)

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
                if message.get("sync_sent_message", {}).get("group_info", {}).get("type", "") == "DELIVER":
                    group = message["sync_sent_message"]["group_info"]["id"]
                    if group not in list(config.get("signal", {}).get("groups", [])):
                        self.logger.info(f"Skipping message because group {group} is not in the config.")
                        continue
                else:
                    self.logger.info("Skipping message because it is not a group message.")
                    continue
                
                if message.get("body", ""):
                    sender = message.get("sender", {}).get("name", "")
                    body = message.get("body", "")

                    msg_signal, msg_telegram, msg_discord = self.process_message(sender, body)

                    current_group = message.get("sync_sent_message", {}).get("group_info", {}).get("id", "")
                    
                    for group in config.get("signal", {}).get("groups", []):
                        if current_group!=group:
                            self.logger.info(f"Sending message to Signal group {group}: {msg}")
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
                    
                    if len(message) > 0:
                        self.logger.info(f"Message received: {message}")
                        asyncio.run(self.global_msg(message))
                        
                stderr = process.communicate()[1]
                if stderr:
                    self.logger.error(f"Error: {stderr}")

        except Exception as e:
            self.logger.error(f"Error: {e}")