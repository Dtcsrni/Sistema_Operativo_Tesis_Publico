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


String  logSerial = "";
int pin[] = {8,9,10,11,12,13};
int tamanoArray = 0;
void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  tamanoArray = sizeof(pin) / sizeof(pin[0]);
  Serial.println(tamanoArray);
  for(int i=0;i<tamanoArray;i++){
  pinMode(pin[i], OUTPUT);
  }
}

void loop() {
  // put your main code here, to run repeatedly:

  for(int i=0;i<tamanoArray;i++){
  digitalWrite(pin[i], HIGH);
    logSerial = "LED"+String(pin[i])+" encendido";
  Serial.println(logSerial);
  delay(espera);
  digitalWrite(pin[i], LOW);
    logSerial = "LED"+String(pin[i]) +" apagado";
  Serial.println(logSerial);
  }


}
