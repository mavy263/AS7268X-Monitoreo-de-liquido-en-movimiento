#include <HardwareSerial.h>

HardwareSerial mySerial(2); 

void setup() {
  Serial.begin(115200);
  mySerial.begin(115200, SERIAL_8N1, 16, 17);
  delay(2000);

  mySerial.println("ATLED1=1");
  delay(200);
  mySerial.println("ATLED3=1");
  delay(200);
  mySerial.println("ATLED5=1");
  delay(200);
  mySerial.println("ATGAIN=3"); 
}

void loop() {
  mySerial.println("ATCDATA");
  delay(600); 
  
  String dataLine = "";
  while (mySerial.available()) {
    char c = mySerial.read();
    if (c == '\n' || c == '\r') {
      dataLine.trim();
      int comaCount = 0;
      for (int i = 0; i < dataLine.length(); i++) {
        if (dataLine[i] == ',') comaCount++;
      }
      if (comaCount >= 17) {
        Serial.println(dataLine); 
      }
      dataLine = "";
    } else {
      dataLine += c;
    }
  }
  delay(400); 
}
