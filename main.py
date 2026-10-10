import socket
import base64
import threading
import time
import datetime
import os
import json
from Crypto.PublicKey import RSA
import crypto_utils

# SERVER = socket.gethostbyname(socket.gethostname()) #Automatically gets IPv4 of device
SERVER = "192.168.129.230"
running = True
active = False
session_log = []


def send_messages(x, session_log, my_private_key, partner_public_key):
    
    global active

    # while not connected
    while active:
        try:
            # Message payload
            message_send = input(">") 


            if message_send == "-DISCONNECT-":
                print("===You have closed this conversation===")
                x.close()
                active = False
                break

            if not active :
                print("===Partner has closed the conversation===")
                break

            else:
                encrypted_packet = crypto_utils.build_secure_packet(
                    message_send.encode("utf-8"), my_private_key, partner_public_key
                )

                x.sendall(encrypted_packet)
                # x.send(message_send.encode())

                # encode in base64, python string limitaiton, cannot append string + bytes
                session_log.append(
                    "You: " + base64.b64encode(encrypted_packet).decode("utf-8")
                )
                
                print("You: " + message_send)

        except (OSError, ConnectionResetError):
            print("===Partner has closed the conversation===")
            active = False
            break


def receive_messages(x, session_log, my_private_key, partner_public_key):

    global active

    while active:
        try:
            raw_message_receive = x.recv(4096)

            if not raw_message_receive:
                print("===Partner has closed the conversation===")
                active = False
                break

            else:
                decrypted_message = crypto_utils.unpack_secure_packet(
                    raw_message_receive, my_private_key, partner_public_key
                )

                if decrypted_message.decode("utf-8") == "-DISCONNECT-":
                    print("===Partner has closed the conversation===")
                    active = False
                    break

                # stores to chat log through recieve message => encode in base64, pyhton strings limitation
                session_log.append(
                    "Partner: " + base64.b64encode(raw_message_receive).decode("utf-8")
                )
                # session_log.append("Partner: " + decrypted_message.decode("utf-8"))
                print(
                    "Partner: " + decrypted_message.decode("utf-8")
                )  # Receives message payload from client


        except (OSError, BrokenPipeError):
            print("===Partner has closed the conversation===")
            active = False
            break
        except (ValueError) as e:
            print(f"Error: {e}")
            active = False
            break


def write_chat_log(session_log):
    if not session_log:
        return

    new_entry = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "messages": session_log,
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


# decrypt the chat log
def view_chat_log():
    if not os.path.exists("chat_log.json"):
        print("No past chat log found")
        return

    with open("chat_log.json", "r") as file:
        history = json.load(file)

    if not history:
        print("No past chat log found")

    currentRole = input("View log as server (1) or client (2): ")

    if currentRole == "1":
        my_private_key = RSA.import_key(
            open("server/server.key", "rb").read(), passphrase="serverPwd"
        )
        partner_public_key = crypto_utils.get_public_key_from_cert("client/client.crt")

    elif currentRole == "2":
        my_private_key = RSA.import_key(
            open("client/client.key", "rb").read(), passphrase="clientPwd"
        )
        partner_public_key = crypto_utils.get_public_key_from_cert("server/server.crt")

    else:
        print("Invalid role.")
        return

    print("=== SAVED CHAT SESSIONS ===")
    for index, session in enumerate(history):
        print(f"[{index}] Session Date: {session['timestamp']}")

    try:
        choice = int(input("\nSelect a session number to read: "))
        selected = history[choice]

        print(f"===Chat Log for {selected['timestamp']}===")

        for msg in selected["messages"]:
            sender = msg.split(": ", 1)[0]

            try:
                sender, plaintext = crypto_utils.decrypt_log_entry(
                    msg, my_private_key, partner_public_key
                )
                print(f"{sender}: {plaintext}  [verified]")

            except ValueError as e:
                if sender == "You":
                    print(f"{sender}: Chat log not decryptable by sender")
                else:
                    print(f"[DECRYPTION/VERIFICATION FAILED: {e}]")

        print("------------------------------------------\n")
    except (IndexError, ValueError):
        print("Invalid selection.")


while running:
    active = False
    session_log = []

    #while script is running but chat not active 
    while not active and running:
        choice = input(
            "Do you want to host (1) or connect (2) or view chat logs (3) or close application (4): "
        )

        if choice == "1":
            # Server loads its own Private Key & extracts Client='s Public Key from client.crt
            my_private_key = RSA.import_key(
                open("server/server.key", "rb").read(), passphrase="serverPwd"
            )
            partner_public_key = crypto_utils.get_public_key_from_cert(
                "client/client.crt"
            )

            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((SERVER, 3000))
            server.listen()

            client, addr = server.accept()
            print(f"===Server is listening on {SERVER}===")
            print("===Type '-DISCONNECT-' to end conversation===")
            active = True

        elif choice == "2":
            # Client loads its own Private Key & extracts Server's Public Key from server.crt
            my_private_key = RSA.import_key(
                open("client/client.key", "rb").read(), passphrase="clientPwd"
            )
            partner_public_key = crypto_utils.get_public_key_from_cert(
                "server/server.crt"
            )

            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(
                (SERVER, 3000)
            )  # If you want to connect to a specific IPv4, replace SERVER with that IPv4
            print(f"===Client successfully connected to {SERVER}===")
            print("===Type '-DISCONNECT-' to end conversation===")
            active = True

        elif choice == "3":
            view_chat_log()

        elif choice == "4":
            print("===Closing Application===")
            active = False
            running = False

        else:
            print("===Please select an option from what is shown===")

    #Chat session
    if active and running:
        sending_thread = threading.Thread(
            target=send_messages, args=(client, session_log, my_private_key, partner_public_key)
        )
        receiving_thread = threading.Thread(
            target=receive_messages, args=(client, session_log, my_private_key, partner_public_key)
        )

        sending_thread.start()
        receiving_thread.start()

        while active:
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
