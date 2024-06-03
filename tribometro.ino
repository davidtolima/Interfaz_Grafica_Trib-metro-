#include <DHT.h>
#include <HX711.h>
#include <Adafruit_MLX90614.h>
#define DHTPIN 14
#define DHTTYPE DHT22
#define LOADCELL_DOUT_PIN 7
#define LOADCELL_SCK_PIN 8
#define MLX90614_ADDRESS 0x5A
#define COUNT_SENSOR_PIN 2
DHT dht(DHTPIN, DHTTYPE);
HX711 scale;
Adafruit_MLX90614 mlx = Adafruit_MLX90614();
volatile unsigned long Count = 0;
float humDHT,tempMLX,rad,weightVal,absweight = 0;
unsigned long tiempo; 
void setup(){
  while (!Serial){}
  Serial.begin(9600);
  dht.begin();
  scale.begin(LOADCELL_DOUT_PIN,LOADCELL_SCK_PIN);
  scale.set_scale(454.675);
  scale.tare();
  mlx.begin();
  mlx.writeEmissivityReg(62258);
  pinMode(COUNT_SENSOR_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(COUNT_SENSOR_PIN),countPulse,RISING);
}
void loop(){
  rad = 2*PI*Count;
  humDHT = dht.readHumidity();
  tempMLX = mlx.readObjectTempC();
  weightVal = scale.get_units(10);
  if (micros()-tiempo >= 200000){
  tiempo = micros();
  Serial.print(humDHT);
  Serial.print("|");
  Serial.print(tempMLX);
  Serial.print("|");
  Serial.print(rad);
  Serial.print("|");
  Serial.println(weightVal);
  }
}
void countPulse(){
  ++Count;
}