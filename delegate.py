from bluepy import btle

PACKET_SIZE = 15

class Delegate(btle.DefaultDelegate):
    def __init__(self, serial_char, header):
        btle.DefaultDelegate.__init__(self)
        self.serial_char = serial_char
        self.header = header
        self.data_buffer = b""
        self.prev_seq_no = None
        self.hand_ack = False       
        self.is_valid_data = False
        self.checksum = 0
        self.is_fragmented = False

    def handleNotification(self, cHandle, data):
        if (len(data) == 1 and data[0] == 65):
            self.__handle_acknowledgement()
        else:
            if (self.is_fragmented or data[0] == self.header):
                self.__handle_data(data)

    def __handle_acknowledgement(self):
        print(f"Acknowledgement Received")
        self.hand_ack = True
    
    def __handle_data(self, data):
        print("Data: ", data)
        if (len(data) == PACKET_SIZE):
            self.checksum = 0
            for i in range(len(data)-1):
                self.checksum ^= data[i]
            
            if self.prev_seq_no == data[1] or self.checksum != data[-1]:
                if self.prev_seq_no == data[1]:
                    print("Sequence numbers do not match")
                else:
                    print("Checksums do not match")
                self.data_buffer = b""
            else:
                self.prev_seq_no = data[1]
                self.data_buffer = data
      
        else:
            if (len(self.data_buffer) + len(data) < PACKET_SIZE):
                self.is_fragmented = True
                print("Fragmentation!")

                for i in range(len(data)):
                    self.checksum ^= data[i]  
                self.data_buffer += data
            else:
                
                self.is_fragmented = False
                for i in range(len(data)-1):
                    self.checksum ^= data[i]
                self.data_buffer += data

                #At this point, data_buffer is assembled
                print("Assembled data: ", self.data_buffer)
                print("Calced Checksum: ", self.checksum)
                if (self.prev_seq_no == self.data_buffer[1] 
                or self.checksum != self.data_buffer[-1]):
                    self.data_buffer = b""
                else:
                    self.prev_seq_no = self.data_buffer[1]



# class GunDelegate(Delegate):
#     def __init__(self, serial_char):
#         super().__init__(serial_char)

#     def handleNotification(self, cHandle, data):
#         print("should not receive i hope")


# class GloveDelegate(Delegate):
#     def __init__(self, serial_char):
#         super().__init__(serial_char)

#     def handleNotification(self, cHandle, data):
#         self.__handle_imu_data(data)

#     def __handle_imu_data(self, data):
#         is_valid_packet = False
#         for label in imu_labels:
#             is_valid_packet &= (label in data)
#         if len(data) == 19 and is_valid_packet:
#             self.serial_char.write(b'A')
#             if self.seq_no != None and self.seq_no == data[-1]:
#                 self.data_buffer = b'X'
#             else:
#                 self.seq_no = data[-1]
#         else:
#             self.data_buffer = b'X'
