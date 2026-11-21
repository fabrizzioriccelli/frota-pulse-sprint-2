"""Configuração central do pipeline da Sprint 2: caminhos, categorias, grupos de comparação e limites.

Todos os limites usados nas regras ficam aqui, em um só lugar, com a justificativa ao lado. Os documentos em
docs/ citam estes valores; se um limite mudar, a documentação deve mudar junto.
"""
from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DADOS = RAIZ / "data"
SINTETICO = DADOS / "sintetico"          # massa de referência da Sprint 1 (fonte da simulação)
BRUTOS = DADOS / "raw"                   # arquivos de entrada simulados, como chegariam do cliente
TELEMETRIA = DADOS / "telemetria"        # leituras do ESP32
PROCESSADOS = DADOS / "processed"        # bases tratadas e consolidadas
SAIDAS = RAIZ / "outputs"
RELATORIOS = SAIDAS / "reports"
GRAFICOS = SAIDAS / "charts"
PREVISOES = SAIDAS / "predictions"

# Categorias de custo da Sprint 2. Seguro entra em OUTROS (subcategoria preservada) para seguir as seis categorias
# pedidas; locação também, mas é marcada para não distorcer a comparação de custo total (ver GRUPOS).
CATEGORIAS = ["COMBUSTIVEL", "MANUTENCAO", "PEDAGIO", "MULTAS", "IMPOSTOS", "OUTROS"]
NOME_CATEGORIA = {"COMBUSTIVEL": "Combustível", "MANUTENCAO": "Manutenção", "PEDAGIO": "Pedágio", "MULTAS": "Multas",
                  "IMPOSTOS": "Impostos", "OUTROS": "Outros"}

# Termos encontrados nas fontes (texto livre do ERP, campos de produto, tipos de ordem de serviço) -> categoria.
# A busca é feita em texto sem acento e em minúsculas; a primeira chave que aparecer no texto decide.
MAPA_CATEGORIA = [
    ("ipva", "IMPOSTOS"), ("licenciamento", "IMPOSTOS"), ("taxa detran", "IMPOSTOS"),
    ("seguro", "OUTROS"), ("apolice", "OUTROS"), ("locacao", "OUTROS"), ("lavagem", "OUTROS"),
    ("estacionamento", "OUTROS"), ("telemetria", "OUTROS"), ("rastreamento", "OUTROS"),
    ("multa", "MULTAS"), ("infracao", "MULTAS"),
    ("pedagio", "PEDAGIO"), ("tag", "PEDAGIO"),
    ("diesel", "COMBUSTIVEL"), ("gasolina", "COMBUSTIVEL"), ("etanol", "COMBUSTIVEL"), ("combustivel", "COMBUSTIVEL"),
    ("revisao", "MANUTENCAO"), ("reparo", "MANUTENCAO"), ("pneu", "MANUTENCAO"), ("oficina", "MANUTENCAO"),
    ("franquia", "MANUTENCAO"), ("manutencao", "MANUTENCAO"),
]

# Grupos de comparação. Um veículo só é comparado com outros de mesmo porte, mesmo perfil de operação e mesma
# categoria: automóvel e utilitário, ou caminhão truck e cavalo mecânico, têm consumos esperados diferentes, e
# misturá-los faria um tipo de veículo parecer ineficiente só por ser o que é.
# Chave: (classe_peso, perfil de operação, categoria_id) -> (código, nome).
PERFIL_OPERACAO = {"urbana_servicos": "urbana", "distribuicao_regional": "mista",
                   "rodoviario_longa_distancia": "rodoviaria"}
GRUPOS = {
    ("leve", "urbana", "LEVE_PASSEIO"): ("LEVE_URBANA_AUTOMOVEL", "Leve urbana (automóvel)"),
    ("leve", "urbana", "UTIL_LEVE"): ("LEVE_URBANA_UTILITARIO", "Leve urbana (utilitário)"),
    ("leve", "mista", "UTIL_LEVE"): ("LEVE_MISTA_UTILITARIO", "Leve mista (utilitário)"),
    ("medio", "mista", "VUC"): ("MEDIA_MISTA_VUC", "Média mista (VUC)"),
    ("medio", "mista", "CAM_TOCO"): ("MEDIA_MISTA_TOCO", "Média mista (caminhão toco)"),
    ("pesado", "rodoviaria", "CAM_TRUCK"): ("PESADA_RODOVIARIA_TRUCK", "Pesada rodoviária (truck)"),
    ("pesado", "rodoviaria", "CAV_SEMI"): ("PESADA_RODOVIARIA_CAVALO", "Pesada rodoviária (cavalo mecânico)"),
}
MIN_VEICULOS_GRUPO = 5   # abaixo disso, a mediana do grupo não é uma referência estável

# Diagnóstico por regras: limites de gap desfavorável, em %. Justificativa e verificação empírica em
# docs/metodologia.md (seção Diagnóstico por regras).
LIMITE_ATENCAO = 5.0
LIMITE_INEFICIENTE = 15.0
KM_MINIMO_FRACAO = 0.25  # veículo com km abaixo de 25% da mediana do grupo: custo por km dominado por custo fixo

# Data de referência da análise (recebimento dos arquivos). Datas posteriores são consideradas inválidas.
DATA_REFERENCIA = "2026-07-10"
# Janela de análise de cada empresa (meses com dados completos de quilometragem e custos)
JANELAS = {"EMP-A": ("2025-10", "2026-03"), "EMP-B": ("2025-07", "2026-06"), "EMP-C": ("2025-07", "2026-06")}

# Qualidade: faixas de plausibilidade (valores fora delas não são apagados; vão para quarentena com motivo)
PRECO_LITRO = {"gasolina": (4.0, 9.5), "etanol": (2.5, 7.0), "diesel_s10": (4.0, 9.5), "diesel_s500": (4.0, 9.5)}
TOLERANCIA_TANQUE = 1.05      # litros abastecidos até 105% da capacidade do tanque (bocal, reserva técnica)
KM_DIA_MAXIMO = {"leve": 900, "medio": 1000, "pesado": 1300}  # km por dia de operação acima disso é incoerente
TOLERANCIA_VALOR = 0.02       # valor total x litros x preço: até 2% de diferença (arredondamento do posto)

# Telemetria (limites operacionais usados pelo firmware do ESP32; espelhados em src/esp32/firmware/limites.h)
LIMITES_TELEMETRIA = {
    "leve": {"vel_max_urbana": 60, "vel_max_rodovia": 110, "rpm_max_verde": 3000, "rpm_limite": 4500,
             "temp_limite": 105, "comb_min": 15},
    "medio": {"vel_max_urbana": 60, "vel_max_rodovia": 90, "rpm_max_verde": 2000, "rpm_limite": 2600,
              "temp_limite": 105, "comb_min": 15},
    "pesado": {"vel_max_urbana": 60, "vel_max_rodovia": 90, "rpm_max_verde": 1800, "rpm_limite": 2300,
               "temp_limite": 105, "comb_min": 15},
}

# Machine Learning
SEMENTE = 42
FRACAO_TESTE = 0.30
