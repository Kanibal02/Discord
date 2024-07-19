# Made with chat GPT

import tkinter as tk
from tkinter import messagebox
import requests
import threading
import time

# Function to leave the group DM
def leave_group_dm(token, channel_id):
    url = f'https://discord.com/api/v10/channels/{channel_id}'
    headers = {'Authorization': f'{token}'}
    response = requests.delete(url, headers=headers)
    
    if response.status_code == 204:
        print(f"Successfully left the group DM: {response.status_code}")
        return True
    elif response.status_code == 429:
        retry_after = response.json().get('retry_after', 1)
        print(f"Rate limited. Retry after: {retry_after} seconds")
        time.sleep(retry_after)
        return leave_group_dm(token, channel_id)
    else:
        print(f"Failed to leave the group DM: {response.status_code} - {response.text}")
        return False

# Function to continuously check and leave the group DM
def monitor_group_dm():
    token = token_entry.get()
    channel_id = group_dm_id_entry.get()
    if not token or not channel_id:
        messagebox.showerror("Error", "Both token and Group DM ID are required")
        return

    while True:
        try:
            print(f"Checking if in group DM {channel_id}...")
            if leave_group_dm(token, channel_id):
                status_label.config(text="Left the group DM", fg="green")
                print("Successfully left the group DM")
                time.sleep(10)  # Wait for a longer interval after successfully leaving
            else:
                status_label.config(text="Failed to leave the group DM", fg="red")
                print("Failed to leave the group DM")
                time.sleep(1)  # Retry after a short interval if failed
        except Exception as e:
            status_label.config(text=f"Error: {str(e)}", fg="red")
            print(f"Error: {str(e)}")
            break  # Stop the loop if there's an exception to avoid spamming errors

# Function to start the monitoring in a separate thread
def start_monitoring():
    monitoring_thread = threading.Thread(target=monitor_group_dm)
    monitoring_thread.daemon = True
    monitoring_thread.start()

# Set up the GUI
root = tk.Tk()
root.title("Discord Group DM Leaver")
root.resizable(False, False)  # Make the window non-resizable

tk.Label(root, text="Discord Token:").grid(row=0, column=0, padx=10, pady=10)
token_entry = tk.Entry(root, width=50)
token_entry.grid(row=0, column=1, padx=10, pady=10)

tk.Label(root, text="Group DM ID:").grid(row=1, column=0, padx=10, pady=10)
group_dm_id_entry = tk.Entry(root, width=50)
group_dm_id_entry.grid(row=1, column=1, padx=10, pady=10)

start_button = tk.Button(root, text="Start Leaving", command=start_monitoring)
start_button.grid(row=2, column=0, columnspan=2, pady=20)

status_label = tk.Label(root, text="", fg="blue")
status_label.grid(row=3, column=0, columnspan=2, pady=10)

root.mainloop()
