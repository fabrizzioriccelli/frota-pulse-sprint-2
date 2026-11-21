// Frota Pulse — telemetria simulada de veículos com ESP32 (Sprint 2)
//
// Lê velocidade, rotação do motor (RPM), temperatura do líquido de arrefecimento e nível de combustível, identifica
// anomalias por limites operacionais da categoria do veículo, sinaliza com LEDs e buzzer e escreve cada leitura no
// Monitor Serial em formato CSV.
//
// As quatro grandezas são ENTRADAS VIRTUAIS: no Wokwi, três potenciômetros e um potenciômetro deslizante fazem o papel
// dos sinais que, num veículo real, viriam do barramento do motor (OBD-II/CAN) e do sensor de nível. Não há sensor
// físico de velocidade, rotação ou temperatura no circuito.
//
// Três modos:
//   SENSORES  (Wokwi, padrão)  as leituras vêm dos potenciômetros, para testar os limites à mão;
//   ROTEIRO   (Wokwi, botão)   o firmware gera as leituras a partir do perfil do veículo selecionado;
//   LOTE      (compilação nativa com -DMODO_LOTE) gera 60 leituras para cada veículo-mês de perfis_lote.h, usado
//             para produzir o CSV de telemetria consumido pelo pipeline em Python.

#ifdef NATIVO
#include "Arduino.h"
#else
#include <Arduino.h>
#endif
#include "limites.h"
#if defined(MODO_LOTE) && !defined(PERFIS_DEMO)
#include "perfis_lote.h"   // gerado por src/simulacao/gerar_perfis_telemetria.py
#else
#include "perfis_demo.h"   // 3 veículos de demonstração (Wokwi)
#endif

// ---------------------------------------------------------------- pinos (ESP32 DevKit C; entradas no ADC1)
const int PINO_VELOCIDADE = 34;
const int PINO_RPM = 35;
const int PINO_TEMPERATURA = 32;
const int PINO_COMBUSTIVEL = 33;
const int PINO_BOTAO_MODO = 4;
const int PINO_BOTAO_VEICULO = 5;
const int LED_VERDE = 25;
const int LED_AMARELO = 26;
const int LED_VERMELHO = 27;
const int PINO_BUZZER = 14;

const unsigned long INTERVALO_MS = 1000;  // Wokwi: uma leitura por segundo
const int LEITURAS_POR_AMOSTRA = 60;      // lote: 60 leituras por veículo-mês (1 por minuto simulado = 1 hora)

// ---------------------------------------------------------------- gerador pseudoaleatório próprio (xorshift32)
// Usado em vez de random() para que o ESP32 e a compilação nativa produzam exatamente a mesma sequência.
static uint32_t estado_rng = 1;
void semear(uint32_t s) { estado_rng = s ? s : 1; }
float aleatorio() {
  estado_rng ^= estado_rng << 13;
  estado_rng ^= estado_rng >> 17;
  estado_rng ^= estado_rng << 5;
  return (estado_rng & 0xFFFFFF) / 16777216.0f;
}
float normal(float media, float dp) {  // aproximação pela soma de 6 uniformes
  float s = 0;
  for (int i = 0; i < 6; i++) s += aleatorio();
  return media + dp * (s - 3.0f) * 1.41421f;
}
float limitar(float x, float lo, float hi) { return x < lo ? lo : (x > hi ? hi : x); }
float arredondar(float x, float passo) { return (float)(long)(x / passo + (x >= 0 ? 0.5f : -0.5f)) * passo; }

// ---------------------------------------------------------------- leitura, simulação e avaliação
// Leitura e Simulacao ficam em perfil.h: o Arduino IDE (e o Wokwi) gera protótipos das funções antes da
// primeira função do .ino, e os tipos usados nesses protótipos precisam estar declarados num cabeçalho.

float limite_velocidade(const Perfil& p) {
  const Limites& L = LIMITES[p.classe];
  return p.operacao == URBANA ? L.vel_max_urbana : L.vel_max_rodovia;
}

void iniciar(Simulacao& s, const Perfil& p) {
  semear(p.semente);
  s.p = &p;
  s.n = 0;
  s.temp = normal(82, 2);
  s.comb = p.comb_inicial;
  s.inicio_aquec = aleatorio() < p.p_aquecimento ? 10 + (int)(aleatorio() * 40) : -1000;
}

// A leitura é arredondada para a resolução impressa no Monitor Serial ANTES da avaliação, para que o CSV e os
// alertas sejam sempre coerentes (ex.: 14,96% seria impresso como 15.0 e geraria um alerta de combustível baixo).
Leitura com_resolucao(Leitura r) {
  r.velocidade = arredondar(r.velocidade, 0.1f);
  r.rpm = arredondar(r.rpm, 1.0f);
  r.temperatura = arredondar(r.temperatura, 0.1f);
  r.combustivel = arredondar(r.combustivel, 0.1f);
  return r;
}

