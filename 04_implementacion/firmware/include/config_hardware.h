// ==============================================================================
// config_hardware.h - Cabecera Autogenerada por hardware_bridge.py
// ==============================================================================
// Placa de Desarrollo: Heltec Wireless Stick Lite V3
// SoC/Microcontrolador: ESP32-S3FN8
// Enlace de Radio: SX1262 LoRa
// ATENCIÓN: No edites este archivo manualmente; edita heltec_wsl_v3_pins.yaml
// ==============================================================================

#ifndef CONFIG_HARDWARE_H
#define CONFIG_HARDWARE_H

// --- Especificaciones del Host SoC ---
#define SO_PLACA_MODELO "Heltec Wireless Stick Lite V3"
#define SO_PLACA_SOC "ESP32-S3FN8"
#define SO_PLACA_FREQ_MHZ 240
#define SO_PLACA_RADIO "SX1262 LoRa"

// --- Pines para LORA_SPI ---
#define PIN_LORA_SPI_SCK 9
#define PIN_LORA_SPI_MISO 11
#define PIN_LORA_SPI_MOSI 10
#define PIN_LORA_SPI_NSS 8
#define PIN_LORA_SPI_RST 12
#define PIN_LORA_SPI_BUSY 13
#define PIN_LORA_SPI_DIO1 14

// --- Pines para SENSORES_I2C ---
#define PIN_SENSORES_I2C_SDA 41
#define PIN_SENSORES_I2C_SCL 42
#define CONFIG_SENSORES_I2C_MODELO_SENSOR "SHT31"
#define PIN_SENSORES_I2C_FRECUENCIA_HZ 100000

// --- Pines para GPS_UART ---
#define PIN_GPS_UART_RX 43
#define PIN_GPS_UART_TX 44
#define PIN_GPS_UART_BAUDRATE 9600
#define CONFIG_GPS_UART_MODELO_GPS "U-blox NEO-6M"

// --- Pines para AUXILIARES ---
#define PIN_AUXILIARES_LED_ESTADO 35
#define PIN_AUXILIARES_ADC_BATERIA 1
#define PIN_AUXILIARES_BOTON_RESET 0

#endif // CONFIG_HARDWARE_H
