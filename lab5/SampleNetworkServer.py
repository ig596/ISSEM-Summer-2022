import threading
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import infinc
import time
import math
import socket
import fcntl
import os
import errno
import random
import string
from SampleNetworkClient import *

class SmartNetworkThermometer (threading.Thread) :
    open_cmds = ["AUTH", "LOGOUT"]
    prot_cmds = ["SET_DEGF", "SET_DEGC", "SET_DEGK", "GET_TEMP", "UPDATE_TEMP"]

    def __init__ (self, source, updatePeriod, port) :
        threading.Thread.__init__(self, daemon = True) 
        #set daemon to be true, so it doesn't block program from exiting
        self.source = source
        self.updatePeriod = updatePeriod
        self.curTemperature = 0
        self.updateTemperature()
        self.tokens = []

        self.serverSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.serverSocket.bind(("127.0.0.1", port))
        fcntl.fcntl(self.serverSocket, fcntl.F_SETFL, os.O_NONBLOCK)

        self.deg = "K"

    def setSource(self, source) :
        self.source = source

    def setUpdatePeriod(self, updatePeriod) :
        self.updatePeriod = updatePeriod 

    def setDegreeUnit(self, s) :
        self.deg = s
        if self.deg not in ["F", "K", "C"] :
            self.deg = "K"

    def updateTemperature(self) :
        self.curTemperature = self.source.getTemperature()

    def getTemperature(self) :
        if self.deg == "C" :
            return self.curTemperature - 273
        if self.deg == "F" :
            return (self.curTemperature - 273) * 9 / 5 + 32

        return self.curTemperature

    def processCommands(self, msg, addr) :
        cmds = msg.split(';')
        for c in cmds :
            cs = c.split(' ')
            if len(cs) == 2 : #should be either AUTH or LOGOUT
                if cs[0] == "AUTH":
                    if cs[1] == "!Q#E%T&U8i6y4r2w" :
                        self.tokens.append(''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16)))
                        self.serverSocket.sendto(self.tokens[-1].encode("utf-8"), addr)
                        #print (self.tokens[-1])
                elif cs[0] == "LOGOUT":
                    if cs[1] in self.tokens :
                        self.tokens.remove(cs[1])
                else : #unknown command
                    self.serverSocket.sendto(b"Invalid Command\n", addr)
            elif c == "SET_DEGF" :
                self.deg = "F"
            elif c == "SET_DEGC" :
                self.deg = "C"
            elif c == "SET_DEGK" :
                self.deg = "K"
            elif c == "GET_TEMP" :
                self.serverSocket.sendto(b"%f\n" % self.getTemperature(), addr)
            elif c == "UPDATE_TEMP" :
                self.updateTemperature()
            elif c :
                self.serverSocket.sendto(b"Invalid Command\n", addr)


    def run(self) : #the running function
        while True : 
            try :
                msg, addr = self.serverSocket.recvfrom(1024)
                msg = msg.decode("utf-8").strip()
                cmds = msg.split(' ')
                if len(cmds) == 1 : # protected commands case
                    semi = msg.find(';')
                    if semi != -1 : #if we found the semicolon
                        #print (msg)
                        if msg[:semi] in self.tokens : #if its a valid token
                            self.processCommands(msg[semi+1:], addr)
                        else :
                            self.serverSocket.sendto(b"Bad Token\n", addr)
                    else :
                            self.serverSocket.sendto(b"Bad Command\n", addr)
                elif len(cmds) == 2 :
                    if cmds[0] in self.open_cmds : #if its AUTH or LOGOUT
                        self.processCommands(msg, addr) 
                    else :
                        self.serverSocket.sendto(b"Authenticate First\n", addr)
                else :
                    # otherwise bad command
                    self.serverSocket.sendto(b"Bad Command\n", addr)
    
            except IOError as e :
                if e.errno == errno.EWOULDBLOCK :
                    #do nothing
                    pass
                else :
                    #do nothing for now
                    pass
                msg = ""

 

            self.updateTemperature()
            time.sleep(self.updatePeriod)


