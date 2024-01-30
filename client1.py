from email.utils import getaddresses
from pkgutil import get_data
import socket
import threading
import queue
import select
import tkinter
import PySimpleGUI as sg
import sqlite3
from datetime import datetime

HOST = '127.0.0.1'
PORT = 9090

isRunning = True

def data_chat(username, target_username, data, datasender, date, time):
    datachat = [username, target_username, data, datasender, date, time]
    return datachat

def create_n_connect_database():
    connect = sqlite3.connect('ChatApp.db')
    cursor = connect.cursor()
    format = f"('user' TEXT, 'target' TEXT, 'data' TEXT, 'datasender' TEXT, 'date' TEXT, 'time' TEXT)"
    create = f"CREATE TABLE IF NOT EXISTS database {format}"
    cursor.execute(create)
    return connect, cursor

def save_datachat(datachat, connect:sqlite3.Connection, cursor:sqlite3.Cursor):
    save = f"INSERT INTO database VALUES (?,?,?,?,?,?)"
    cursor.execute(save,datachat)
    connect.commit()

def get_datachat(username, target_username, cursor:sqlite3.Cursor):
    target = (username, target_username)
    get = f"SELECT * FROM database WHERE user=? AND target=?"
    fetcheddatachat = cursor.execute(get,target).fetchall()
    return fetcheddatachat

def time_HM(time):
    data = time.split(':')
    print('data:', data)
    hour = data[0]
    minute = data[1]
    output = hour+':'+minute
    return output

def connect_to_server(HOST, PORT):
    mySocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    mySocket.connect((HOST, PORT))
    return mySocket

def createBytes(message:str):
    final_message = message.encode('utf-8')
    return final_message

def disconnect_from_server(mySocket:socket.socket):
    mySocket.close()

def Communicate_with_server(mySocket:socket.socket, recvMsg_queue: queue.Queue, command_queue: queue.Queue, stop_event, username, sendMsg_queue:queue.Queue):
    read_list = [mySocket]
    write_list = [mySocket]
    recvMsg_queue.put({'Message_Type':'-type-', 'sender':'-waiting-', 'data':"-waiting-", 'target':'-waiting-'})
    while not stop_event.is_set():
        readable, writeable, _ = select.select(read_list, write_list, [], 2)
        try:
            command = command_queue.get(block=False)
            print('command:', command)
        except queue.Empty:
            pass
        else:
            if command == 'Connect':
                if mySocket in writeable:
                    send_message = 'USERNAME:'+username
                    finalmessage = createBytes(send_message)
                    mySocket.send(finalmessage)
                    print('connect message send to the server')
            elif command == 'LogOut':
                if mySocket in writeable:
                    send_message = 'LOGOUT:'+username
                    finalmessage = createBytes(send_message)
                    mySocket.send(finalmessage)
                    loggedout = True
                    print('logout message send to the server')
                    return loggedout
            elif command == 'SEND':
                if mySocket in writeable:
                    try:
                        sendclient_message = sendMsg_queue.get(block=False)
                    except queue.Empty:
                        pass
                    else:
                        finalmessage = createBytes(sendclient_message)
                        mySocket.send(finalmessage)
        if mySocket in readable and not stop_event.is_set():
            # listening for message from server
            msgRaw = mySocket.recv(1024).decode('utf-8')
            print('messageRaw:', msgRaw)
            type="-"
            sender="-"
            data="-"
            target="-"
            if msgRaw:
                msgList = msgRaw.split(':')
                if len(msgList)>0: #message send by another client format = SEND:sender_username:msg:target_username
                    if msgList[0]=='SEND':
                        type = msgList[0]
                        sender = msgList[1]
                        data= msgList[2]
                        target = msgList[3]
                        recvMsg_queue.put({'Message_Type':type, 'sender':sender, 'data':data, 'target':target})
                    elif msgList[0]=='USERS': #message send by server, USERS:list of connected usernames
                        type = msgList[0]
                        sender = msgList[1]
                        data = msgList[2]
                        target = "None"
                        recvMsg_queue.put({'Message_Type':type, 'sender':sender, 'data':data, 'target':target})
                    elif msgList[0]=='STATES': #message send by server, STATES:states of user (connected or leave/disconnect)
                        type = msgList[0]
                        sender = msgList[1]
                        data = msgList[2]
                        target = "None"
                        recvMsg_queue.put({'Message_Type':type, 'sender':sender, 'data':data, 'target':target})
                elif len(msgList)==0:
                    print("Error : Length message is zero!!")

