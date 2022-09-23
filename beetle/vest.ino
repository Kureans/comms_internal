#include <Arduino_FreeRTOS.h>
#include <semphr.h>

#define TIMEOUT 5000

//Thread Declaration
void ReceiveAndProcessData(void *pvParameters);
void SendDataAndReceiveACK(void *pvParameters);

//Mutex to ensure that only 1 thread accesses count variable at a time
SemaphoreHandle_t count_mutex;

uint8_t get_hit_count; //Number of received hits that have not been processed
bool has_handshake;
bool has_ack;
char seq_no;
String padding = "111111111111"; //12 bytes padding

//Assembles the 15 byte packet and sends it out over serial
void assemble_and_send_data() {
    String packet = "";
    packet += "V";
    packet += seq_no;
    packet += padding;
    int checksum = 0;
    for (char c : packet) {
      checksum ^= c;
    }
    packet += (char) checksum;
    Serial.print(packet);
}

void setup() {
  Serial.begin(115200);

  //Initialises flags
  has_handshake = false;
  has_ack = false;
  seq_no = '0';
  get_hit_count = 0;

  //Initial Handshaking
  while (!has_handshake) {
    if (Serial.available() && Serial.read() == 'H') {
      has_handshake = true;
      Serial.print('A');
    } 
  } 

 //Creates the mutex object
 count_mutex = xSemaphoreCreateMutex();
 
 xTaskCreate(ReceiveAndProcessData, "Receive", 128, NULL, 2, NULL);
 xTaskCreate(SendDataAndReceiveACK, "Send", 128, NULL, 2, NULL);
}


//Receives and process data. For now, just increments the counter.
void ReceiveAndProcessData(void *pvParameters) { 

 (void) pvParameters;
 
 for (;;) {
   if (xSemaphoreTake(count_mutex, portMAX_DELAY) == pdTRUE) {
     //Stores only up to 3 hits
     if (get_hit_count < 3)
       get_hit_count++;
     xSemaphoreGive(count_mutex);
   }
 }
}


void SendDataAndReceiveACK(void *pvParameters) {

 (void) pvParameters;
 
 for (;;) {

   // No data to send
   if (get_hit_count == 0) {
     vTaskDelay(10);
     continue;
   }
   
   //Sends data from the head of the buffer
   assemble_and_send_data();

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

   //Decrements count variable
   if (has_ack && xSemaphoreTake(count_mutex, portMAX_DELAY) == pdTRUE) {
     get_hit_count--;
     xSemaphoreGive(count_mutex);
   }

   //Reinits ACK to false for next cycle
   has_ack = false;
 }
}