Leitura gerar(Simulacao& s) {
  const Perfil& p = *s.p;
  const Limites& L = LIMITES[p.classe];
  Leitura r;
  float vlim = limite_velocidade(p);

  // Velocidade: parado com motor ligado (marcha lenta) ou em movimento conforme o perfil de operação
  if (aleatorio() < p.p_marcha_lenta) {
    r.velocidade = 0;
  } else {
    float alvo;
    if (p.operacao == URBANA) alvo = normal(32, 12);
    else if (p.operacao == MISTA) alvo = aleatorio() < 0.5f ? normal(35, 12) : normal(72, 8);
    else alvo = normal(76, 6);
    if (aleatorio() < p.p_excesso) alvo = vlim + 5 + aleatorio() * 20;
    r.velocidade = limitar(alvo, 3, vlim + 40);
  }

  // Rotação: proporcional à velocidade numa marcha típica; condução agressiva leva acima da faixa verde
  float rpm_lenta = p.classe == LEVE ? 850 : 650;
  float coef = p.classe == LEVE ? 32 : (p.classe == MEDIO ? 17 : 14);
  if (r.velocidade == 0) r.rpm = normal(rpm_lenta, 30);
  else r.rpm = rpm_lenta + coef * r.velocidade + normal(0, 60);
  if (r.velocidade > 0 && aleatorio() < p.p_rpm_alto) r.rpm = L.rpm_max_verde * (1.15f + 0.45f * aleatorio());

  // Temperatura: aquece com a carga; um episódio de superaquecimento sobe cerca de 2,2 °C por leitura
  float alvo_temp = 86 + 5 * (r.velocidade / vlim) + normal(0, 1.0);
  int k = s.n - s.inicio_aquec;
  if (k >= 0 && k < 10) alvo_temp = 92 + k * 2.2f;
  s.temp += (alvo_temp - s.temp) * 0.5f;
  r.temperatura = s.temp;

  // Combustível: consumo de 1 minuto no rendimento do grupo, piorado pela condução agressiva
  float kml = p.kml_ref * (1 - 0.4f * p.p_rpm_alto);
  float litros = r.velocidade > 0 ? (r.velocidade / 60.0f) / kml : 0.012f * p.tanque_l / 100.0f;
  s.comb = limitar(s.comb - litros / p.tanque_l * 100.0f, 0, 100);
  r.combustivel = s.comb;

  // Falha rara do sinal de rotação (leitura zerada com o veículo em movimento)
  if (r.velocidade > 20 && aleatorio() < 0.003f) r.rpm = 0;

  s.n++;
  return com_resolucao(r);
}

uint8_t avaliar(const Leitura& r, const Perfil& p) {
  const Limites& L = LIMITES[p.classe];
  uint8_t a = 0;
  if (r.temperatura > L.temp_limite) a |= A_TEMP_ALTA;
  if (r.rpm > L.rpm_limite) a |= A_RPM_ALTO;
  if (r.velocidade > limite_velocidade(p)) a |= A_VEL_EXCESSO;
  if (r.combustivel < L.comb_min) a |= A_COMB_BAIXO;
  if (r.velocidade > 20 && r.rpm < 300) a |= A_SENSOR_INCOERENTE;
  return a;
}

int contar_bits(uint8_t a) {
  int n = 0;
  for (; a; a >>= 1) n += a & 1;
  return n;
}

// 0 = NORMAL, 1 = ATENCAO, 2 = CRITICO
int status_de(uint8_t a) {
  if (a == 0) return 0;
  if ((a & (A_TEMP_ALTA | A_SENSOR_INCOERENTE)) || contar_bits(a) >= 2) return 2;
  return 1;
}

const char* NOME_STATUS[3] = {"NORMAL", "ATENCAO", "CRITICO"};

void sinalizar(int status) {
  digitalWrite(LED_VERDE, status == 0 ? HIGH : LOW);
  digitalWrite(LED_AMARELO, status == 1 ? HIGH : LOW);
  digitalWrite(LED_VERMELHO, status == 2 ? HIGH : LOW);
  if (status == 2) tone(PINO_BUZZER, 1000, 150);
}

void imprimir_alertas(uint8_t a) {
  const char* nomes[5] = {"TEMP_ALTA", "RPM_ALTO", "VEL_EXCESSO", "COMB_BAIXO", "SENSOR_INCOERENTE"};
  bool primeiro = true;
  for (int i = 0; i < 5; i++) {
    if (a & (1 << i)) {
      if (!primeiro) Serial.print("|");
      Serial.print(nomes[i]);
      primeiro = false;
    }
  }
}

