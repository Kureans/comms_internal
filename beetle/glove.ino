#include <Arduino_FreeRTOS.h>
#include <CircularBuffer.h>
#include <semphr.h>

#define MASK_BYTE 0xff

#define BUFFER_SIZE 50
#define TIMEOUT     200

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
  char packet[16];
  packet[0] = 'M';
  packet[1] = seq_no;
  int ptr = 2;
  append_value(packet, data.roll, ptr);
  append_value(packet, data.pitch, ptr);
  append_value(packet, data.yaw, ptr);
  append_value(packet, data.x_val, ptr);
  append_value(packet, data.y_val, ptr);
  append_value(packet, data.z_val, ptr);

  char checksum = 0;
  
  for (int i = 0; i < 14; i++) {
    checksum ^= packet[i];
  }

  packet[14] = checksum;
  packet[15] = '\0';
  Serial.write(packet, 15);
}

void printByte(char& b) {
    for (int i = 7; i >= 0; i--) {
        int a = b >> i;
        if (a & 1)
            Serial.print("1");
        else
            Serial.print("0");
    }
    Serial.print(" ");
}

//Helper function to convert 16 bit ints to 2 bytes (represented as 2 string characters)
void append_value(char* packet, uint16_t& val, int& ptr) {
  packet[ptr++] = (val >> 8) & MASK_BYTE;
  packet[ptr++] = (val & MASK_BYTE);
}

void setup() {
  Serial.begin(115200);

  //Initialises flags
  has_handshake = false;
  has_ack = false;
  seq_no = '1';

  //Initialising dummy data
  imu_data1.roll = 12123;
  imu_data1.pitch = 35422;
  imu_data1.yaw = 5612;
  imu_data1.x_val = 256;
  imu_data1.y_val = 2155;
  imu_data1.z_val = 2330;

  imu_data2.roll = 256;
  imu_data2.pitch = 255;
  imu_data2.yaw = 0;
  imu_data2.x_val = 1;
  imu_data2.y_val = 4;
  imu_data2.z_val = 10;

  //Initial Handshaking
  while (!has_handshake) {
    if (Serial.available() && Serial.read() == 'H') {
      has_handshake = true;
      Serial.print('A');
    } 
  } 

  //Creates the mutex object
  buffer_mutex = xSemaphoreCreateMutex();

  //Creates and starts the threads
  xTaskCreate(ReceiveAndProcessData, "Receive", 128, NULL, 2, NULL);
  xTaskCreate(SendDataAndReceiveACK, "Send", 128, NULL, 2, NULL);
}

void loop() {}

//Receives and process data. For now, just pushes mock data into buffer.
void ReceiveAndProcessData(void *pvParameters) {
  
  (void) pvParameters;
  
  for (;;) {
    if (xSemaphoreTake(buffer_mutex, portMAX_DELAY) == pdTRUE) {
      
      //If buffer is not full, push data into buffer
      if (!buffer.isFull()) {
        
        //pseudo_randomly pushes 2 different mock data into buffer
        if (seq_no == '0') {
          buffer.push(imu_data1);
        } else {
          buffer.push(imu_data2);
        }
      }
      xSemaphoreGive(buffer_mutex);
    }
    
    vTaskDelay(5);
  }
}


void SendDataAndReceiveACK(void *pvParameters) {
  (void) pvParameters;
  
  for (;;) {
    
    //Sends data from the head of the buffer
    assemble_and_send_data(buffer.first());

    //Initialises timer to check for packet timeout
    TickType_t curr_time = xTaskGetTickCount();
    
    while (!has_ack && ((xTaskGetTickCount() - curr_time) < TIMEOUT)) {
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

    //Removes sent data from head of buffer
    if (has_ack && xSemaphoreTake(buffer_mutex, portMAX_DELAY) == pdTRUE) {
      buffer.shift();
      xSemaphoreGive(buffer_mutex);
    }

    //Reinits ACK to false for next cycle
    has_ack = false;
    vTaskDelay(5);
  }

  
}