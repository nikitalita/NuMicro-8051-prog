#include <Arduino.h>



int limits[5] = {
    0x1F,       // 5 bit
    0x3F,       // 6 bit
    0x7F,       // 7 bit
    0xFF,       // 8 bit
    0x1FF,      // 9 bit
};


void setup() {
    // Serial connectio over UART for test output    
    Serial.begin(115200);
    Serial2.begin(115200);

    delay(500);
}

int counter = 0;

// void test_usart(int mode, int limit) {

//     // set up the USARTS 
//     Serial1.begin(115200, modes[mode]);
//     Serial2.begin(115200);
//     Serial3.begin(115200, modes[mode]);

//     while(true){
//         int result2 = Serial2.read();
//         if(result2 != -1) {
//             Serial.print("Serial2 received ");
//             Serial.print(result2, HEX);
//             Serial.println(", OK! ");
//         }
//         Serial2.print("Hi!");
//         Serial2.write(result2);
//         Serial2.println();
//     }
//       for(int i=0; i <= limits[limit]; i++) {
//         Serial1.write(i);
//         Serial2.write(i);
//         Serial3.write(i);   
        
//         counter++;
        
//         while(!Serial1.available());
//         while(!Serial2.available());
//         while(!Serial3.available());

//         int result1 = Serial1.read();
//         int result2 = Serial2.read();
//         int result3 = Serial3.read();

//         if(result1 == i) {
//             Serial.print("Serial1 sent ");
//             Serial.print(i, HEX);
//             Serial.print(", received ");
//             Serial.print(result1, HEX);
//             Serial.println(", OK! ");
//         } else {
//             Serial.print("Serial1 sent ");
//             Serial.print(i, HEX);
//             Serial.print(", received ");
//             Serial.print(result1, HEX);
//             Serial.println(", >>>> FAIL <<<< ");
//         }
        
//         if(result2 == i) {
//             Serial.print("Serial2 sent ");
//             Serial.print(i, HEX);
//             Serial.print(", received ");
//             Serial.print(result2, HEX);
//             Serial.println(", OK! ");
//         } else {
//             Serial.print("Serial2 sent ");
//             Serial.print(i, HEX);
//             Serial.print(", received ");
//             Serial.print(result2, HEX);
//             Serial.println(", >>>> FAIL <<<< ");
//         }
        
//         if(result3 == i) {
//             Serial.print("Serial3 sent ");
//             Serial.print(i, HEX);
//             Serial.print(", received ");
//             Serial.print(result3, HEX);
//             Serial.println(", OK! ");
//         } else {
//             Serial.print("Serial3 sent ");
//             Serial.print(i, HEX);
//             Serial.print(", received ");
//             Serial.print(result3, HEX);
//             Serial.println(", >>>> FAIL <<<< ");
//         }

//         Serial.print(counter, DEC);
//         Serial.println(" bytes sent");
        
//     }
    
// }

void loop() {
  // put your main code here, to run repeatedly:    
    int result2 = Serial2.read();
    if(result2 != -1) {
        Serial.print("Serial2 received ");
        Serial.print(result2, HEX);
        Serial.println(", OK! ");
        Serial2.print("Hi!");
        Serial2.write(result2);
        Serial2.println();
    }

    // // for each frame width
    // for(int i=0; i<4; i++) {
    //     // for each mode in this frame width
    //     for(int j=0; j<6; j++) {
    //         Serial.print("Test mode ");
    //         Serial.println(i*6 + j, DEC);
    //         test_usart(i*6 +j, i);
    //         delay(500);
    //     }
    // }
       
    // delay(1000);
}