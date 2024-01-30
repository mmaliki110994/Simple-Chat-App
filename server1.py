import socket
import queue
import threading
import time

HOST = '127.0.0.1'
PORT = 9090

user_limit = 10
active_username =[]
clients = []
isRunning = True

def broadcast(message):
    for client in clients:
        client.send(message.encode('utf-8'))
        print(message)

def client_handler(client):
    # format = SEND:sender:content_message:target
    while isRunning:
        message = client.recv(1024).decode('utf-8')
        data = message.split(':')
        if data[0] == 'SEND':
            target = data[3]
            index = active_username.index(target)
            target_client = clients[index]
            print('target:', target_client)
            print('message:', message)
            target_client.send(message.encode('utf-8'))
            print('message sent')
        

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    print(f"Server is Running!")
    while isRunning:
        server.listen(user_limit)
        client, address = server.accept()
        clients.append(client)
        print('client:',clients)
        print(f"Successfully connected to client {address[0]} {address[1]}")
        message = client.recv(1024).decode('utf-8')
        print('message:', message)
        header = message.split(':')[0]
        print('header: ', header)
        if header == 'USERNAME':
            client_username = message.split(':')[-1]
            print('client username:', client_username)
            # active_username.append(client_username)
            active_username.append(client_username)
            STATES_message = "STATES:"+'server:'+client_username+" is connected to the server"
            broadcast(STATES_message)
            time.sleep(0.5)
            USERS_message = "USERS:"+'server:'+','.join(active_username)
            broadcast(USERS_message)
        else:
            print('Error: this is not Message meant for server')
        threading.Thread(target=client_handler, args=(client,)).start()

if __name__ == '__main__':
    main()
