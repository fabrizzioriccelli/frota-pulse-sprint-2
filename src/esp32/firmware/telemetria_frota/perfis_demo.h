// Perfis de demonstração para o Wokwi: um veículo por porte. B-V23 dirige dentro da faixa; B-V12 (caminhão antigo
// com reparos de motor) tende a superaquecer; C-V07 (queda de rendimento desde jan/2026) roda com rotação alta,
// excesso de velocidade e pouco combustível.
// Os mesmos identificadores existem no cadastro da frota (data/raw/cadastro/cadastro_frota.csv).
#pragma once
#include "perfil.h"

const int TOTAL_PERFIS = 3;
const Perfil PERFIS[TOTAL_PERFIS] = {
  // veículo  mês        classe  operação    tanque  km/L ref rpm alto lenta excesso aquec. comb.  semente
  {"B-V23", "2026-06", LEVE,   MISTA,      55.0f,  9.50f,  0.05f,  0.08f, 0.02f,  0.05f,  80.0f, 101u},
  {"B-V12", "2026-06", MEDIO,  MISTA,      275.0f, 4.75f,  0.12f,  0.10f, 0.03f,  0.90f,  60.0f, 202u},
  {"C-V07", "2026-06", PESADO, RODOVIARIA, 600.0f, 2.36f,  0.39f,  0.25f, 0.15f,  0.10f,  18.0f, 303u},
};
