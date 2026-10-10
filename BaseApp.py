import socket
import threading
import time
import datetime
import os
import json


#SERVER = socket.gethostbyname(socket.gethostname()) #Automatically gets IPv4 of device
SERVER = "192.168.129.230"
running = True
active = True
session_log = []

def send_messages(x, session_log):
        global active
        while not active:
            try:
                message_send = input(">") #Message payload, to encrypt or something
                if message_send == "-DISCONNECT-":
                    print("===You have closed this conversation===")
                    x.close()
                    active = True
                    break

                elif active:
                    print("===Partner has closed the conversation===")
                    break

                else:    
                    x.send(message_send.encode())
                    session_log.append("You: " + message_send)
                    print("You: " + message_send)

            except (OSError, ConnectionResetError):
                print("===Partner has closed the conversation===")
                active = True
                break

def receive_messages(x, session_log):
    global active
    while not active:
        try:
            message_receive = x.recv(1024).decode()
            if message_receive == "-DISCONNECT-":
                print("===Partner has closed the conversation===")
                active = True
                break

            elif not message_receive:
                print("===Partner has closed the conversation===")
                active = True
                break

            else:
                session_log.append("Partner: " + message_receive)
                print("Partner: " + message_receive) #Receives message payload from client

        except (OSError, BrokenPipeError):
            print("===Partner has closed the conversation===")
            active = True
            break

def write_chat_log(session_log):
    if not session_log:
        return

    new_entry = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "messages": session_log
    }
    history = []
    if os.path.exists("chat_log.json"):
        with open("chat_log.json", "r") as file:
            try:
                history = json.load(file) 
            except json.JSONDecodeError:
                history = [] 

    history.append(new_entry)

    with open("chat_log.json", "w") as file:
        json.dump(history, file) 

def view_chat_log():
    if not os.path.exists("chat_log.json"):
        print("No past chat log found")
        return

    with open("chat_log.json", "r") as file:
        history = json.load(file)

    if not history:
        print("No past chat log found")

    print("=== SAVED CHAT SESSIONS ===")
    for index, session in enumerate(history):
        print(f"[{index}] Session Date: {session['timestamp']}")

    try:
        choice = int(input("\nSelect a session number to read: "))
        selected = history[choice]
        
        print(f"===Chat Log for {selected['timestamp']}===")
        for msg in selected['messages']:
            print(msg)
        print("------------------------------------------\n")
    except (IndexError, ValueError):
        print("Invalid selection.")

while running:
    active = True
    session_log = []

    while active:
        choice = input("Do you want to host (1) or connect (2) or view chat logs (3) or close application (4): ")

        if choice == "1":
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind((SERVER, 3000))
            server.listen()

            client, addr = server.accept()
            print(f"===Server is listening on {addr}===")
            print("===Type '-DISCONNECT-' to end conversation===")
            active = False

        elif choice == "2":
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((SERVER, 3000)) #If you want to connect to a specific IPv4, replace SERVER with that IPv4
            print(f"===Client successfully connected to {SERVER}===")
            print("===Type '-DISCONNECT-' to end conversation===")
            active = False

        elif choice == "3":
            view_chat_log()

        elif choice == "4":
            print("===Closing Application===")
            active = False
            running = False

        else:
            print("===Please select an option from what is shown===")

    if not active and running:
        sending_thread = threading.Thread(target=send_messages, args=(client, session_log))
        receiving_thread = threading.Thread(target=receive_messages, args=(client, session_log))

        sending_thread.start()
        receiving_thread.start()

        while not active:
            time.sleep(0.5)

        try:
            client.shutdown(socket.SHUT_RDWR)
            client.close()
        except OSError:
            pass

        sending_thread.join(timeout=1.0)
        receiving_thread.join(timeout=1.0)
        print("===Connection closed===")

    write_chat_log(session_log)