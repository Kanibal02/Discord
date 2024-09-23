# Created with chat gpt and roblox apis
# You don't need to login into anything, other than needing Universe ids, and Your Discord BOT token

import discord
import requests
import asyncio
import logging
import os
from discord.ext import tasks, commands
from datetime import datetime
import pytz  # Import pytz for timezone handling

# Dictionary to store channel-specific universe IDs
CHANNEL_UNIVERSE_IDS = {
    123: ['', ''],
    123: ['', '', ''],
    123: ['']
    # (your discord chnanel id): ['roblox universe id', 'other one']
}

class PolishTimezoneFormatter(logging.Formatter):
    """Custom formatter to set the timezone to Polish time (CET/CEST)."""

    def formatTime(self, record, datefmt=None):
        # Set the timezone to Polish time
        polish_timezone = pytz.timezone('Europe/Warsaw')
        dt = datetime.fromtimestamp(record.created, tz=polish_timezone)

        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.strftime('%Y-%m-%d %H:%M:%S')

def get_next_log_filename(base_name="logs", extension=".txt"):
    """Finds the next available log filename."""
    i = 1
    while True:
        filename = f"{base_name}{i}{extension}"
        if not os.path.exists(filename):
            return filename
        i += 1

# Set up logging with the next available log filename
log_filename = get_next_log_filename()
logging.basicConfig(
    level=logging.INFO,
    format='[{asctime}]: {message}',
    style='{',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Create a formatter that uses Polish time
polish_formatter = PolishTimezoneFormatter('[{asctime}]: {message}', style='{')

# Apply the formatter to all the handlers
for handler in logging.getLogger().handlers:
    handler.setFormatter(polish_formatter)

# Function to read the token from a file
def read_token(file_path):
    """Read the Discord bot token from a file."""
    try:
        with open(file_path, 'r') as file:
            token = file.read().strip()
    except FileNotFoundError:
        logging.warning(f"{file_path} not found.")
        raise
    except IOError as e:
        logging.error(f"Error reading {file_path}: {e}")
        raise

    if not token:
        print("Token is empty or not found in token.txt")
        raise ValueError("Token is empty or not found in token.txt")

    return token

# Read the token from token.txt
DISCORD_TOKEN = read_token('token.txt')

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True  # Ensure message content intent is enabled
bot = commands.Bot(command_prefix='!', intents=intents)

def get_game_data(universe_ids):
    """Fetch game data from Roblox API for specific universe IDs."""
    url = f'https://games.roblox.com/v1/games?universeIds={",".join(universe_ids)}'
    response = requests.get(url)
    return response.json()

def format_number(number):
    """Format number with commas."""
    return "{:,}".format(number)

def convert_to_unix(timestamp):
    """Convert ISO 8601 timestamp to Unix timestamp."""
    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    return int(dt.timestamp())

# Function to get current time in Polish timezone
def get_polish_time():
    tz = pytz.timezone('Europe/Warsaw')
    return datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

# Custom log message function with Polish time
def log_message(message):
    timestamp = get_polish_time()
    logging.info(f"[{timestamp}]: {message}")

def fetch_image_url(place_id):
    """Fetch the image URL for a game based on placeId."""
    url = f'https://thumbnails.roblox.com/v1/places/gameicons?placeIds={place_id}&returnPolicy=PlaceHolder&size=512x512&format=Png&isCircular=false'
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if "data" in data and len(data["data"]) > 0 and "imageUrl" in data["data"][0]:
            return data["data"][0]["imageUrl"]
        else:
            logging.warning("imageUrl not found in the response")
            return None
    else:
        logging.warning(f"Failed to fetch data. Status code: {response.status_code}")
        return None

async def update_discord_message(channel, message_id=None):
    """Update the message with game information."""
    # Get the universe IDs for the channel
    universe_ids = CHANNEL_UNIVERSE_IDS.get(channel.id)
    
    if not universe_ids:
        logging.warning(f"No universe IDs found for channel {channel.id}")
        return
    
    data = get_game_data(universe_ids)
    
    embeds = []
    
    for game in data.get('data', []):
        updated_timestamp = convert_to_unix(game.get('updated'))
        
        # Prepare the game details
        name = game.get('name')
        playing = format_number(game.get('playing'))
        visits = format_number(game.get('visits'))
        favorites = format_number(game.get('favoritedCount'))
        game_link = f"https://www.roblox.com/games/{game.get('rootPlaceId')}/"
        
        # Fetch the thumbnail for the game
        thumbnail_url = fetch_image_url(game.get('rootPlaceId'))
        
        # Create an embed for each game
        embed = discord.Embed(
            title=name,
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Game Info",
            value=f"Current Playing: **{playing}**\nVisits: **{visits}**\nFavorites: **{favorites}**\n\nLast Updated: <t:{updated_timestamp}:R>",
            inline=False
        )
        embed.set_thumbnail(url=thumbnail_url)
        embed.set_footer(text=game_link)
        
        embeds.append(embed)
        
        # Print statement with timestamp
        logging.info(f"Successfully fetched information from Roblox to Discord. Time: {get_polish_time()}")

    # Send or edit the message with the embed(s)
    if message_id:
        try:
            message = await channel.fetch_message(message_id)
            if len(embeds) == 1:
                await message.edit(embed=embeds[0])  # Single embed case
            else:
                await message.edit(content=None, embeds=embeds)  # Multiple embeds case
        except discord.NotFound:
            for embed in embeds:
                await channel.send(embed=embed)
    else:
        for embed in embeds:
            await channel.send(embed=embed)


@bot.event
async def on_ready():
    """Event that runs when the bot is ready."""
    logging.info(f'Logged in as {bot.user}')
    
    # Iterate over all channels in the dictionary
    for channel_id in CHANNEL_UNIVERSE_IDS.keys():
        channel = bot.get_channel(channel_id)
        
        # Fetch the most recent message or send a new one
        async for message in channel.history(limit=10):
            await update_discord_message(channel, message.id)
            break

    # Start the periodic updates only if it's not already running
    if not periodic_update.is_running():
        periodic_update.start()



@bot.event
async def on_message(message):
    """Event that runs on every new message."""
    if message.author == bot.user:
        return
    if message.content.startswith('!updategames'):
        channel = message.channel
        await update_discord_message(channel, message.id)

# Inside your periodic_update task, replace print with log_message
@tasks.loop(seconds=30)
async def periodic_update():
    """Periodic task to update the game information."""
    for channel_id in CHANNEL_UNIVERSE_IDS.keys():
        channel = bot.get_channel(channel_id)
        try:
            if channel.last_message_id:
                await update_discord_message(channel, channel.last_message_id)
            else:
                await update_discord_message(channel)
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            logging.warning("Retrying in 1 minute...")
            await asyncio.sleep(60)  # Wait for 1 minute before retrying
            continue  # Retry the loop

# Run the bot
bot.run(DISCORD_TOKEN)
