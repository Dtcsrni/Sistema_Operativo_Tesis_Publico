/*
Este programa recibe dos valores enteros positivos por el puerto 
serial: Pin y Estado.
Pin es un numero entre 1 y 6.
Estado es un numero entre 0 (apagado) y 1 (encendido).
Pin sirve para direccionar cualquiera de los 6 LEDs mientras 
que Estado sirve para controlar el estado del LED previamente 
seleccionado usando Pin.
Nota: Los valores Pin y Estado deben estar separados por un espacio.
*/

#define espera 3000


String logSerial = "";
int pin[] = { 8, 9, 10, 11, 12, 13 };
int Estado = 0;
int PinElegido = 0;
int tamanoArray = 0;
int comandosTotales = 0;

void setup() {
  Serial.begin(115200);
  tamanoArray = sizeof(pin) / sizeof(pin[0]);
  for (int i = 0; i < tamanoArray; i++) {
    pinMode(pin[i], OUTPUT);
  }
}

void loop() {
  if (Serial.available() > 0) {
    procesarComando();
    Serial.println("Ejecutados: " + String(comandosTotales) + " comandos");
    comandosTotales = 0;
  }
}


void procesarComando() {
  String texto;
  int caracteresXComando = 3;
  int contadorCaracteres = 0;
  Serial.println("Procesando Comando: ");
  texto = Serial.readString();

  for (int i = 0; i < texto.length(); i++) {  ///Se recorre cada caracter del mensaje
    contadorCaracteres++;

    if (isDigit(texto.charAt(i))) {
      if (contadorCaracteres == 1)  //Si corresponde a una letra de Letras, entonces se envía el Morse correspondiente a encenderMorse
        PinElegido = String(texto.charAt(i)).toInt();

      if (contadorCaracteres == 2) {
        if (String(texto.charAt(i)).toInt() == 1) {
          Estado = 3;

        } else if (String(texto.charAt(i)).toInt() == 0) {
          Estado = 2;
        }
        Serial.println(Estado);
      }
      if (contadorCaracteres == 3 && Estado != 3 && Estado != 2) {  //Si corresponde a una letra de Letras, entonces se envía el Morse correspondiente a encenderMorse
        Estado = String(texto.charAt(i)).toInt();
      }
    }
    if (contadorCaracteres == caracteresXComando) {
      contadorCaracteres = -1;
      comandosTotales++;
      ejecutarComando();
    }
  }
}
void ejecutarComando() {
  Serial.println("Ejecutando Comando:");

  if (Estado == 0) {
    digitalWrite(pin[PinElegido - 1], LOW);
    logSerial = "LED " + String(PinElegido) + " APAGADO";
  }
  if (Estado == 1) {
    digitalWrite(pin[PinElegido - 1], HIGH);
    logSerial = "LED " + String(PinElegido) + " ENCENDIDO";
  }
  if (Estado == 2) {
    for (int i = 0; i < tamanoArray; i++) {
      digitalWrite(pin[i], LOW);
    }
    logSerial = "TODOS LOS LED APAGADOS";
  }
  if (Estado == 3) {
    for (int i = 0; i < tamanoArray; i++) {
      digitalWrite(pin[i], HIGH);
    }
    logSerial = "TODOS LOS LED ENCENDIDOS";
  }
  Estado = 0;
  Serial.println(logSerial);
}
void DeserializarJSON(String json)
{
    StaticJsonDocument<250> doc;
    DeserializationError error = deserializeJson(doc, json);
    if (error) { return; }//si hay error se finaliza programa

    int estado = doc["estado"];
    int led = doc["led"];
    bool stat = doc["status"];
    float value = doc["value"];

    Serial.println(text);
    Serial.println(id);
    Serial.println(stat);
    Serial.println(value);
}