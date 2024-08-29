import discord
import requests
import asyncio
from discord.ext import tasks, commands
from datetime import datetime
import pytz  # Import pytz for timezone handling

# Function to read the token from a file
def read_token(file_path):
    """Read the Discord bot token from a file."""
    try:
        with open(file_path, 'r') as file:
            token = file.read().strip()
    except FileNotFoundError:
        print(f"{file_path} not found.")
        raise
    except IOError as e:
        print(f"Error reading {file_path}: {e}")
        raise

    if not token:
        print("Token is empty or not found in token.txt")
        raise ValueError("Token is empty or not found in token.txt")

    return token

# Read the token from token.txt
DISCORD_TOKEN = read_token('token.txt')
CHANNEL_ID = 1253389437069557840  # Replace with your Discord channel ID
UNIVERSE_IDS = [
    'Add an universe id, not game id, if you dont know how to get it, check on the internet!',
    # 'ANOTHER_UNIVERSE_ID',
]

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True  # Ensure message content intent is enabled
bot = commands.Bot(command_prefix='!', intents=intents)

def get_game_data():
    """Fetch game data from Roblox API."""
    url = f'https://games.roblox.com/v1/games?universeIds={",".join(UNIVERSE_IDS)}'
    response = requests.get(url)
    return response.json()

def format_number(number):
    """Format number with commas."""
    return "{:,}".format(number)

def convert_to_unix(timestamp):
    """Convert ISO 8601 timestamp to Unix timestamp."""
    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    return int(dt.timestamp())

def get_polish_time():
    """Get the current time in Polish time zone."""
    tz = pytz.timezone('Europe/Warsaw')
    return datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

async def update_discord_message(channel, message_id=None):
    """Update the message with game information."""
    data = get_game_data()
    
    embeds = []
    padding = "ㅤ" * 35  # 25 instances of the character to pad the title
    
    for game in data.get('data', []):
        updated_timestamp = convert_to_unix(game.get('updated'))
        
        # Prepare the padded game title
        name = game.get('name') + padding
        playing = format_number(game.get('playing'))
        visits = format_number(game.get('visits'))
        favorites = format_number(game.get('favoritedCount'))
        game_link = f"[Click Me](https://www.roblox.com/games/{game.get('rootPlaceId')}/)"
        
        # Create an embed for each game
        embed = discord.Embed(
            title=name,
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Current Player Count", value=f"**{playing}**", inline=False)
        embed.add_field(name="Visits", value=visits, inline=False)
        embed.add_field(name="Favorites", value=favorites, inline=False)
        embed.add_field(name="Last Updated", value=f"<t:{updated_timestamp}:R>", inline=False)
        embed.add_field(name="Game Link", value=game_link, inline=False)
        
        embeds.append(embed)
        
        # Print statement with timestamp
        print(f"Successfully fetched information from Roblox to Discord. Time: {get_polish_time()}")

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
    print(f'Logged in as {bot.user}')
    channel = bot.get_channel(CHANNEL_ID)
    
    # Fetch the most recent message or send a new one
    async for message in channel.history(limit=10):
        await update_discord_message(channel, message.id)
        break
    else:
        await channel.send("Fetching game data...")

    # Start the periodic updates
    periodic_update.start()

@bot.event
async def on_message(message):
    """Event that runs on every new message."""
    if message.author == bot.user:
        return
    if message.content.startswith('!updategames'):
        channel = message.channel
        await update_discord_message(channel, message.id)

@tasks.loop(minutes=1)
async def periodic_update():
    """Periodic task to update the game information."""
    channel = bot.get_channel(CHANNEL_ID)
    if channel.last_message_id:
        await update_discord_message(channel, channel.last_message_id)
    else:
        await update_discord_message(channel)

# Run the bot
bot.run(DISCORD_TOKEN)
