from bluepy import btle
from delegate import Delegate
import threading
import time

ADDRESS_GUN = "d0:39:72:bf:c8:87"
ADDRESS_VEST = "d0:39:72:bf:c6:51"
ADDRESS_GLOVE = "d0:39:72:bf:c6:47"

HEADER_ACK = 65
HEADER_GUN = 71
HEADER_GLOVE = 77
HEADER_VEST = 86

PACKET_SIZE = 15

address_list = [ADDRESS_VEST, ADDRESS_GLOVE, ADDRESS_GUN]
name_list = ["Vest1", "Glove1", "Gun1"]
header_list = [HEADER_VEST, HEADER_GLOVE, HEADER_GUN]

# address_list = [ADDRESS_GLOVE]
# name_list = ["Beetle Glove"]

SERIAL_UUID = "0000dfb1-0000-1000-8000-00805f9b34fb"
RETRY_COUNT = 8

data_count = 0
frag_packet_count = 0
drop_packet_count = 0

ultra96_mutex = threading.Lock()
data_count_mutex = threading.Lock()
frag_packet_mutex = threading.Lock()
drop_packet_mutex = threading.Lock()


class Beetle():
    def __init__(self, address, name, header):
        self.peripheral = btle.Peripheral()
        self.address = address
        self.name = name
        self.header = header
        self.is_connected = False
        self.has_handshake = False
        self.serial_char = None
        self.delegate = None

    # only call this when we are sure we are not connected
    def connect_with_retries(self, retries):
        self.is_connected = False

        while not self.is_connected and retries > 0:
            try:
                print(f"{retries} Attempts Left:")
                self.__connect()
            except btle.BTLEException as e:
                print(e)
            retries -= 1
        if not self.is_connected:
            print(f"{self.name} could not connect!")
            print("Exiting Program...")
            exit()

    # only call when we encounter BTLEDisconnectError
    def set_disconnected(self):
        print(f"{self.name} disconnected. Attempting Reconnection...")
        self.is_connected = False

    def init_peripheral(self):
        self.__set_serial_char()
        self.__set_delegate()
        self.__attach_delegate()

    def init_handshake(self):
        try:
            self.__try_init_handshake()

        # Catches disconnect exception raised by __try_init_handshake.
        # Callers of init_handshake will handle reconnection process
        except btle.BTLEDisconnectError:
            self.set_disconnected()


    #Private Methods

    def __connect(self):
        print(f"Connecting to {self.address}...")
        self.peripheral.connect(self.address)
        self.is_connected = True
        print("Connected.")

    def __try_init_handshake(self):
        self.has_handshake = False
        while not self.has_handshake:
            self.__send_handshake()
            if self.peripheral.waitForNotifications(5.0):
                self.__receive_ack()

    # Sets serial characteristic in order to write to beetle
    def __set_serial_char(self):
        print(f"Setting serial characteristic for {self.name}...")
        chars = self.peripheral.getCharacteristics()
        serial_char = [c for c in chars if c.uuid == SERIAL_UUID][0]
        self.serial_char = serial_char
        print("Serial characteristic set.")

    # Creates delegate object to receive notifications
    def __set_delegate(self):
        print(f"Setting Delegate for {self.name}...")
        self.delegate = Delegate(self.serial_char, self.header)
        print("Delegate set.")

    # Attaches delegate object to peripheral
    def __attach_delegate(self):
        print(f"Attaching {self.name} delegate to peripheral...")
        self.peripheral.withDelegate(self.delegate)
        print("Done.")

    # Sends Handshake Packet
    def __send_handshake(self):
        print("Handshake in Progress...")
        self.serial_char.write(b'H')

    def __receive_ack(self):
        if self.delegate.hand_ack:
            print(f"Handshake ACK received from {self.name}")
            self.has_handshake = True
            self.serial_char.write(b'A')
    
    

# Helper function for initialisation
def initialise_beetle_list():
    init_params_beetle_list()
    init_connect_beetle_list()
    init_peripheral_beetle_list()
    init_handshake_beetle_list()


# Creates Beetle objects with their corresponding address and name,
# and appends it to the beetle list.
def init_params_beetle_list():
    for addr, name, header in zip(address_list, name_list, header_list):
        beetle_list.append(Beetle(addr, name, header))


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

            # If beetle disconnects during the handshake, will attempt
            # reconnection and handshaking
            if not beetle.is_connected:
                beetle.connect_with_retries(RETRY_COUNT)


# Thread Worker that relays valid data to Ultra96
def serial_handler(beetle):
    global data_count
    global frag_packet_count
    global drop_packet_count
    global start_time
    while True:
        try:
            if beetle.peripheral.waitForNotifications(5):
                # print(f" {beetle.name} Buffer: ", beetle.delegate.data_buffer)
                # print("Buffer Len: ", len(beetle.delegate.data_buffer))

        # if data is detected to be corrupted, it is set to empty byte obj
                if len(beetle.delegate.data_buffer) < PACKET_SIZE:
                    # print("Appending fragmented data into buffer...")
                    frag_packet_mutex.acquire()
                    frag_packet_count += 1
                    data_count_mutex.release()
                else:
                    # For now, mock up relaying to ultra96 by printing data
                    # print("Valid data! Relaying to Ultra96...")
                    # print("Data Sent: ", beetle.delegate.data_buffer)

                    if beetle.delegate.is_valid_data:
                        data_count_mutex.acquire()
                        data_count += 1
                        data_count_mutex.release()
                        beetle.serial_char.write(b'A')
                        
                    else:
                    # print("Invalid Data: Packet dropped!")
                        drop_packet_mutex.acquire()
                        drop_packet_count += 1
                        drop_packet_mutex.release()    

                    beetle.delegate.data_buffer = beetle.delegate.data_buffer[PACKET_SIZE-1:]
                    beetle.delegate.checksum = 0        
                
                    
                
                
        # Handles disconnect by attempting reconnection/rehandshake
        except btle.BTLEDisconnectError:
            beetle.set_disconnected()
            while not beetle.is_connected:
                beetle.connect_with_retries(RETRY_COUNT)
                print(f"{beetle.name} reconnected. Reinitialising handshake...")
                beetle.init_handshake()


if __name__ == "__main__":

    beetle_list = []

    initialise_beetle_list()

    # Delay to read the initial print statements
    time.sleep(2)
    start_time = time.time()

    # Starts threads
    thread_vest = threading.Thread(
        target=serial_handler, args=(beetle_list[0],))
    thread_vest.start()
    thread_glove = threading.Thread(
        target=serial_handler, args=(beetle_list[1],))
    thread_glove.start()
    thread_gun = threading.Thread(
        target=serial_handler, args=(beetle_list[2],))
    thread_gun.start()


    while True:
        pass



    # elapsed_time = time.time() - start_time
    #                 print(f"Packet Statuses for {beetle.name}:")
    #                 print("Time Elapsed: ", elapsed_time, end=" ")
    #                 print("Good Packets: ", data_count, end=" ")
    #                 print("Dropped Packets: ", drop_packet_count, end=" ")
    #                 print("Fragmented Packets: ", frag_packet_count, end=" ")
    #                 data_rate = ((data_count*15)/1000) / elapsed_time
    #                 print(f"Data Rate: {data_rate:.3f}kB/s")
