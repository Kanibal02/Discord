import tkinter as tk

def convert_text(event):
    input_text = input_box.get("1.0", tk.END).strip().lower()
    output_text = " ".join([
        f":regional_indicator_{char}:" if char.isalpha() else
        f":number_{char}:" if char.isdigit() else
        ":grey_exclamation:" if char == "!" else
        ":grey_question:" if char == "?" else
        "     " for char in input_text
    ])
    output_box.config(state=tk.NORMAL)
    output_box.delete("1.0", tk.END)
    output_box.insert(tk.END, output_text)
    output_box.config(state=tk.DISABLED)

def copy_to_clipboard():
    output_text = output_box.get("1.0", tk.END).strip()
    if output_text:
        root.clipboard_clear()  # Clear the clipboard
        root.clipboard_append(output_text)
        root.update()  # Ensure it stays on the clipboard

root = tk.Tk()
root.title("Text Converter")
root.resizable(False, False)  # Disable window resizing

input_label = tk.Label(root, text="Input:")
input_label.pack()

input_box = tk.Text(root, height=10, width=50)
input_box.pack()
input_box.bind("<KeyRelease>", convert_text)

output_label = tk.Label(root, text="Output:")
output_label.pack()

output_box = tk.Text(root, height=10, width=50, state=tk.DISABLED)
output_box.pack()

copy_button = tk.Button(root, text="Copy Text", command=copy_to_clipboard)
copy_button.pack()

root.mainloop()

# Made with chat gpt and kanibal
# Use without asking
