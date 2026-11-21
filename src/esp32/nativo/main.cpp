// Ponto de entrada da compilação nativa: chama setup() uma vez (o modo lote gera todas as leituras no setup).
#include <chrono>
#include "Arduino.h"

SerialNativo Serial;
static const auto inicio = std::chrono::steady_clock::now();
unsigned long millis() {
  return (unsigned long)std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - inicio)
      .count();
}

void setup();
extern bool concluido;

int main() {
  setup();
  return concluido ? 0 : 1;
}
