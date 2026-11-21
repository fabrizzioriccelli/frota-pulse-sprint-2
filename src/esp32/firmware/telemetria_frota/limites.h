// Limites operacionais usados na detecção de anomalias (espelham LIMITES_TELEMETRIA em src/frota_pulse/config.py).
// Justificativas em docs/telemetria-esp32.md.
#pragma once

struct Limites {
  float vel_max_urbana;   // km/h em operação urbana
  float vel_max_rodovia;  // km/h em rodovia
  float rpm_max_verde;    // fim da faixa de rotação econômica
  float rpm_limite;       // rotação acima da qual a leitura é anomalia
  float temp_limite;      // °C do líquido de arrefecimento
  float comb_min;         // % de combustível abaixo do qual o veículo entra na reserva operacional
};

//                       urbana rodovia verde  limite temp  comb
const Limites LIMITES[3] = {{60, 110, 3000, 4500, 105, 15},   // LEVE
                            {60,  90, 2000, 2600, 105, 15},   // MEDIO
                            {60,  90, 1800, 2300, 105, 15}};  // PESADO

// Códigos de alerta (bits)
const uint8_t A_TEMP_ALTA = 1, A_RPM_ALTO = 2, A_VEL_EXCESSO = 4, A_COMB_BAIXO = 8, A_SENSOR_INCOERENTE = 16;