# Class threading for client
class Client_Thread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.recvMsg_queue = args[0]
        self.command_queue = args[1]
        self.host = args[2]
        self.port = args[3]
        self.username = args[4]
        self.sendMsg_queue = args[5]
        self.args, self.kwargs = args, kwargs
        self.stop_event = threading.Event()
        
    def run(self):
        self.socket = connect_to_server(self.host, self.port)
        Communicate_with_server(self.socket, self.recvMsg_queue, self.command_queue, self.stop_event, self.username, self.sendMsg_queue)
    
    def stop(self):
        self.stop_event.set()
        disconnect_from_server(self.socket)
    
    def clone(self):
        return Client_Thread(*self.args, **self.kwargs)

def main():
    username=''
    target_username=''
    prev_username=''
    other_usernames=[]
    command_queue = queue.Queue()
    recvMsg_queue = queue.Queue()
    sendMsg_queue = queue.Queue()

    datentime = datetime.now()

    welcome_layout = [
        [sg.Text("Please Input your username:")],
        [sg.Input(key='-Username-',enable_events=True)],
        [sg.Button('Connect', key='-Connect-',disabled=True)]
    ]
    
    welcome_window = sg.Window('Welcome',welcome_layout,size=(250,150))
    while isRunning:
        welcome_event, welcome_value = welcome_window.read(timeout = 100)
        if welcome_value['-Username-'] != '':
            welcome_window['-Connect-'].update(disabled=False)
        elif welcome_value['-Username-'] == '':
            welcome_window['-Connect-'].update(disabled=True)

        if welcome_event=='-Connect-':
            username = welcome_value['-Username-']
            command_queue.put('Connect')
            break
        elif welcome_event in (None, 'Cancel', 'Exit'):
            break
    welcome_window.close()
    
    # print('username: ', username)
    client = Client_Thread(recvMsg_queue,command_queue, HOST, PORT, username, sendMsg_queue)
    client.start()

    connect, cursor = create_n_connect_database()

    main_column_layout = [
        [sg.Text('Welcome to Chat App, '+username)],
        [sg.Listbox(values=other_usernames, key='-OtherUsers-', select_mode='single', enable_events=True, size=(20,20)), sg.Multiline(key='-Status-', disabled=True, size=(50,10))]
    ]

    chat_column_layout = [
        [sg.Multiline(key='-ChatStatus-',disabled=True, autoscroll=True, size=(50,20))],
        [sg.Multiline(key='-InputMessage-', size=(50,2))],
        [sg.Button('Send', key='-Send-', disabled=True, size=(50,3))]
    ]

    Chat_app_layout = [
        [
            sg.Column(main_column_layout),
            sg.VSeparator(),
            sg.Column(chat_column_layout)
        ]
    ]

    loggedout = False

    window = sg.Window('Chat App', Chat_app_layout,size=(1000,500))
    while isRunning:
        event, value = window.read(timeout=100)
        
        if event == '-OtherUsers-':
            selected = value[event]
            target_username = selected[0]
            index = other_usernames.index(target_username)
            window['-OtherUsers-'].Widget.itemconfig(index, bg='white', fg='black')
            if selected:
                window['-Send-'].update(disabled=False)
                if prev_username == '':
                    prev_username = target_username
                    datachat = get_datachat(username,target_username,cursor)
                    if datachat == []:
                        pass
                    else:
                        for n in range (0,len(datachat)):
                            dchat = datachat[n][2]
                            dsender = datachat[n][3]
                            dtime = datachat[n][5]
                            disp_time = time_HM(dtime)
                            if dsender == 'other':
                                window['-ChatStatus-'].update(dchat+'\n'+disp_time+'\n', append=True, justification=tkinter.LEFT)
                            else:
                                window['-ChatStatus-'].update(dchat+'\n'+disp_time+'\n', append=True, justification=tkinter.RIGHT)
                elif prev_username != '':
                    check_username = prev_username
                    if check_username == target_username:
                        pass
                    else:
                        prev_username = target_username
                        window['-ChatStatus-'].update('')
                        datachat = get_datachat(username,target_username,cursor)
                        for n in range(0,len(datachat)):
                            dchat = datachat[n][2]
                            dsender = datachat[n][3]
                            dtime = datachat[n][5]
                            disp_time = time_HM(dtime)
                            if dsender == 'other':
                                window['-ChatStatus-'].update(dchat+'\n'+disp_time+'\n', append=True, justification=tkinter.LEFT)
                            else:
                                window['-ChatStatus-'].update(dchat+'\n'+disp_time+'\n', append=True, justification=tkinter.RIGHT)

        if event == '-Send-' and window['-InputMessage-'] != '':
            data = value['-InputMessage-']
            final_message = 'SEND:'+username+':'+data+':'+target_username
            sendMsg_queue.put(final_message)
            command_queue.put('SEND')
            dateMessage = str(datentime.date())
            timeMessage = str(datentime.time())
            disp_time = time_HM(timeMessage)
            window['-ChatStatus-'].update(data+'\n'+disp_time+'\n', append=True, justification=tkinter.RIGHT)
            window['-InputMessage-'].update('')
            dataChat = data_chat(username, target_username, data, 'user', dateMessage, timeMessage) 
            save_datachat(dataChat,connect,cursor)

        try:
            received_message = recvMsg_queue.get(block=False)
        except queue.Empty:
            pass
        else:
            sender = received_message['sender']
            messageType = received_message['Message_Type']
            if sender == 'server':
                if messageType == 'STATES':
                    data = received_message['data']
                    dateMessage = str(datentime.date())
                    timeMessage = str(datentime.time())
                    disp_time = time_HM(timeMessage)
                    window['-Status-'].update(data+'~'+disp_time+'\n',append=True)
                elif messageType == 'USERS':
                    other = received_message['data'].split(',')
                    other.remove(username)
                    other_usernames = other
                    window['-OtherUsers-'].update(other_usernames)
            else:
                if messageType == 'SEND':
                    if target_username==sender: 
                        data = received_message['data']
                        dateMessage = str(datentime.date())
                        timeMessage = str(datentime.time())
                        disp_time = time_HM(timeMessage)
                        window['-ChatStatus-'].update(data+'\n'+disp_time+'\n', append=True, justification=tkinter.LEFT)
                        dataChat = data_chat(username, sender, data, 'other', dateMessage, timeMessage)
                        save_datachat(dataChat,connect,cursor)
                    else:
                        dateMessage = str(datentime.date())
                        timeMessage = str(datentime.time())
                        disp_time = time_HM(timeMessage)
                        data = received_message['data']
                        sender = received_message['sender']
                        index = other_usernames.index(sender)
                        window['-OtherUsers-'].Widget.itemconfig(index, bg = 'red', fg = 'blue' )
                        pending_warning = 'you got a message from '+sender
                        window['-Status-'].update(pending_warning+'\n', append=True)
                        dataChat = data_chat(username,sender, data, 'other', dateMessage, timeMessage)
                        save_datachat(dataChat,connect,cursor)

        if event in (None, 'Cancel', 'Exit'):
            command_queue.put('LogOut')
            if loggedout == True:
                client.stop()
            break

    window.close()
    client.stop()
    

if __name__ == '__main__':
    main()

    