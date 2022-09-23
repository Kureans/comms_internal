#define TIMEOUT 5000

volatile int gun_fire_count;
bool has_handshake;
bool has_ack;
char seq_no;
String padding = "111111111111"; //12 bytes padding

void trigger_ISR() {
  if (gun_fire_count < 3) {
    gun_fire_count++;
  }
}

//Assembles the 15 byte packet and sends it out over serial
void assemble_and_send_data() {
    String packet = "";
    packet += "F";
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
  gun_fire_count = 0;
  seq_no = '0';

  //Initial Handshaking
  while (!has_handshake) {
    if (Serial.available() && Serial.read() == 'H') {
      has_handshake = true;
      Serial.print('A');
    } 
  } 
}


void loop() {

  //Sends data from the head of the buffer
  if (gun_fire_count > 0) {
    assemble_and_send_data();
  }

  //Initialises timer to check for packet timeout
  unsigned long curr_time = millis();
  
  while (!has_ack && ((millis() - curr_time) < TIMEOUT)) {
    if (Serial.available()) {
      
      //Should read either 'H' for handshake or 'A' for normal ACK
      char hdr = Serial.read();

      //Successfully received ACK, and flips seq_no for next packet
      if (hdr == 'A') {
        has_ack = true;
        seq_no = (seq_no == '0') ? '1' : '0';
        gun_fire_count--;
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
