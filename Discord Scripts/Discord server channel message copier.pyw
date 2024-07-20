# made by chat gpt

import tkinter as tk
from tkinter import scrolledtext
import requests
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

class MessageCopierApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Discord Message Copier")
        self.root.geometry("450x900")  # Set the initial window size
        self.root.resizable(False, False)  # Make the window non-resizable

        self.token_label = tk.Label(root, text="Enter User Token:")
        self.token_label.pack()

        self.token_entry = tk.Entry(root, width=50)
        self.token_entry.pack()

        self.source_server_id_label = tk.Label(root, text="(copy from) Enter Source Server ID:")
        self.source_server_id_label.pack()

        self.source_server_id_entry = tk.Entry(root, width=50)
        self.source_server_id_entry.pack()

        self.source_channel_id_label = tk.Label(root, text="(copy from) Enter Source Channel ID:")
        self.source_channel_id_label.pack()

        self.source_channel_id_entry = tk.Entry(root, width=50)
        self.source_channel_id_entry.pack()

        self.target_server_id_label = tk.Label(root, text="(copy to) Enter Target Server ID:")
        self.target_server_id_label.pack()

        self.target_server_id_entry = tk.Entry(root, width=50)
        self.target_server_id_entry.pack()

        self.target_channel_id_label = tk.Label(root, text="(copy to) Enter Target Channel ID:")
        self.target_channel_id_label.pack()

        self.target_channel_id_entry = tk.Entry(root, width=50)
        self.target_channel_id_entry.pack()

        self.start_button = tk.Button(root, text="Start Copying", command=self.start_copying)
        self.start_button.pack()

        self.stop_button = tk.Button(root, text="Stop Copying", command=self.stop_copying)
        self.stop_button.pack()

        self.log = scrolledtext.ScrolledText(root, height=40, width=50)
        self.log.pack()

        self.running = False
        self.latest_message_id = None  # Track the latest message ID
        self.message_mapping = {}  # Map source message IDs to target message IDs
        self.edited_messages = {}  # Track messages that have been edited
        self.edited_message_ids = set()  # Set to keep track of edited message IDs
        self.message_last_edit = {}  # Store the last edit timestamp of messages
        self.processed_message_ids = set()  # Track processed message IDs
        self.executor = ThreadPoolExecutor(max_workers=4)  # Adjust the number of threads as needed

        self.message_send_interval = 0.5  # Interval between sending messages (2 messages per second)

    def log_message(self, message):
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)

    def get_channel_name(self, token, channel_id):
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        url = f'https://discord.com/api/v9/channels/{channel_id}'
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            channel_data = response.json()
            return channel_data.get('name', 'Unknown Channel')
        else:
            self.log_message(f'Failed to fetch channel name: {response.status_code} - {response.text}')
            return 'Unknown Channel'

    def download_media(self, media_url, file_path, retries=3):
        for attempt in range(retries):
            try:
                response = requests.get(media_url, stream=True)
                if response.status_code == 200:
                    with open(file_path, 'wb') as file:
                        for chunk in response.iter_content(chunk_size=8192):
                            file.write(chunk)
                    return True
                else:
                    self.log_message(f"Failed to download media on attempt {attempt + 1}: {response.status_code} - {response.text}")
            except Exception as e:
                self.log_message(f"Error downloading media on attempt {attempt + 1}: {str(e)}")
            time.sleep(2)  # Wait before retrying
        return False

    def upload_media(self, token, file_path, target_channel_id, retries=3):
        for attempt in range(retries):
            try:
                headers = {
                    'Authorization': token
                }
                url = f'https://discord.com/api/v9/channels/{target_channel_id}/messages'
                with open(file_path, 'rb') as file:
                    files = {'file': file}
                    response = requests.post(url, headers=headers, files=files)
                    if response.status_code == 200:
                        self.log_message(f"Successfully uploaded media: {file_path}")
                        return True
                    elif response.status_code == 429:
                        retry_after = response.json().get('retry_after', 0)
                        self.log_message(f'Rate limited. Retrying after {retry_after} seconds.')
                        time.sleep(retry_after)
                    else:
                        self.log_message(f'Failed to upload media on attempt {attempt + 1}: {response.status_code} - {response.text}')
            except Exception as e:
                self.log_message(f"Error uploading media on attempt {attempt + 1}: {str(e)}")
            time.sleep(2)  # Wait before retrying
        return False

    def fetch_messages(self, token, channel_id, limit=10):
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        url = f'https://discord.com/api/v9/channels/{channel_id}/messages'
        params = {'limit': limit}
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            messages = response.json()
            self.log_message(f"Fetched {len(messages)} messages from channel.")
            if messages:
                # Reverse the messages to preserve the correct order
                messages.reverse()
                self.latest_message_id = messages[-1]['id']
                return messages
        elif response.status_code == 401:
            self.log_message('Unauthorized: Check if the token is correct and has necessary permissions.')
        elif response.status_code == 429:
            retry_after = response.json().get('retry_after', 0)
            self.log_message(f'Rate limited. Retrying after {retry_after} seconds.')
            time.sleep(retry_after)
        else:
            self.log_message(f'Failed to fetch messages: {response.status_code} - {response.text}')
        return []

    def format_message(self, token, message, source_channel_id, is_fetched_message=False):
        user_info = message.get('author', {}).get('username', 'Unknown User')
        user_info += ' (Bot)' if message.get('author', {}).get('bot') else ' (Webhook)' if message.get('webhook_id') else ''
        
        global_name = message.get('author', {}).get('global_name', 'Unknown Display Name')
        content = message.get('content', '')
        
        if message.get('attachments'):
            for attachment in message['attachments']:
                content += f'\n[Attachment: {attachment.get("filename", "attachment")}]({attachment["url"]})'

        # Get the channel name
        channel_name = self.get_channel_name(token, source_channel_id)
        
        # Format the timestamp using Unix timestamp
        timestamp = message.get('timestamp', '')
        if timestamp:
            # Parse the timestamp
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            unix_timestamp = int(dt.timestamp())
            formatted_timestamp = f"<t:{unix_timestamp}:f>"
        else:
            formatted_timestamp = 'Unknown Time'
        
        # Add the Hangul Filler character for invisible space
        invisible_character = '\u3164'
        formatted_message = (f'> **User:** {user_info} :white_small_square: **Display:** {global_name} '
                             f':white_small_square: **Channel:** {channel_name} :white_small_square: '
                             f'**Timestamp:** {formatted_timestamp}')
        
        if is_fetched_message:
            formatted_message += ' :white_small_square: **It\'s a fetched message**'
        
        formatted_message += f'\n{content}\n{invisible_character}'
        
        return formatted_message

    def send_message(self, target_url, headers, payload, source_message_id):
        response = requests.post(target_url, headers=headers, json=payload)
        if response.status_code == 200:
            self.log_message(f"Successfully copied message: {payload['content']}")
            target_message_id = response.json()['id']
            self.message_mapping[source_message_id] = target_message_id  # Store the mapping
        elif response.status_code == 429:
            retry_after = response.json().get('retry_after', 0)
            self.log_message(f'Rate limited. Retrying after {retry_after} seconds.')
            time.sleep(retry_after)
        else:
            self.log_message(f'Failed to send message: {response.status_code} - {response.text}')

    def process_message(self, token, message, target_channel_id, source_channel_id, is_fetched_message=False):
        source_message_id = message['id']
        
        # Avoid processing the same message more than once
        if source_message_id in self.processed_message_ids:
            return
        
        formatted_message = self.format_message(token, message, source_channel_id, is_fetched_message)
        
        if formatted_message.strip():
            headers = {
                'Authorization': token,
                'Content-Type': 'application/json'
            }
            target_url = f'https://discord.com/api/v9/channels/{target_channel_id}/messages'
            payload = {
                'content': formatted_message,
                'tts': False
            }
            
            # Submit the message sending task to the executor
            self.executor.submit(self.send_message, target_url, headers, payload, source_message_id)
            self.processed_message_ids.add(source_message_id)
            
            # Implement a delay to control the rate of sending messages
            time.sleep(self.message_send_interval)

    def listen_for_new_messages(self, token, source_channel_id, target_channel_id):
        while self.running:
            new_messages = self.fetch_messages(token, source_channel_id)
            for message in new_messages:
                self.process_message(token, message, target_channel_id, source_channel_id)
            time.sleep(2)  # Adjust the sleep time as needed

    def start_copying(self):
        self.running = True
        token = self.token_entry.get().strip()
        source_channel_id = self.source_channel_id_entry.get().strip()
        target_channel_id = self.target_channel_id_entry.get().strip()

        if not token or not source_channel_id or not target_channel_id:
            self.log_message("Please fill in all fields.")
            return

        # Fetch initial set of messages
        messages = self.fetch_messages(token, source_channel_id)
        for i, message in enumerate(messages):
            # Apply special format only to the first 10 messages
            is_fetched_message = i < 10
            self.process_message(token, message, target_channel_id, source_channel_id, is_fetched_message)
        
        # Start listening for new messages and edits
        self.listener_thread = threading.Thread(target=self.listen_for_new_messages, args=(token, source_channel_id, target_channel_id))
        self.listener_thread.daemon = True
        self.listener_thread.start()

    def stop_copying(self):
        self.running = False
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.join()

if __name__ == "__main__":
    root = tk.Tk()
    app = MessageCopierApp(root)
    root.mainloop()
