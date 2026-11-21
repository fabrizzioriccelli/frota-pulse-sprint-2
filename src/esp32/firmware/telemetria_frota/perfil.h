// Estrutura de um perfil de simulação: um veículo em um mês de operação.
#pragma once
#include <stdint.h>

// Classe de porte e perfil de operação (iguais aos de src/frota_pulse/config.py)
enum Classe { LEVE = 0, MEDIO = 1, PESADO = 2 };
enum Operacao { URBANA = 0, MISTA = 1, RODOVIARIA = 2 };

struct Perfil {
  const char* veiculo;      // identificador comum com o cadastro (ex.: "C-V07")
  const char* competencia;  // mês de referência AAAA-MM
  uint8_t classe;           // Classe
  uint8_t operacao;         // Operacao
  float tanque_l;           // capacidade do tanque, em litros
  float kml_ref;            // rendimento de referência do grupo no mês (km/L)
  float p_rpm_alto;         // chance, por leitura, de rotação acima da faixa verde (condução agressiva)
  float p_marcha_lenta;     // fração de leituras com motor ligado e veículo parado
  float p_excesso;          // chance, por leitura em movimento, de velocidade acima do limite
  float p_aquecimento;      // chance de ocorrer um episódio de superaquecimento na amostra
  float comb_inicial;       // nível de combustível no início da amostra (%)
  uint32_t semente;         // semente do gerador pseudoaleatório (reprodutível)
};

// Uma leitura de telemetria e o estado da simulação de um veículo.
struct Leitura {
  float velocidade;   // km/h
  float rpm;          // rotações por minuto
  float temperatura;  // °C
  float combustivel;  // % do tanque
};

struct Simulacao {
  const Perfil* p;
  int n;            // leituras já geradas
  float temp;       // temperatura atual (tem inércia)
  float comb;       // nível atual
  int inicio_aquec; // leitura em que começa o superaquecimento (-1000 = não ocorre)
};
