#include <LiquidCrystal.h>
#include <ESP32Servo.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128  // Ancho de la pantalla OLED, en píxeles
#define SCREEN_HEIGHT 64  // Alto de la pantalla OLED, en píxeles
#define LED_BUILTIN 2

// Declaración para una pantalla SSD1306 conectada a través de I2C (pines SDA, SCL)
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

int btnPiso1 = 35;
int btnPiso2 = 34;
int pisoAnterior = 0;
int pisoActual = 1;
int pisoDestino = 1;
const int servoPin = 18;
int gradosObjetivo = 0;
int gradosActuales = 0;
int TOUCH_SENSOR_VALUE = 0;
bool LED = false;
Servo servo;

void setup() {
  Serial.begin(2000000);
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(btnPiso1, INPUT_PULLUP);
  pinMode(btnPiso2, INPUT_PULLUP);
  // Inicializar la pantalla SSD1306
  Serial.print("Inicializando pantalla ");
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("Fallo en la asignación de SSD1306"));
    for (;;) {
      // Se repite indefinidamente si falla la inicialización de la pantalla
    }
  }
  delay(300);
  display.setTextColor(WHITE);
  display.setTextSize(1);
  display.clearDisplay();
  display.setRotation(2);
  dibujarGUI(0);
  Serial.println("Inicializado elevador");
  servo.attach(servoPin, 544, 2400);
  servo.write(0);  //Reiniciar servo a 0 grados
}

void loop() {


  if (digitalRead(btnPiso1) == LOW) {
    pisoDestino = 1;

  } else if (digitalRead(btnPiso2) == LOW) {
    pisoDestino = 2;
  } else if (touchRead(T7) < 70) {
    pisoDestino = 3;
  }


  if (pisoDestino != pisoActual) {
    Serial.println("Piso Destino = " + String(pisoDestino));
    cambiarPiso(pisoDestino);
  }
}

void cambiarPiso(int pisoDestino) {
  switch (pisoDestino) {
    case 1:
      gradosObjetivo = 0;
      break;
    case 2:
      gradosObjetivo = 90;
      break;
    case 3:
      gradosObjetivo = 180;
      break;
  }
  while (gradosActuales != gradosObjetivo) {
    if (LED) {
      digitalWrite(LED_BUILTIN, LOW);
      LED = false;
    } else {
      digitalWrite(LED_BUILTIN, HIGH);
      LED = true;
    }

    display.clearDisplay();
    if (gradosObjetivo > gradosActuales) {
      gradosActuales++;
      dibujarGUI(1);
    } else if (gradosObjetivo < gradosActuales) {
      gradosActuales--;
      dibujarGUI(2);
    }
    servo.write(gradosActuales);
    if (gradosActuales > 0 && gradosActuales < 40) {
      pisoActual = 1;
    } else if (gradosActuales > 70 && gradosActuales < 100) {
      pisoActual = 2;
    } else if (gradosActuales > 110 && gradosActuales <= 120) {
      pisoActual = 3;
    }
    delay(10);
  }
  dibujarGUI(0);
  pisoAnterior = pisoActual;
  pisoActual = pisoDestino;
}
void dibujarGUI(int estado) {
  display.clearDisplay();
  display.setCursor(0, 0);
  display.print("|CyberSys Elevadores|");
  display.setCursor(0, 60 - map(gradosActuales, 0, 180, 5, 50));
  if (estado == 1) {
    display.print("^");
    display.setCursor(15, 20);
    display.print("Subiendo a piso " + String(pisoDestino));
  } else if (estado == 2) {
    display.print("v");
    display.setCursor(15, 20);
    display.print("Bajando a piso " + String(pisoDestino));
  } else {
    display.print("#");
  }


  display.setCursor(15, 50);
  display.print("Piso Actual: " + String(pisoActual));

  display.display();
}