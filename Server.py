import socket
import threading
import json
import os
from datetime import datetime

class ChatServer:
    def __init__(self, host='0.0.0.0', port=8888):
        # Initialize server with host and port
        self.host = host
        self.port = port
        # List to store client connections
        self.clients = []
        self.client_names = {}  # Maps client sockets to names
        # Server socket
        self.server_socket = None
        self.setup_socket()

    def setup_socket(self):
        # Create the server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Reuse address to avoid 'address already in use' error
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind the socket to host and port
        self.server_socket.bind((self.host, self.port))
        # Listen for connections, allowing up to 5 pending connections
        self.server_socket.listen(5)
        print(f"Server is listening on {self.host}:{self.port}")

    def accept_connections(self):
        # Accept incoming connections
        while True:
            client_socket, client_address = self.server_socket.accept()
            self.clients.append(client_socket)
            print(f"Accepted connection from {client_address}")

            # Handle each client in a separate thread
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket, client_address))
            client_thread.start()

    def handle_client(self, client_socket, address):
        # Receive the client's name
        client_name = client_socket.recv(1024).decode()
        print(f"{client_name} has joined the chat.")
        # Broadcast system message when a user joins
        self.broadcast_system_message(f"{client_name} has joined the chat.", client_socket)
        self.client_names[client_socket] = client_name
        self.broadcast_user_list()

        while True:
            try:
                data = client_socket.recv(1024).decode("utf-8")
                if not data:
                    # Broadcast system message when a user leaves
                    self.broadcast_system_message(f"{client_name} has left the chat.", client_socket)
                    print(f"{client_name} disconnected.")
                    del self.client_names[client_socket]  # Remove client from the names list
                    self.broadcast_user_list()  # Broadcast updated user list
                    break

                message = json.loads(data)
                self.process_message(client_socket, client_name, message)

            except (json.JSONDecodeError, UnicodeDecodeError, ConnectionError) as e:
                print(f"Error: {e}")
                break

        # Remove client from the list and close the connection
        self.clients.remove(client_socket)
        client_socket.close()

    def process_message(self, client_socket, client_name, message):
        # Process and dispatch messages based on their type
        message_type = message["type"]

        if message_type == "text":
            # Broadcast text messages to all clients
            self.broadcast_text(client_name, message, client_socket)
        elif message_type == "file":
            # Receive, save, and forward files
            file_data = self.receive_file(client_socket, message["length"])
            if file_data:
                self.save_file(client_name, file_data, message['filename'])
                self.forward_file(client_socket, client_name, file_data, message)

    def broadcast_system_message(self, text, client_socket):
        # Broadcast system messages (e.g., user joined, user left)
        timestamp = datetime.now().strftime("%H:%M:%S")
        broadcast_data = {
            "timestamp": timestamp,
            "text": text,
            "type": "system"
        }
        self.broadcast(broadcast_data, client_socket)

    def broadcast_user_list(self):
        # Broadcasts the list of connected users to all clients
        user_list = list(self.client_names.values())
        message = {"type": "user_list", "users": user_list}
        self.broadcast(message, None)  # Send to all clients

    def broadcast_text(self, client_name, message, sender_socket):
        # Broadcast text messages to all clients except the sender
        timestamp = datetime.now().strftime("%H:%M:%S")
        broadcast_data = {
            "timestamp": timestamp,
            "name": client_name,
            "text": message['text'],
            "type": message["type"]
        }
        # Debug print the message
        print(f"(Debugging) {timestamp} - {client_name}: {message['text']}")
        self.broadcast(broadcast_data, sender_socket)

    def broadcast(self, message, sender_socket):
        # Send a message to all connected clients except the sender
        for client in self.clients:
            if client != sender_socket:
                try:
                    client.send(json.dumps(message).encode())
                except:
                    # Remove the client if message sending fails
                    self.clients.remove(client)

    def receive_file(self, client_socket, data_length):
        # Receive a file from a client
        data = b''
        try:
            while len(data) < data_length:
                packet = client_socket.recv(1024)
                if not packet:
                    raise ConnectionError("File transfer interrupted")
                data += packet
            if len(data) != data_length:
                raise ValueError("File data incomplete")
        except Exception as e:
            print(f"Error receiving file: {e}")
            return None
        return data

    def save_file(self, client_name, file_data, filename):
        # Save received files in a designated directory
        directory = "files"
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        file_path = os.path.join(directory, f"{client_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}")
        with open(file_path, 'wb') as file:
            file.write(file_data)
        print(f"File received and saved to {file_path}")

    def forward_file(self, sender_socket, sender_name, file_data, message):
        # Forward a file to all clients except the sender
        header = {
            "type": "file",
            "timestamp": message["timestamp"],
            "name": sender_name,
            "filename": message["filename"],
            "length": message["length"]
        }
        for client in self.clients:
            if client != sender_socket:
                try:
                    client.send(json.dumps(header).encode())
                    client.sendall(file_data)
                except:
                    # Remove the client if message sending fails
                    self.clients.remove(client)

    def handle_cleanup(self):
        # Cleanup resources on server shutdown
        try:
            self.server_socket.shutdown(socket.SHUT_RDWR)
            self.server_socket.close()
        except Exception as e:
            print(f"Error during shutdown: {e}")

if __name__ == '__main__':
    chat_server = ChatServer()
    try:
        chat_server.accept_connections()
    finally:
        chat_server.handle_cleanup()