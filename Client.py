import socket
import json
import os
import threading
import tkinter as tk
import time
from tkinter import scrolledtext, filedialog
from datetime import datetime
from glob import glob
from pathlib import Path
import tkinter.font as tkFont

class ChatClient:
    def __init__(self, host='127.0.0.1', port=8888):
        # Initialize client with target server host and port
        self.host = host
        self.port = port
        # Socket for the client
        self.client_socket = None
        # User name of the client
        self.name = ""
        self.setup_socket()
        self.create_gui()
        self.start_receive_thread()

    def log_error(self, error_message):
        print(f"ERROR: {error_message}")

    def setup_socket(self):
        # Establish connection to the server
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.host, self.port))
        except Exception as e:
            self.log_error(f"Failed to connect to server: {e}")
            exit(1)

    def send_file(self, file_path):
        try:
            # Send a file to the server
            with open(file_path, "rb") as file:
                file_data = file.read()
            header = {
                "type": "file",
                "filename": os.path.basename(file_path),
                "length": len(file_data),
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            self.client_socket.send(json.dumps(header).encode())
            self.client_socket.sendall(file_data)
            time.sleep(1)  # Wait to ensure file is sent before refreshing the file list
            self.refresh_file_list()
        except Exception as e:
            self.log_error(f"Failed to send file {file_path}: {e}")

    def receive_file(self, message, data_length):
        try:
            # Receive a file from the server
            self.message_display.insert("end", f"[{message['timestamp']}] {message['name']}: sending file: {message['filename']}\n")
            self.message_display.see("end")
            self.window.update()
            data = b''
            while len(data) < data_length:
                packet = self.client_socket.recv(1024)
                if not packet:
                    break
                data += packet
            return data
        except Exception as e:
            self.log_error(f"Failed to recieve file: {e}")

    def save_file(self, client_name, file_data, filename):
        try:
            # Save the received file locally
            file_path = f'files/{client_name}_{datetime.now().strftime("%Y%m%d%H%M%S")}_{filename}'
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb') as file:
                file.write(file_data)
            print(f"File received and saved to {file_path}")
            self.refresh_file_list()  # Refresh the file list to include the new file 
        except Exception as e:
            self.log_error(f"Failed to save file {filename}: {e}")


    def refresh_file_list(self):
        try:
            # Refresh the list of files shown in the GUI
            self.file_list.delete(0, tk.END)  # Clear current list
            for f in sorted(Path('files/').glob("*"+self.name+"*")):
                self.file_list.insert(tk.END, f)  # Add files to the list
            self.file_list.bind("<<ListboxSelect>>", self.open_file)
            self.window.geometry("600x800")  # Adjust window size if needed
        except Exception as e:
            self.log_error(f"Failed to refresh file list: {e}")

    def refresh_user_list(self, users):
        try:
            # Updates the GUI component with the current list of users
            self.user_list_box.delete(0, tk.END)  # Clear the current list
            for user in users:
                self.user_list_box.insert(tk.END, user)
        except Exception as e:
            self.log_error(f"Failed to refresh user list: {e}")

    def send_message(self):
        try:
            # Send a text message to the server
            message_text = self.message_entry.get()
            if message_text:
                message = {"text": message_text, "type": "text"}
                self.client_socket.send(json.dumps(message).encode())
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.message_display.insert("end", f"[{timestamp}] You: {message_text}\n", "sender")
                self.message_display.see("end")
                self.message_entry.delete(0, "end")
                self.window.update()
        except Exception as e:
            self.log_error(f"Failed to send message: {e}")

    def receive_messages(self):
        try:
            # Receive messages from the server
            while True:
                data = self.client_socket.recv(1024)
                if not data:
                    break
                message = json.loads(data.decode())
                message_type = message["type"]
                if message_type == "text":
                    self.message_display.insert("end", f"[{message['timestamp']}] {message['name']}: {message['text']}\n")
                    self.message_display.see("end")
                    self.window.update()
                elif message_type == "file":
                    file_data = self.receive_file(message, message["length"])
                    self.save_file(self.name, file_data, message['filename'])
                elif message_type == "system":
                    self.message_display.insert("end", f"[{message['timestamp']}] {message['text']}\n", "system")
                elif message_type == "user_list":
                    self.refresh_user_list(message["users"])
        except Exception as e:
            self.log_error(f"Failed to recieve message: {e}")

    def choose_file(self):
        try:
            # Open a dialog to choose a file to send
            file_path = filedialog.askopenfilename()
            if file_path:
                self.send_file(file_path)
        except Exception as e:
            self.log_error(f"Failed to choose file: {e}")


    def set_name(self):
        # Set the client's user name
        self.name = self.name_entry.get()
        self.name_entry.config(state="disabled")
        self.name_button.pack_forget()
        self.client_socket.send(self.name.encode())
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.message_display.insert("end", f"[{timestamp}] Welcome to the chat {self.name}\n", "system")
        self.message_display.see("end")
        self.create_file_widgets()
        self.window.update()

    def create_gui(self):
        # Create the GUI for the chat client
        try:
            self.window = tk.Tk()
            self.window.title("QuickChat")
            self.window.geometry("600x800")  # Set initial window size
            self.window.tk.call('source', 'Azure/azure.tcl')
            self.window.tk.call('set_theme', 'dark')

            self.create_name_widgets()
            self.create_message_widgets()
            self.create_user_list_widgets()
        except tk.TclError as e:
            self.log_error(f"Modern theme not available, using default. {e}")
        except Exception as e:
            self.log_error(f"Failed to create Graphical User Interface: {e}")

    def create_user_list_widgets(self):
        try:
            # Creates GUI components for displaying the list of users
            user_list_frame = tk.Frame(self.window)
            user_list_frame.pack(padx=10, pady=5, fill=tk.X, side=tk.RIGHT)
            tk.Label(user_list_frame, text="Connected Users").pack()
            self.user_list_box = tk.Listbox(user_list_frame)
            self.user_list_box.pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            self.log_error(f"Failed to create Graphical User Interface - User list widgets: {e}")

    def create_message_widgets(self):
        try:
            # Create widgets for message display and sending
            message_frame = tk.Frame(self.window)
            message_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

            font = tkFont.Font(family="Helvetica", size=12)

            chat_heading = tk.Label(message_frame, text="Chat", font=tkFont.Font(family="Helvetica", size=14, weight="bold"))
            chat_heading.pack(pady=(0,5))

            self.message_display = scrolledtext.ScrolledText(message_frame, font=font, wrap=tk.WORD)
            self.message_display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
            self.message_display.tag_config('sender', foreground="#61d461")
            self.message_display.tag_config('system', foreground="#ffd633")

            entry_frame = tk.Frame(message_frame)
            entry_frame.pack(fill=tk.X, padx=10, pady=5)

            self.message_entry = tk.Entry(entry_frame, font=font)
            self.message_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

            send_file_button = tk.Button(entry_frame, text="Send File", command=self.choose_file, font=font)
            send_file_button.pack(side=tk.RIGHT)

            send_button = tk.Button(entry_frame, text="Send", command=self.send_message, font=font)
            send_button.pack(side=tk.RIGHT, padx=(5, 0))
        except Exception as e:
            self.log_error(f"Failed to create Graphical User Interface - chat message widgets: {e}")

    def create_name_widgets(self):
        try:
            # Create widgets for setting the client's user name
            name_frame = tk.Frame(self.window)
            name_frame.pack(padx=10, pady=5, fill=tk.X)

            font = tkFont.Font(family="Helvetica", size=12)

            tk.Label(name_frame, text="Enter your name:", font=font).pack(side=tk.LEFT)

            self.name_entry = tk.Entry(name_frame, font=font)
            self.name_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

            self.name_button = tk.Button(name_frame, text="Set Name", command=self.set_name, font=font)
            self.name_button.pack(side=tk.RIGHT)
        except Exception as e:
            self.log_error(f"Failed to create Graphical User Interface - name setting widgets: {e}")

    def create_file_widgets(self):
        try:
            # Create widgets for displaying and interacting with files
            file_frame = tk.Frame(self.window)
            file_frame.pack(padx=10, pady=5, fill=tk.X)

            font = tkFont.Font(family="Helvetica", size=12)

            files_heading = tk.Label(file_frame, text="Files", font=tkFont.Font(family="Helvetica", size=14, weight="bold"))
            files_heading.pack(pady=(0,5))

            self.file_list = tk.Listbox(file_frame, font=font)
            self.file_list.pack(expand=True, fill=tk.BOTH)

            self.refresh_file_list()  # Populate the file list
        except Exception as e:
            self.log_error(f"Failed to create Graphical User Interface - file widgets: {e}")
    

    def open_file(self, event):
        try:
            # Open a file when selected from the list
            selection = self.file_list.curselection()
            if selection:
                index = selection[0]
                data = self.file_list.get(index)
                os.startfile(data)
        except Exception as e:
            self.log_error(f"Failed to open file: {e}")


    def start_receive_thread(self):
        try:
        # Start a thread to receive messages from the server
            threading.Thread(target=self.receive_messages, daemon=True).start()
        except Exception as e:
            self.log_error(f"Failed to open thread for message reciept: {e}")

    def run(self):
        # Run the GUI
        self.window.mainloop()

    def cleanup(self):
        # Clean up the socket connection on exit
        try:
            self.client_socket.shutdown(socket.SHUT_RDWR)
            self.client_socket.close()
        except Exception as e:
            self.log_error(f"Cleanup failed: {e}")

if __name__ == '__main__':
    client = ChatClient()
    try:
        client.run()
    finally:
        client.cleanup()