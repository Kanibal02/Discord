import tkinter as tk
from tkinter import scrolledtext
import requests
import time
import threading

class SpamBotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Discord Spam Bot")
        self.root.resizable(False, False)  # Make the UI not resizable

        self.token_label = tk.Label(root, text="Enter Tokens (comma separated):")
        self.token_label.pack()

        self.token_entry = scrolledtext.ScrolledText(root, height=5, width=50)
        self.token_entry.pack()

        self.group_id_label = tk.Label(root, text="Enter Group DM ID:")
        self.group_id_label.pack()

        self.group_id_entry = tk.Entry(root, width=50)
        self.group_id_entry.pack()

        self.message_label = tk.Label(root, text="Enter Message:")
        self.message_label.pack()

        self.message_entry = tk.Entry(root, width=50)
        self.message_entry.pack()

        self.start_button = tk.Button(root, text="Start Spamming", command=self.start_spamming)
        self.start_button.pack()

        self.stop_button = tk.Button(root, text="Stop Spamming", command=self.stop_spamming)
        self.stop_button.pack()

        self.log = scrolledtext.ScrolledText(root, height=10, width=50)
        self.log.pack()

        self.threads = []
        self.running = False

    def log_message(self, message):
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)

    def send_ring_message(self, group_dm_id, message, token):
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }
        url = f'https://discord.com/api/v9/channels/{group_dm_id}/messages'
        payload = {
            'content': message,
            'tts': False
        }
        
        while self.running:
            start_time = time.time()
            for _ in range(3):
                response = requests.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    self.log_message(f'Successfully sent message')
                elif response.status_code == 429:  # Rate limit response
                    retry_after = response.json().get('retry_after', 0)
                    self.log_message(f'Rate limited. Retrying after {retry_after} seconds.')
                    time.sleep(retry_after)
                else:
                    self.log_message(f'Failed to send message: {response.status_code} - {response.text}')
                
                elapsed_time = time.time() - start_time
                sleep_time = max(0, 1 / 3 - elapsed_time)
                time.sleep(sleep_time)

    def start_spamming(self):
        self.running = True
        tokens = self.token_entry.get("1.0", tk.END).strip().split(',')
        group_dm_id = self.group_id_entry.get().strip()
        message = self.message_entry.get().strip()

        if not tokens or not group_dm_id or not message:
            self.log_message("Please fill in all fields.")
            return

        for token in tokens:
            thread = threading.Thread(target=self.send_ring_message, args=(group_dm_id, message, token.strip()))
            thread.daemon = True  # Make the thread a daemon
            thread.start()
            self.threads.append(thread)

    def stop_spamming(self):
        self.running = False
        self.log_message("Stopped spamming.")
        # Clear the threads list
        self.threads = []

if __name__ == "__main__":
    root = tk.Tk()
    app = SpamBotApp(root)
    root.mainloop()
