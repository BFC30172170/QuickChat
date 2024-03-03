#Import required modules and advise user to retry if fails
try:
    import socket
    import threading
    import json
    import os
    from datetime import datetime
except ImportError:
    raise ImportError('Failed to start, close and retry')

#Function to handle client connections
def handle_client(client_socket, address):
    print(f"Accepted connection from {address}")
    
    #Receive the client's name
    
    client_name = client_socket.recv(1024).decode()
    print(f"{client_name} has joined the chat.")
    
    #Create message handle loop
    while True:
        try:
            data = client_socket.recv(1024).decode("utf-8") #Assign JSON data to data variable
            
            #If no data received, the client has disconnected
            if not data:
                print(f"{client_name} disconnected.")
                break
                    
            message = json.loads(data) #Load message from clients from JSON data
            message_type = message["type"]

            if message_type == "text":
                timestamp = datetime.now().strftime("%H:%M:%S") #Format timestamp to hour:min:sec

                broadcastData = {"timestamp": timestamp, "name": client_name, "text": message['text'], "type": message["type"]} #Create dictionary variable for the data / timestamp and senders name.
                
                #Debugging to display the received message with timestamp and sender's name
                print(f"(Debugging) {timestamp} - {client_name}: {message['text']}")
                    
                #Broadcast the message to all connected clients
                broadcast(broadcastData, client_socket)
            elif message_type == "file":
                file_data = receive_file(client_socket, message["length"])
                save_file(client_name, file_data)
                forward_file(client_socket, client_name, file_data, message)

        except json.JSONDecodeError:
            print("Invalid JSON received")

        except UnicodeDecodeError:
            print("Binary data received, expected JSON")
        
        except ConnectionError as e:
            print(f"Connection error with {client_name}: {e}")
            break
        
        except Exception as e:
            print(f"Unexpected error: {e}")
            break

def forward_file(sender_socket, sender_name, file_data, message):
    header = {"type": "file", "timestamp":message["timestamp"],"name":sender_name, "filename": message["filename"], "length": message["length"] }
    for client in clients:
        if client != sender_socket:
            try:
                client.send(json.dumps(header).encode())
                client.sendall(file_data)
            except:
                clients.remove(client)
    
def receive_file(client_socket, data_length):
    data = b''
    try:
        while len(data) < data_length:
            packet = client_socket.recv(1024)
            if not packet:
                raise ConnectionError("File transfer interupted")
            data += packet
        if len(data) != data_length:
                raise ValueError("File data incomplete")
    except Exception as e:
        print(f"Error receiving file: {e}")
        return None
    return data

# Function to save received file data
def save_file(client_name, file_data):
    directory = "files"
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    file_path = os.path.join(directory, f"{client_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}")
    with open(file_path, 'wb') as file:
        file.write(file_data)
    print(f"File received and saved to {file_path}")
    
#Function to broadcast a message to all connected clients
def broadcast(message, sender_socket):
    #Loop through all connected clients
    for client in clients:
        #If client is not the sender
        if client != sender_socket:
            #Try to send the message or remove the client
            try:
                #Encode the message as JSON and send it
                client.send(json.dumps(message).encode())
            except:
                #Remove the client if it's no longer available
                clients.remove(client)


def create_socket_bind(host='0.0.0.0',port=8888):
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Create a dictionary data set of socket data using the socket library
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port)) #Create a bind connection for clients using the library functionality and set server / port
    server_socket.listen(5)  #Allow up to 5 connections
    print(f"Server is listening on {host}:{port}")
    global clients #List to store connected client sockets
    clients = []


def handle_cleanup():
    try:
        server_socket.shutdown(socket.SHUT_RDWR)
        server_socket.close()
    except Exception as e:
        print(f"Error during shutdown: {e}")

def main():
    try:
        create_socket_bind()

        #Loop the program until exit
        while True:
            client_socket, client_address = server_socket.accept()
            clients.append(client_socket)  #Add the client socket to the list of connected clients

            #Start a new thread to handle the client
            global client_thread
            client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
            client_thread.start()
    finally:
        handle_cleanup()


if __name__=='__main__':
    main()
    
