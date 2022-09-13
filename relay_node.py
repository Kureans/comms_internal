from bluepy import btle
from delegate import Delegate
import threading
import time

ADDRESS_GUN = "d0:39:72:bf:cd:04"
ADDRESS_GLOVE = "d0:39:72:bf:c6:51"
ADDRESS_VEST = "d0:39:72:bf:c6:47"

HEADER_GUN = 71
HEADER_GLOVE = 77
HEADER_VEST = 86

PACKET_SIZE = 15

address_list = [ADDRESS_GLOVE, ADDRESS_VEST]
name_list = ["Beetle Glove", "Beetle Vest"] 

SERIAL_UUID = "0000dfb1-0000-1000-8000-00805f9b34fb"
RETRY_COUNT = 8
ultra96_mutex = threading.Lock()


class Beetle():
    def __init__(self, address, name):
        self.peripheral = btle.Peripheral()
        self.address = address
        self.name = name
        self.is_connected = False
        self.has_handshake = False
        self.serial_char = None
        self.delegate = None

    #only call this when we are sure we are not connected
    def connect_with_retries(self, retries):
        self.is_connected = False
        
        while not self.is_connected and retries > 0:
            try:
                print(f"{retries} Attempts Left:")
                self.connect()
            except btle.BTLEException as e:
                print(e)
            retries -= 1
        if not self.is_connected:
            print(f"{self.name} could not connect!")
            print("Exiting Program...")
            exit()

    def connect(self):
        print(f"Connecting to {self.address}...")
        self.peripheral.connect(self.address)
        self.is_connected = True
        print("Connected.")

    def init_peripheral(self):
        self.__set_serial_char()
        self.__set_delegate()
        self.__attach_delegate()

    def init_handshake(self):
        try:
            self.__try_init_handshake()
        except btle.BTLEDisconnectError:
            print("Disconnected while handshaking!")
            self.is_connected = False

    def __try_init_handshake(self):
        self.has_handshake = False
        while not self.has_handshake:
            print("Handshake in Progress...")
            self.serial_char.write(b'H')
            if self.peripheral.waitForNotifications(5.0):
                if self.delegate.hand_ack:
                    print(f"Handshake ACK received from {self.name}")
                    self.has_handshake = True
                    self.serial_char.write(b'A')

    def __set_serial_char(self):
        print(f"Setting serial characteristic for {self.name}...")
        chars = self.peripheral.getCharacteristics()
        serial_char = [c for c in chars if c.uuid == SERIAL_UUID][0]
        self.serial_char = serial_char
        print("Serial characteristic set.")

    # Creates delegate object to receive notifications
    def __set_delegate(self):
        print(f"Setting Delegate for {self.name}...")
        if self.name == "Beetle Vest":
            self.delegate = Delegate(self.serial_char, HEADER_VEST)
        elif self.name == "Beetle Glove":
            self.delegate = Delegate(self.serial_char, HEADER_GLOVE)
        elif self.name == "Beetle Gun":
            self.delegate = Delegate(self.serial_char, HEADER_GUN)
        print("Delegate set.")

    # Attaches delegate object to peripheral
    def __attach_delegate(self):
        print(f"Attaching {self.name} delegate to peripheral...")
        self.peripheral.withDelegate(self.delegate)
        print("Done.")


def initialise_beetle_list():
    init_params_beetle_list()
    init_connect_beetle_list()
    init_peripheral_beetle_list()
    init_handshake_beetle_list()


def init_params_beetle_list():
    for addr, name in zip(address_list, name_list):
        beetle_list.append(Beetle(addr, name))


def init_connect_beetle_list():
    for beetle in beetle_list:
        beetle.connect_with_retries(RETRY_COUNT)


def init_peripheral_beetle_list():
    for beetle in beetle_list:
        beetle.init_peripheral()


def init_handshake_beetle_list():
    for beetle in beetle_list:
        while not beetle.has_handshake and beetle.is_connected:
            beetle.init_handshake()
            if not beetle.is_connected:
                beetle.connect_with_retries(RETRY_COUNT)
            

# Thread Worker that relays non-fragmented/corrupted data to Ultra96
def serial_handler(beetle):
    while True:
        try:
            if beetle.peripheral.waitForNotifications(5):
                print(f" {beetle.name} Buffer: ", beetle.delegate.data_buffer)
                print("Buffer Len: ", len(beetle.delegate.data_buffer))

        # if data is detected to be corrupted, it is set to empty byte obj
                if beetle.delegate.data_buffer == b"":
                    print("Invalid Data: Packet dropped!")
                elif len(beetle.delegate.data_buffer) < PACKET_SIZE:
                    print("Appending fragmented data into buffer...")
                else:
                    print("Valid data! Relaying to Ultra96...")
                    print("Data Sent: ", beetle.delegate.data_buffer)
                    beetle.serial_char.write(b'A')
                    beetle.delegate.data_buffer = b""
                    beetle.delegate.checksum = 0

        except btle.BTLEDisconnectError:
            beetle.is_connected = False
            print(f"{beetle.name} disconnected. Attempting Reconnection...")
            while not beetle.is_connected:
                beetle.connect_with_retries(RETRY_COUNT)
                print(f"{beetle.name} reconnected. Reinitialising handshake...")
                beetle.init_handshake()

if __name__ == "__main__":

    beetle_list = []

    initialise_beetle_list()
    time.sleep(2)
    thread_glove = threading.Thread(
        target=serial_handler, args=(beetle_list[0],))
    thread_glove.start()
    thread_vest = threading.Thread(
        target=serial_handler, args=(beetle_list[1],))
    thread_vest.start()

    while True:
        pass

