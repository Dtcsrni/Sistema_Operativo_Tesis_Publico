/*
El sketch utiliza cadenas JSON para enviar  los valores analógicos leídos de 2 potenciómetros y 2 motones, y recibe el estado de 6 leds 
Autor: Erick Renato Vega Ceron
*/
#include <ArduinoJson.h>

#define espera 3000

const uint8_t potenciometro1 = A0;
const uint8_t potenciometro2 = A1;

const int btnPIN1 = 6;
const int btnPIN2 = 7;

String logSerial = "";
const int numLEDS = 6;  
int pinLEDs[numLEDS] = {8, 9, 10, 11, 12, 13}; 
int Estado = 0;
int PinElegido = 0;
int tamanoArray = 0;
int comandosTotales = 0;
int estado = 0;
int led = 0;
int pot1 = 0;
int pot2 = 0;
int pot1Anterior = 0;
int pot2Anterior = 0;

bool btn1 = false;
bool btn2 = false;
bool boton1Anterior = false;
bool boton2Anterior = false;
bool cambios = false;
String jsonComandos = "";
String comandoLed = "";
String mensajeSerial = "";

void setup() {
  Serial.begin(9600);
  for (int i = 0; i < numLEDS; i++) {
    pinMode(pinLEDs[i], OUTPUT); 
  }

  //Definir GPIO de botones
  pinMode(btnPIN1, INPUT_PULLUP);
  pinMode(btnPIN2, INPUT_PULLUP);
  pinMode(potenciometro1, INPUT);
  pinMode(potenciometro2, INPUT);
}

void loop() {

  if (Serial.available() > 0) {
    int pin = Serial.parseInt();  
    int estado = Serial.parseInt();  

    comandoLed = mensajeSerial;             //se obtiene la cadena de LED a mostrar
    procesarComandoLED(pin, estado);  //se procesa la cadena obtenida  para mostrar los LED
  }
  if (leerValoresAnalogicos()) {
    serializarJSON();
  }
}

bool leerValoresAnalogicos() {
  pot1Anterior = pot1;
  pot2Anterior = pot2;
  boton1Anterior = btn1;
  boton2Anterior = btn2;
  pot1 = map(analogRead(potenciometro1), 0, 1023, 0.05, 1000);
  pot2 = map(analogRead(potenciometro2), 0, 1023, 0.05, 1000);
  btn1 = !digitalRead(btnPIN1);
  btn2 = !digitalRead(btnPIN2);
  if (pot1 != pot1Anterior || pot2 != pot2Anterior || btn1 != boton1Anterior || btn2 != boton2Anterior)
    cambios = true;
  else
    cambios = false;

  return cambios;
}

void procesarComandoLED(int pin, int estado) {

  if ((pin >= 1 && pin <= 6 || pin == 7) && (estado == 0 || estado == 1)) {
    if (pin == 7) {
      for (int i = 0; i < numLEDS; i++) {
        digitalWrite(pinLEDs[i], estado);
      }

    } else {
      digitalWrite(pinLEDs[pin - 1], estado);

    }
  }
}


void serializarJSON() {
  String json;
  StaticJsonDocument<300> doc;
  doc["A0"] = pot1;
  doc["A1"] = pot2;
  doc["btn1"] = btn1;
  doc["btn2"] = btn2;
  serializeJson(doc, json);
  Serial.println(json);
}