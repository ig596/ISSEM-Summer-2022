import configparser
import fcntl
import hashlib
import math
import os
import secrets
import socket
import threading
import time

import cryptography.fernet
import matplotlib.animation as animation
import matplotlib.pyplot as plt

import infinc

PASSWORD = None


class SmartNetworkThermometer(threading.Thread):
    open_cmds = ["AUTH", "LOGOUT"]
    prot_cmds = ["SET_DEGF", "SET_DEGC", "SET_DEGK", "GET_TEMP", "UPDATE_TEMP"]

    def __init__(self, source, updatePeriod, port, password, key):  # Added password as parameter.
        threading.Thread.__init__(self, daemon=True)
        # set daemon to be true, so it doesn't block program from exiting
        self.source = source
        self.updatePeriod = updatePeriod
        self.curTemperature = 0
        self.updateTemperature()
        self.tokens = []
        self.crypto = cryptography.fernet.Fernet(key=key)
        self.hashed_password = hashlib.sha256(bytes(password, "utf-8")).hexdigest()  # store hashed password
        #print(self.hashed_password)
        #self.serverSocket = socket.create_server(address=("127.0.0.1", port), reuse_port=True, family=socket.AF_INET)
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.serverSocket.bind(("127.0.0.1", port))
        fcntl.fcntl(self.serverSocket, fcntl.F_SETFL, os.O_NONBLOCK)

        self.deg = "K"

    def setPassword(self, password):
        self.hashed_password = hashlib.sha256(password).hexdigest()

    def setSource(self, source):
        self.source = source

    def setUpdatePeriod(self, updatePeriod):
        self.updatePeriod = updatePeriod

    def setDegreeUnit(self, s):
        self.deg = s
        if self.deg not in ["F", "K", "C"]:
            self.deg = "K"

    def updateTemperature(self):
        self.curTemperature = self.source.getTemperature()

    def getTemperature(self):
        if self.deg == "C":
            return self.curTemperature - 273
        if self.deg == "F":
            return (self.curTemperature - 273) * 9 / 5 + 32

        return self.curTemperature

    def processCommands(self, msg, addr):
        print(msg)
        cmds = msg.split(';')
        for c in cmds:
            cs = c.split(' ')
            if len(cs) == 2:  # should be either AUTH or LOGOUT
                if cs[0] == "AUTH":
                    if cs[1] == self.hashed_password:
                        if len(self.tokens) > 9:  # Added Check for number of active tokens
                            print("Token Limit Reached")
                            msg = self.crypto.encrypt(b"Too many active tokens. Please Logout a session.")
                            self.serverSocket.sendto(msg, addr)
                        else:
                            self.tokens.append(secrets.token_urlsafe(16))
                            self.serverSocket.sendto(self.crypto.encrypt(self.tokens[-1].encode('utf-8')), addr)
                        # print (self.tokens[-1])
                elif cs[0] == "LOGOUT":
                    if cs[1] in self.tokens:
                        self.tokens.remove(cs[1])
                else:  # unknown command
                    msg = self.crypto.encrypt(b"Invalid Command\n")
                    self.serverSocket.sendto(msg, addr)
            elif c == "SET_DEGF":
                self.deg = "F"
            elif c == "SET_DEGC":
                self.deg = "C"
            elif c == "SET_DEGK":
                self.deg = "K"
            elif c == "GET_TEMP":
                msg = self.crypto.encrypt(b"%f\n" % self.getTemperature())
                self.serverSocket.sendto(msg, addr)
            elif c == "UPDATE_TEMP":
                self.updateTemperature()
            elif c:
                msg = self.crypto.encrypt(b"Invalid Command\n")
                self.serverSocket.sendto(msg, addr)

    def run(self):  # the running function
        while True:
            try:
                msg, addr = self.serverSocket.recvfrom(1024)
                #print(f"Encrypted MSG: {msg}")
                msg = self.crypto.decrypt(msg)
                msg = msg.decode("utf-8").strip()
                cmds = msg.split(' ')
                if len(cmds) == 1:  # protected commands case
                    semi = msg.find(';')
                    if semi != -1:  # if we found the semicolon
                        # print (msg)
                        if msg[:semi] in self.tokens:  # if its a valid token
                            self.processCommands(msg[semi + 1:], addr)
                        else:
                            msg = self.crypto.encrypt(b"Bad Token\n")
                            self.serverSocket.sendto(msg, addr)
                    else:
                        msg = self.crypto.encrypt(b"Bad Command\n")
                        self.serverSocket.sendto(msg, addr)
                elif len(cmds) == 2:
                    if cmds[0] in self.open_cmds:  # if its AUTH or LOGOUT
                        self.processCommands(msg, addr)
                    else:
                        msg = self.crypto.encrypt(b"Authenticate First\n")
                        self.serverSocket.sendto(msg, addr)
                else:
                    # otherwise bad command
                    msg = self.crypto.encrypt(b"Bad Command\n")
                    self.serverSocket.sendto(msg, addr)

            except IOError:
                msg = "Error"

            self.updateTemperature()
            time.sleep(self.updatePeriod)


