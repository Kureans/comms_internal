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
        self.checksum = 0
        self.is_fragmented = False
        self.is_valid_data = False

    # Triggers whenever data comes in to the characteristic
    def handleNotification(self, cHandle, data):
        if (len(data) == 1 and data[0] == 65):
            self.__handle_acknowledgement()
        else:
            # when data is fragmented is true, there won't be a header,
            # so pass in unconditionally
            if (self.is_fragmented or data[0] == self.header):
                self.__handle_data(data)

    def __handle_acknowledgement(self):
        print(f"Acknowledgement Received")
        self.hand_ack = True
    
    def __handle_data(self, data):
        for b in data:
            print(b, end=" ")
        #Non-fragmented Data
        if not self.is_fragmented and len(data) == PACKET_SIZE:
            self.checksum = 0
            for i in range(len(data)-1):
                self.checksum ^= data[i]
            
            if self.prev_seq_no == data[1] or self.checksum != data[-1]:
                self.is_valid_data = False
            else:
                self.prev_seq_no = data[1]
                self.data_buffer = data
                self.is_valid_data = True
        
        #Fragmented Data
        else:
            self.is_fragmented = True

            #Data coming in + current data buffer is under packet size
            if (len(self.data_buffer) + len(data) < PACKET_SIZE):
                for i in range(len(data)):
                    self.checksum ^= data[i]  
                self.data_buffer += data

            #Data coming in + current data buffer is over packet size
            elif (len(self.data_buffer) + len(data) > PACKET_SIZE):
                rem = PACKET_SIZE - len(self.data_buffer)
                for i in range(rem-1):
                    self.checksum ^= data[i]
                self.data_buffer += data
                if (self.prev_seq_no == self.data_buffer[1] 
                or self.checksum != self.data_buffer[PACKET_SIZE-1]):
  
                    self.is_valid_data = False
                else:
                    self.prev_seq_no = self.data_buffer[1]
                    self.is_valid_data = True

            else:
                #Data coming in + Current data buffer meets packet size
                self.is_fragmented = False
                for i in range(len(data)-1):
                    self.checksum ^= data[i]
                self.data_buffer += data

                #At this point, data_buffer is assembled
                # print("Assembled data: ", self.data_buffer)
                # print("Calced Checksum: ", self.checksum)
                if (self.prev_seq_no == self.data_buffer[1] 
                or self.checksum != self.data_buffer[PACKET_SIZE-1]):
                    self.is_valid_data = False
                else:
                    self.prev_seq_no = self.data_buffer[1]
                    self.is_valid_data = True




