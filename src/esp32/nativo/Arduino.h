// Camada mínima da API Arduino para compilar o firmware no computador (modo lote, sem hardware).
// Só reproduz o que o firmware usa: Serial, pinos e tempo. Não emula o ESP32.
#pragma once
#include <cstdarg>
#include <cstdint>
#include <cstdio>

#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2

class SerialNativo {
 public:
  void begin(unsigned long) {}
  void print(const char* s) { std::fputs(s, stdout); }
  void println(const char* s) { std::fputs(s, stdout); std::fputc('\n', stdout); }
  void printf(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);
    std::vprintf(fmt, args);
    va_end(args);
  }
};
extern SerialNativo Serial;

inline void pinMode(int, int) {}
inline void digitalWrite(int, int) {}
inline int digitalRead(int) { return HIGH; }
inline int analogRead(int) { return 0; }
inline void tone(int, unsigned int, unsigned long) {}
inline void delay(unsigned long) {}
unsigned long millis();