class SimpleClient:
    def __init__(self, therm1, therm2):
        self.fig, self.ax = plt.subplots()
        now = time.time()
        self.lastTime = now
        self.times = [time.strftime("%H:%M:%S", time.localtime(now - i)) for i in range(30, 0, -1)]
        self.infTemps = [0] * 30
        self.incTemps = [0] * 30
        self.infLn, = plt.plot(range(30), self.infTemps, label="Infant Temperature")
        self.incLn, = plt.plot(range(30), self.incTemps, label="Incubator Temperature")
        plt.xticks(range(30), self.times, rotation=45)
        plt.ylim((20, 50))
        plt.legend(handles=[self.infLn, self.incLn])
        self.infTherm = therm1
        self.incTherm = therm2

        self.ani = animation.FuncAnimation(self.fig, self.updateInfTemp, interval=500)
        self.ani2 = animation.FuncAnimation(self.fig, self.updateIncTemp, interval=500)

    def updateTime(self):
        now = time.time()
        if math.floor(now) > math.floor(self.lastTime):
            t = time.strftime("%H:%M:%S", time.localtime(now))
            self.times.append(t)
            # last 30 seconds of of data
            self.times = self.times[-30:]
            self.lastTime = now
            plt.xticks(range(30), self.times, rotation=45)
            plt.title(time.strftime("%A, %Y-%m-%d", time.localtime(now)))

    def updateInfTemp(self, frame):
        self.updateTime()
        self.infTemps.append(self.infTherm.getTemperature() - 273)
        # self.infTemps.append(self.infTemps[-1] + 1)
        self.infTemps = self.infTemps[-30:]
        self.infLn.set_data(range(30), self.infTemps)
        return self.infLn,

    def updateIncTemp(self, frame):
        self.updateTime()
        self.incTemps.append(self.incTherm.getTemperature() - 273)
        # self.incTemps.append(self.incTemps[-1] + 1)
        self.incTemps = self.incTemps[-30:]
        self.incLn.set_data(range(30), self.incTemps)
        return self.incLn,


UPDATE_PERIOD = .05  # in seconds
SIMULATION_STEP = .1  # in seconds

# create a new instance of IncubatorSimulator
bob = infinc.Human(mass=8, length=1.68, temperature=36 + 273)
# CODE TO PULL PASSWORD FROM CONFIGS
parser = configparser.ConfigParser(strict=False, interpolation=None)
parser.read(filenames='config.ini')
password = parser['configs']["PASSWORD"]
key = parser['configs']['key']
# bobThermo = infinc.SmartThermometer(bob, UPDATE_PERIOD)
bobThermo = SmartNetworkThermometer(bob, UPDATE_PERIOD, 23456, password, key)
bobThermo.start()  # start the thread

inc = infinc.Incubator(width=1, depth=1, height=1, temperature=37 + 273, roomTemperature=20 + 273)
# incThermo = infinc.SmartNetworkThermometer(inc, UPDATE_PERIOD)
incThermo = SmartNetworkThermometer(inc, UPDATE_PERIOD, 23457, password, key)
incThermo.start()  # start the thread

incHeater = infinc.SmartHeater(powerOutput=1500, setTemperature=45 + 273, thermometer=incThermo,
                               updatePeriod=UPDATE_PERIOD)
inc.setHeater(incHeater)
incHeater.start()  # start the thread

sim = infinc.Simulator(infant=bob, incubator=inc, roomTemp=20 + 273, timeStep=SIMULATION_STEP,
                       sleepTime=SIMULATION_STEP / 10)

sim.start()

sc = SimpleClient(bobThermo, incThermo)

plt.grid()
plt.show()
