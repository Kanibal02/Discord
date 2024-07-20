import tkinter as tk
from tkinter import scrolledtext
import requests
import time
import threading
import os

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

    def log_message(self, message):
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)

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

    def fetch_messages(self, token, channel_id, limit=5):
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

    def format_message(self, message):
        user_info = message.get('author', {}).get('username', 'Unknown User')
        user_info += ' (Bot)' if message.get('author', {}).get('bot') else ' (Webhook)' if message.get('webhook_id') else ''
        
        content = message.get('content', '')
        
        if message.get('attachments'):
            for attachment in message['attachments']:
                content += f'\n[Attachment: {attachment.get("filename", "attachment")}]({attachment["url"]})'

        # Add the Hangul Filler character for invisible space
        invisible_character = '\u3164'
        return f'> **User:** {user_info}\n{content}\n{invisible_character}'

    def process_message(self, token, message, target_channel_id):
        formatted_message = self.format_message(message)
        
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
            
            # Send the message
            response = requests.post(target_url, headers=headers, json=payload)
            if response.status_code == 200:
                self.log_message(f"Successfully copied message: {formatted_message}")
            elif response.status_code == 429:
                retry_after = response.json().get('retry_after', 0)
                self.log_message(f'Rate limited. Retrying after {retry_after} seconds.')
                time.sleep(retry_after)
            else:
                self.log_message(f'Failed to send message: {response.status_code} - {response.text}')

    def listen_for_new_messages(self, token, source_channel_id, target_channel_id):
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        url = f'https://discord.com/api/v9/channels/{source_channel_id}/messages'
        
        while self.running:
            try:
                params = {'after': self.latest_message_id} if self.latest_message_id else {}
                response = requests.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    messages = response.json()
                    if messages:
                        self.log_message(f"Fetched {len(messages)} new messages from channel.")
                        
                        # Reverse the messages order
                        messages.reverse()
                        
                        for message in messages:
                            self.process_message(token, message, target_channel_id)
                        
                        # Update latest message ID after processing
                        self.latest_message_id = messages[-1]['id']
                    
                elif response.status_code == 401:
                    self.log_message('Unauthorized: Check if the token is correct and has necessary permissions.')
                    break
                elif response.status_code == 429:
                    retry_after = response.json().get('retry_after', 0)
                    self.log_message(f'Rate limited. Retrying after {retry_after} seconds.')
                    time.sleep(retry_after)
                else:
                    self.log_message(f'Failed to fetch new messages: {response.status_code} - {response.text}')
                
                # Wait before checking for new messages
                time.sleep(1)  # Adjusted to 1 seconds

            except Exception as e:
                self.log_message(f'Error: {str(e)}')
                time.sleep(1)  # Wait before retrying on error

    def start_copying(self):
        self.running = True
        token = self.token_entry.get().strip()
        source_channel_id = self.source_channel_id_entry.get().strip()
        target_channel_id = self.target_channel_id_entry.get().strip()

        if not token or not source_channel_id or not target_channel_id:
            self.log_message("Please fill in all fields.")
            return

        # Fetch initial set of messages
        self.fetch_messages(token, source_channel_id)
        
        # Start listening for new messages
        self.listener_thread = threading.Thread(target=self.listen_for_new_messages, args=(token, source_channel_id, target_channel_id))
        self.listener_thread.daemon = True
        self.listener_thread.start()

    def stop_copying(self):
        self.running = False
        self.log_message("Stopped copying.")
        if hasattr(self, 'listener_thread'):
            self.listener_thread.join()

if __name__ == "__main__":
    root = tk.Tk()
    app = MessageCopierApp(root)
    root.mainloop()
