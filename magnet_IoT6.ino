#include <ESP32Servo.h>
// line送信
#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "AP01-01";
const char* password =  "1qaz2wsxs";
 
const String endpoint = "https://maker.ifttt.com/trigger/";//定型url
const String eventName = "SchooMyIoT";//IFTTTのEvent Name
const String conn = "/with/key/";//定型url
const String Id = "SpluMUtU_DTXM5clG3iYt";//自分のIFTTTのYour Key
//const String value ="?value1=aaa&value2=bbbb&value3=ccccc";//値 value1=xxxx value2=xxxxx value3=xxxxx
//const String value ="?value1=a";   //値 value1=xxxx value2=xxxxx value3=xxxxx

#define hallpin 33 //INA:33 INB:32
#define ledPin 26 //OUTA:26 OUTB:13
#define moterPin 13
#define on LOW
#define off HIGH
Servo myservo;

byte val;
byte val2;
//bool ledOn = false; // LEDの状態を記録する変数
bool servoMoved = false; // Servoの動きを記録する変数
bool onceopen = false;
bool onceclose = false;
bool personcoming = false;
float gauss;

void setup() {
  // line送信
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi..");
  }
  Serial.println("Connected to the WiFi network");

  Serial.begin(115200);
  pinMode(hallpin, INPUT);
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, off);
  myservo.attach(moterPin, 700, 2300);
}

float gaussculc(){
  int base = 1650; // ゼロガウス(0G) = 2.5V(2500mV)
  // アナログ入力の値を電圧に変換(mV)
  float voltage = (analogRead(hallpin) / 4096.0) * 3.3 * 1000;
  float gauss = abs((voltage - base) / 3.3); // 1ガウス(1G) = 5mV
  delay(500);
  return gauss;
}

void rightrotate(){
  myservo.write(1300);
  delay(750);
  myservo.write(1500);
}

void leftrotate(){
  myservo.write(1700);
  delay(750);
  myservo.write(1500);
}

void resetrotation(){
  val2 = Serial.read();
  if ( val2 == 'r'){
    myservo.write(1300);
    delay(750);
    myservo.write(1500);
  }
  else if ( val2 == 'l') {
    myservo.write(1700);
    delay(750);
    myservo.write(1500);
  }
}

void loop() {
  //resetrotation();

  val = Serial.read();
  servoMoved = false;

  if(val == 'A'){
    personcoming = true;
    onceopen = false;

    if ((WiFi.status() == WL_CONNECTED)) {
 
      HTTPClient http;
 
      //http.begin(endpoint + eventName + conn + Id + value); //URLを指定
      http.begin(endpoint + eventName + conn + Id); //URLを指定
      int httpCode = http.GET();  //GETリクエストを送信
 
      if (httpCode == 200) { //返答がある場合
        Serial.println("200.OK");
      }else {
        Serial.println("Error on HTTP request");
      }
      http.end(); //Free the resources
      }
  }

  if(personcoming == true){
    gauss = gaussculc();

    // 磁石のプラスチック側（N極）をHallセンサーの「Hall」シルク側へ近づけるとgauss値が高くなる。
    if (gauss >= 130 && onceopen == false) {
      
      rightrotate();
      onceopen = true;
      delay(500);
      Serial.println("閉まっています");

    } else if(gauss >= 130 && onceclose == true) {
      digitalWrite(ledPin, off);
      delay(3500);
      leftrotate();
      personcoming = false;
      onceclose = false;
      delay(500);
      Serial.println("閉まっていますB");
    }
    else if(gauss < 130) {
      digitalWrite(ledPin, on);
      delay(500);
      onceopen = true;
      onceclose = true;
      delay(500);
      Serial.println("開いています");
    }
    else{
      Serial.println("開錠中");
    }
  }
  //Serial.println("待機中..");
  Serial.print("val:");
  Serial.println(val);
  //Serial.print("personcoming:");
  //Serial.println(personcoming);
  delay(200);
}