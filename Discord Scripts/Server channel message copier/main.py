# Coded with chat gpt


import asyncio
import json
import websockets
import requests
import logging
import time
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Function to read the token from a file
def read_token(file_path):
    try:
        with open(file_path, 'r') as file:
            token = file.read().strip()
    except FileNotFoundError:
        logger.error(f"{file_path} not found.")
        raise
    except IOError as e:
        logger.error(f"Error reading {file_path}: {e}")
        raise

    if not token:
        logger.error("Token is empty or not found in token.txt")
        raise ValueError("Token is empty or not found in token.txt")

    return token

# Function to replace mentions in the content
def replace_mentions(content):
    # Replace @everyone and @here with :no_entry: everyone and :no_entry: here respectively
    content = content.replace('@everyone', ':no_entry: everyone')
    content = content.replace('@here', ':no_entry: here')
    return content

def truncate_url(url, max_length=65):
    """ Truncate the URL to a maximum length and append ellipsis. """
    if len(url) > max_length:
        return url[:max_length] + '...'
    return url

# Function to send a message to the webhook
def send_to_webhook(webhook_url, message, retries=5, wait_time=2):
    payload = {
        "content": message
    }
    attempt = 0
    while attempt < retries:
        try:
            response = requests.post(webhook_url, json=payload)
            if response.status_code == 429:  # Too Many Requests
                # Extract retry-after time from the response headers, if provided
                retry_after = int(response.headers.get('Retry-After', wait_time))
                logger.warning(f"Rate limited. Retrying after {retry_after} seconds...")
                time.sleep(retry_after)
                attempt += 1
            else:
                response.raise_for_status()
                truncated_webhook_url = truncate_url(webhook_url)
                logger.info(f"Message sent to webhook: {truncated_webhook_url}")
                break
        except requests.RequestException as e:
            logger.error(f"Error sending message to webhook: {e}")
            break

# Cache for channel names
channel_cache = {}

# Function to fetch channel name using Discord API
async def get_channel_name(token, channel_id):
    # Check if channel name is in the cache
    if channel_id in channel_cache:
        return channel_cache[channel_id]
    
    url = f'https://discord.com/api/v10/channels/{channel_id}'
    headers = {
        'Authorization': token
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        channel_name = data.get('name', 'Unknown Channel')
        # Cache the channel name
        channel_cache[channel_id] = channel_name
        return channel_name
    except requests.RequestException as e:
        logger.error(f"Error fetching channel name: {e}")
        return 'Unknown Channel'

# Function to handle WebSocket connection
async def handle_websocket(token, configurations):
    url = 'wss://gateway.discord.gg/?v=10&encoding=json'
    while True:  # Loop to handle reconnections
        try:
            async with websockets.connect(url) as ws:
                logger.info("Websocket connection established")

                # Authenticate with the Discord API
                payload = {
                    "op": 2,
                    "d": {
                        "token": token,
                        "properties": {
                            "$os": "linux",
                            "$browser": "my_library",
                            "$device": "my_library"
                        }
                    }
                }
                await ws.send(json.dumps(payload))
                logger.info("Authentication payload sent")

                heartbeat_interval = None
                next_heartbeat = time.time() + 30  # Initialize to send first heartbeat after 30 seconds

                while True:
                    try:
                        message = await ws.recv()
                        event = json.loads(message)

                        if event.get('t') == 'MESSAGE_CREATE':
                            channel_id = event['d']['channel_id']
                            config = next((cfg for cfg in configurations if str(channel_id) in cfg['source_channel_ids']), None)

                            if config:
                                user_info = event['d']['author']['username']
                                global_name = event['d']['author'].get('global_name', 'No Display')
                                timestamp = event['d']['timestamp']
                                content = replace_mentions(event['d']['content'])

                                if event['d'].get('attachments'):
                                    for attachment in event['d']['attachments']:
                                        if attachment['content_type'].startswith('image/') or attachment['content_type'].startswith('video/'):
                                            content += f"\n{attachment['url']}"

                                channel_name = await get_channel_name(token, channel_id)

                                if timestamp:
                                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                    unix_timestamp = int(dt.timestamp())
                                    formatted_timestamp = f'<t:{unix_timestamp}:D>'
                                    formatted_timestamp2 = f'<t:{unix_timestamp}:T>'
                                else:
                                    formatted_timestamp = 'Unknown Time'
                                    formatted_timestamp2 = 'Unknown Time'

                                invisible_character = '\u3164'
                                formatted_message = (f'> **User:** {user_info} :white_small_square: **Display:** {global_name} '
                                                    f':white_small_square: **Channel:** {channel_name} :white_small_square: '
                                                    f'**Timestamp:** {formatted_timestamp} {formatted_timestamp2}\n{content}\n{invisible_character}')

                                # Send the formatted message to the target webhook
                                send_to_webhook(config['target_channel_webhook'], formatted_message)

                        elif event.get('t') == 'READY':
                            heartbeat_interval = event['d'].get('heartbeat_interval') / 1000 if 'heartbeat_interval' in event['d'] else 30  # Default to 30s
                            logger.info(f"Heartbeat interval received: {heartbeat_interval} seconds")

                        elif event.get('t') == 'HELLO':
                            heartbeat_interval = event['d'].get('heartbeat_interval') / 1000 if 'heartbeat_interval' in event['d'] else 30  # Default to 30s
                            next_heartbeat = time.time() + heartbeat_interval
                            logger.info(f"Hello event received, setting heartbeat interval to {heartbeat_interval} seconds")

                        # Check if it's time to send a heartbeat
                        if heartbeat_interval and time.time() >= next_heartbeat:
                            heartbeat_payload = {
                                "op": 1,
                                "d": None
                            }
                            await ws.send(json.dumps(heartbeat_payload))
                            logger.info("Heartbeat sent")
                            next_heartbeat = time.time() + heartbeat_interval

                    except websockets.ConnectionClosed as e:
                        logger.error(f"Websocket connection closed: {e}")
                        break
                    except Exception as e:
                        logger.error(f"Error handling websocket message: {e}")

        except Exception as e:
            logger.error(f"Error establishing websocket connection: {e}")
            logger.info("Reconnecting in 5 seconds...")
            time.sleep(5)  # Wait before retrying to reconnect

if __name__ == "__main__":
    try:
        TOKEN = read_token('token.txt')

        # List of configurations
        # Source channel ids are your channel ids where you are going to listen for messages
        # Webhook is webhook :p
        # source guild id, is the server id where the channels are getting listened from
        # and u can add more to it
        configurations = [
            {
                'source_channel_ids': ['Put your 1 id here', 'remove this if u dont need it', 'and this'],
                'target_channel_webhook': 'webhook link!',
                'source_guild_id': 'server of the source channel ids'
            },
            {
                'source_channel_ids': ['the same here'],
                'target_channel_webhook': 'webhook',
                'source_guild_id': 'server'
            },
        ]

        # Run the websocket handling function
        asyncio.run(handle_websocket(TOKEN, configurations))

    except Exception as e:
        logger.error(f"Script error: {e}")



# Coded with chat gpt