class SimpleClient :
    def __init__(self, therm1, therm2) :
        self.fig, self.ax = plt.subplots()
        now = time.time()
        self.lastTime = now
        self.times = [time.strftime("%H:%M:%S", time.localtime(now-i)) for i in range(30, 0, -1)]
        self.infTemps = [0]*30
        self.incTemps = [0]*30
        self.infLn, = plt.plot(range(30), self.infTemps, label="Infant Temperature")
        self.incLn, = plt.plot(range(30), self.incTemps, label="Incubator Temperature")
        plt.xticks(range(30), self.times, rotation=45)
        plt.ylim((20,50))
        plt.legend(handles=[self.infLn, self.incLn])
        self.infTherm = therm1
        self.incTherm = therm2

        self.ani = animation.FuncAnimation(self.fig, self.updateInfTemp, interval=500)
        self.ani2 = animation.FuncAnimation(self.fig, self.updateIncTemp, interval=500)

    def updateTime(self) :
        now = time.time()
        if math.floor(now) > math.floor(self.lastTime) :
            t = time.strftime("%H:%M:%S", time.localtime(now))
            self.times.append(t)
            #last 30 seconds of of data
            self.times = self.times[-30:]
            self.lastTime = now
            plt.xticks(range(30), self.times,rotation = 45)
            plt.title(time.strftime("%A, %Y-%m-%d", time.localtime(now)))


    def updateInfTemp(self, frame) :
        self.updateTime()
        self.infTemps.append(self.infTherm.getTemperature()-273)
        #self.infTemps.append(self.infTemps[-1] + 1)
        self.infTemps = self.infTemps[-30:]
        self.infLn.set_data(range(30), self.infTemps)
        return self.infLn,

    def updateIncTemp(self, frame) :
        self.updateTime()
        self.incTemps.append(self.incTherm.getTemperature()-273)
        #self.incTemps.append(self.incTemps[-1] + 1)
        self.incTemps = self.incTemps[-30:]
        self.incLn.set_data(range(30), self.incTemps)
        return self.incLn,

UPDATE_PERIOD = .05 #in seconds
SIMULATION_STEP = .1 #in seconds

#create a new instance of IncubatorSimulator
bob = infinc.Human(mass = 8, length = 1.68, temperature = 36 + 273)
#bobThermo = infinc.SmartThermometer(bob, UPDATE_PERIOD)
bobThermo = SmartNetworkThermometer(bob, UPDATE_PERIOD, 23456)
bobThermo.start() #start the thread

inc = infinc.Incubator(width = 1, depth=1, height = 1, temperature = 37 + 273, roomTemperature = 20 + 273)
#incThermo = infinc.SmartNetworkThermometer(inc, UPDATE_PERIOD)
incThermo = SmartNetworkThermometer(inc, UPDATE_PERIOD, 23457)
incThermo.start() #start the thread

incHeater = infinc.SmartHeater(powerOutput = 1500, setTemperature = 45 + 273, thermometer = incThermo, updatePeriod = UPDATE_PERIOD)
inc.setHeater(incHeater)
incHeater.start() #start the thread

sim = infinc.Simulator(infant = bob, incubator = inc, roomTemp = 20 + 273, timeStep = SIMULATION_STEP, sleepTime = SIMULATION_STEP / 10)

sim.start()

sc = SimpleClient(bobThermo, incThermo)

# Write Test cases

# 1- Get Hard Coded Password
sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
sock.sendto(b"AUTH !Q#E%T&U8i6y4r2w", ("127.0.0.1", 23456))
print("sent")
token, addr = sock.recvfrom(1024)
token = token.decode()
print("token", token)
sock.sendto(("LOGOUT " + token).encode(), ("127.0.0.1", 23456))

# 2- Token List Grows, probably increase to VERY big number?
for i in range(10):
    sock.sendto(b"AUTH !Q#E%T&U8i6y4r2w", ("127.0.0.1", 23456))
    token, addr = sock.recvfrom(1024)
    token = token.decode()
    print("DDOS LIST TOKEN", token)

    # because an invalid token is passed, no token is removed in self.list
    sock.sendto(b"LOGOUT random-token", ("127.0.0.1", 23456))

# 3- Plaintext authentication, use MITM to capture stuff
mitmSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
mitmSocket.bind(("127.0.0.2", 23456))
fcntl.fcntl(mitmSocket, fcntl.F_SETFL, os.O_NONBLOCK)

# Client authenticates, MITM grabs Client Auth Token
sock.sendto(b"AUTH !Q#E%T&U8i6y4r2w", ("127.0.0.2", 23456))
auth_password, client_addr = mitmSocket.recvfrom(1024)
print("MITM STOLE", auth_password)

# MITM captures plaintext password and forwards to server.
mitmSocket.sendto(auth_password, ("127.0.0.1", 23456))
# Give MITM time to send the request and have the token stealing time to complete.
time.sleep(5)
token, real_server_addr = mitmSocket.recvfrom(1024)
print("MITM STOLE TOKEN", token, real_server_addr)

# End Test cases

plt.grid()
plt.show()

