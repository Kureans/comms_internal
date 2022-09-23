#include <Arduino_FreeRTOS.h>
#include <CircularBuffer.h>
#include <semphr.h>

#define MASK_MSB 0xff00
#define MASK_LSB 0xff

#define BUFFER_SIZE 50

#define HIGH_FRAG_DELAY 50
#define NORMAL_DELAY 2000

//Mock IMU Data Structure
typedef struct IMUData {
  uint16_t roll;
  uint16_t pitch;
  uint16_t yaw;
  uint16_t x_val;
  uint16_t y_val;
  uint16_t z_val;
} IMUData;

//Thread Declaration
void ReceiveAndProcessData(void *pvParameters);
void SendDataAndReceiveACK(void *pvParameters);

//Buffer to store incoming IMU Readings
CircularBuffer<IMUData, BUFFER_SIZE> buffer;

//Mutex to ensure that only 1 thread accesses buffer at a time
SemaphoreHandle_t buffer_mutex;

//Dummy Data
IMUData imu_data1;
IMUData imu_data2;

bool has_handshake;
bool has_ack;
char seq_no;

//Assembles the 15 byte packet and sends it out over serial
void assemble_and_send_data(IMUData data) {
  String packet = "";
  packet += "M";
  packet += seq_no;
  packet += int_to_bytes(data.roll);
  packet += int_to_bytes(data.pitch);
  packet += int_to_bytes(data.yaw);
  packet += int_to_bytes(data.x_val);
  packet += int_to_bytes(data.y_val);
  packet += int_to_bytes(data.z_val);
  uint8_t checksum = 0;
  for (char c : packet) {
    checksum ^= c;
  }
  packet += (char) checksum;
  Serial.print(packet);
}

//Helper function to convert 16 bit ints to 2 bytes (represented as 2 string characters)
String int_to_bytes(uint16_t val) {
  String bytes = "";
  char msb_byte = (val & MASK_MSB) >> 8;
  char lsb_byte = (val & MASK_LSB);
  bytes += msb_byte;
  bytes += lsb_byte;
  return bytes;
}

void setup() {
  Serial.begin(115200);

  //Initialises flags
  has_handshake = false;
  has_ack = false;
  seq_no = '0';

  //Initialising dummy data
  imu_data1.roll = 12123;
  imu_data1.pitch = 35422;
  imu_data1.yaw = 5612;
  imu_data1.x_val = 7834;
  imu_data1.y_val = 903;
  imu_data1.z_val = 36;

  imu_data2.roll = 88;
  imu_data2.pitch = 77;
  imu_data2.yaw = 66;
  imu_data2.x_val = 55;
  imu_data2.y_val = 44;
  imu_data2.z_val = 33;

  //Initial Handshaking
  while (!has_handshake) {
    if (Serial.available() && Serial.read() == 'H') {
      has_handshake = true;
      Serial.print('A');
    } 
  } 

//  //Creates the mutex object
//  buffer_mutex = xSemaphoreCreateMutex();
//
//  //Creates and starts the threads
//  xTaskCreate(ReceiveAndProcessData, "Receive", 128, NULL, 2, NULL);
//  xTaskCreate(SendDataAndReceiveACK, "Send", 128, NULL, 2, NULL);
}


// For high speed fragmentation test
void loop() {

    delay(HIGH_FRAG_DELAY);
    
    if (seq_no == '0') {
      assemble_and_send_data(imu_data1);
    } else {
      assemble_and_send_data(imu_data2);
    }
    

    //Initialises timer to check for packet timeout
    unsigned long curr_time = millis();
    
    while (!has_ack && ((millis() - curr_time) < 5000)) {
      if (Serial.available()) {

        //Should read either 'H' for handshake or 'A' for normal ACK
        char hdr = Serial.read();

        //Successfully received ACK, and flips seq_no for next packet
        if (hdr == 'A') {
          has_ack = true;
          seq_no = (seq_no == '0') ? '1' : '0';
        }

        //In the event that connection loss occured and relay_node re-inits handshake
        if (hdr == 'H') {
          Serial.print('A');
        }
        
      }
    }

    //Reinits ACK to false for next cycle
    has_ack = false;
  
}

//
////Receives and process data. For now, just pushes mock data into buffer.
//void ReceiveAndProcessData(void *pvParameters) {
//  
//  (void) pvParameters;
//  
//  for (;;) {
//    if (xSemaphoreTake(buffer_mutex, portMAX_DELAY) == pdTRUE) {
//      
//      //If buffer is not full, push data into buffer
//      if (!buffer.isFull()) {
//        
//        //pseudo_randomly pushes 2 different mock data into buffer
//        if (seq_no == '0') {
//          buffer.push(imu_data1);
//        } else {
//          buffer.push(imu_data2);
//        }
//      }
//      xSemaphoreGive(buffer_mutex);
//    }
//  }
//}
//
//
//void SendDataAndReceiveACK(void *pvParameters) {
//  (void) pvParameters;
//  
//  for (;;) {
//    
//    //Sends data from the head of the buffer
//    assemble_and_send_data(buffer.first());
//
//    //Initialises timer to check for packet timeout
//    TickType_t curr_time = xTaskGetTickCount();
//    
//    while (!has_ack && ((xTaskGetTickCount() - curr_time) < 5000)) {
//      if (Serial.available()) {
//
//        //Should read either 'H' for handshake or 'A' for normal ACK
//        char hdr = Serial.read();
//
//        //Successfully received ACK, and flips seq_no for next packet
//        if (hdr == 'A') {
//          has_ack = true;
//          seq_no = (seq_no == '0') ? '1' : '0';
//        }
//
//        //In the event that connection loss occured and relay_node re-inits handshake
//        if (hdr == 'H') {
//          Serial.print('A');
//        }
//        
//      }
//    }
//
//    //Removes sent data from head of buffer
//    if (has_ack && xSemaphoreTake(buffer_mutex, portMAX_DELAY) == pdTRUE) {
//      buffer.shift();
//      xSemaphoreGive(buffer_mutex);
//    }
//
//    //Reinits ACK to false for next cycle
//    has_ack = false;
//  }
//
//  
//}

//for (;;) {
//   
//    while (has_ack == 0) {
//      send_data(buffer.first());
//      TickType_t curr_time = xTaskGetTickCount();
//      while (!has_ack && ((xTaskGetTickCount() - curr_time) < 5000)) {
//        if (Serial.available()) {
//          char hdr = Serial.read();
//          if (hdr == 'A') {
//            has_ack = 1;
//            seq_no = (seq_no == '0') ? '1' : '0';
//            if (xSemaphoreTake(buffer_mutex, portMAX_DELAY) == pdTRUE) {
//              buffer.shift();
//              xSemaphoreGive(buffer_mutex);
//            }
//            
//          }
//          if (hdr == 'H') {
//            Serial.print('A');
//          }
//        }
//      }
//    }
//
//    has_ack = 0;
//  }
//  
//void loop() {
//  
//    delay(2000);
//    receive_data(seq_no);
//    while (has_ack == 0) {
//      send_data(buffer.first());
//      unsigned long curr_time = millis();
//      while (!has_ack && ((millis() - curr_time) < 5000)) {
//        if (Serial.available()) {
//          char hdr = Serial.read();
//          if (hdr == 'A') {
//            has_ack = 1;
//            seq_no = (seq_no == '0') ? '1' : '0';
//            buffer.shift();
//          }
//          if (hdr == 'H') {
//            Serial.print('A');
//          }
//        }
//      }
//  
//    }
//    
//    has_ack = 0;
//  
//}
