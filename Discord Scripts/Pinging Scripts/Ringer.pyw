import discord
from discord.ext import commands
import tkinter as tk
from tkinter import messagebox
import requests
import asyncio
import json
import threading

# Create a bot instance
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

# Global variable to control the ringing loop
ringing = False

def ring_call(user_ids, bot_token, channel_id):
    url = f'https://discord.com/api/v9/channels/{channel_id}/call/ring'
    payload = {
        "recipients": user_ids
    }
    headers = {
        "Authorization": bot_token,
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 204:
        print(f"Call sent to {', '.join(user_ids)} successfully!")
    else:
        print(f"Failed to send call: {response.text}")

async def send_calls(user_ids, bot_token, channel_id):
    global ringing
    while ringing:
        ring_call(user_ids, bot_token, channel_id)
        await asyncio.sleep(1.25)

def start_ringing():
    global ringing
    user_ids_input = user_id_entry.get()
    bot_token = token_entry.get()
    channel_id = channel_id_entry.get()

    if user_ids_input and bot_token and channel_id:
        user_ids = [uid.strip() for uid in user_ids_input.split(',')]
        ringing = True
        asyncio.run(send_calls(user_ids, bot_token, channel_id))
    else:
        messagebox.showwarning("Input Error", "Please fill in all fields.")

def stop_ringing():
    global ringing
    ringing = False

# Set up the GUI
root = tk.Tk()
root.title("Discord Call Sender")
root.geometry("400x300")  # Set a larger size for the UI
root.resizable(False, False)

# Token input
tk.Label(root, text="Enter Bot Token:").pack(pady=10)
token_entry = tk.Entry(root, width=50)
token_entry.pack(pady=5)

# Channel ID input
tk.Label(root, text="Enter Channel ID:").pack(pady=10)
channel_id_entry = tk.Entry(root, width=50)
channel_id_entry.pack(pady=5)

# User ID input
tk.Label(root, text="Enter User IDs to Call (comma-separated):").pack(pady=10)
user_id_entry = tk.Entry(root, width=50)
user_id_entry.pack(pady=5)

# Start ringing button
start_button = tk.Button(root, text="Start Ringing", command=lambda: threading.Thread(target=start_ringing).start())
start_button.pack(pady=10)

# Stop ringing button
stop_button = tk.Button(root, text="Stop Ringing", command=stop_ringing)
stop_button.pack(pady=10)

root.mainloop()