void imprimir(unsigned long t_s, const Perfil& p, const char* modo, int n, const Leitura& r, uint8_t a) {
  Serial.printf("%lu,%s,%s,%s,%d,%.1f,%.0f,%.1f,%.1f,", t_s, p.veiculo, p.competencia, modo, n, r.velocidade, r.rpm,
                r.temperatura, r.combustivel);
  imprimir_alertas(a);
  Serial.printf(",%s\n", NOME_STATUS[status_de(a)]);
}

void cabecalho() {
  Serial.println("timestamp_s,veiculo_id,competencia,modo,leitura,velocidade_kmh,rpm,temperatura_c,"
                 "nivel_combustivel_pct,alertas,status");
}

// ---------------------------------------------------------------- modos interativos (Wokwi)
int modo_atual = 0;     // 0 = SENSORES, 1 = ROTEIRO
int veiculo_atual = 0;  // índice em PERFIS
Simulacao sim;
unsigned long ultima_leitura = 0;
int botao_modo_antes = HIGH, botao_veiculo_antes = HIGH;
bool concluido = false;

float escala(int pino, float minimo, float maximo) { return minimo + analogRead(pino) / 4095.0f * (maximo - minimo); }

Leitura ler_sensores(const Perfil& p) {
  const Limites& L = LIMITES[p.classe];
  Leitura r;
  r.velocidade = escala(PINO_VELOCIDADE, 0, L.vel_max_rodovia + 40);
  r.rpm = escala(PINO_RPM, 0, L.rpm_limite * 1.3f);
  r.temperatura = escala(PINO_TEMPERATURA, 40, 120);
  r.combustivel = escala(PINO_COMBUSTIVEL, 0, 100);
  return com_resolucao(r);
}

void anunciar() {
  const Perfil& p = PERFIS[veiculo_atual];
  const Limites& L = LIMITES[p.classe];
  Serial.printf("# modo=%s veiculo=%s limites: velocidade %.0f km/h, rpm %.0f, temperatura %.0f C, combustivel %.0f%%\n",
                modo_atual == 0 ? "SENSORES" : "ROTEIRO", p.veiculo, limite_velocidade(p), L.rpm_limite,
                L.temp_limite, L.comb_min);
}

void setup() {
  Serial.begin(115200);
#ifdef MODO_LOTE
  cabecalho();
  for (int i = 0; i < TOTAL_PERFIS; i++) {
    iniciar(sim, PERFIS[i]);
    for (int k = 0; k < LEITURAS_POR_AMOSTRA; k++) {
      Leitura r = gerar(sim);
      imprimir((unsigned long)k * 60, PERFIS[i], "lote", k + 1, r, avaliar(r, PERFIS[i]));
    }
  }
  concluido = true;
#else
  pinMode(PINO_BOTAO_MODO, INPUT_PULLUP);
  pinMode(PINO_BOTAO_VEICULO, INPUT_PULLUP);
  pinMode(LED_VERDE, OUTPUT);
  pinMode(LED_AMARELO, OUTPUT);
  pinMode(LED_VERMELHO, OUTPUT);
  pinMode(PINO_BUZZER, OUTPUT);
  iniciar(sim, PERFIS[veiculo_atual]);
  cabecalho();
  anunciar();
#endif
}

void loop() {
#ifndef MODO_LOTE
  int bm = digitalRead(PINO_BOTAO_MODO), bv = digitalRead(PINO_BOTAO_VEICULO);
  if (bm == LOW && botao_modo_antes == HIGH) {
    modo_atual = 1 - modo_atual;
    iniciar(sim, PERFIS[veiculo_atual]);
    anunciar();
  }
  if (bv == LOW && botao_veiculo_antes == HIGH) {
    veiculo_atual = (veiculo_atual + 1) % TOTAL_PERFIS;
    iniciar(sim, PERFIS[veiculo_atual]);
    anunciar();
  }
  botao_modo_antes = bm;
  botao_veiculo_antes = bv;

  unsigned long agora = millis();
  if (agora - ultima_leitura >= INTERVALO_MS) {
    ultima_leitura = agora;
    const Perfil& p = PERFIS[veiculo_atual];
    Leitura r = modo_atual == 0 ? ler_sensores(p) : gerar(sim);
    uint8_t a = avaliar(r, p);
    sinalizar(status_de(a));
    imprimir(agora / 1000, p, modo_atual == 0 ? "sensores" : "roteiro", sim.n, r, a);
  }
  delay(20);
#endif
}
