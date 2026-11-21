#!/usr/bin/env python3
"""Gera os perfis de condução que o firmware do ESP32 usa para simular a telemetria de cada veículo-mês.

Hipótese de simulação (declarada na documentação): o comportamento de condução explica parte do consumo. Como a massa
da Sprint 1 já tem o rendimento (km/L) de cada veículo-mês, a ordem é invertida por conveniência: o rendimento é lido e
o comportamento é sorteado de forma coerente com ele. Veículo que rende pior que a mediana do seu grupo no mês recebe
mais rotação acima da faixa verde, mais marcha lenta e mais excesso de velocidade, com ruído. Meses com reparo de motor
ou arrefecimento recebem maior chance de um episódio de superaquecimento.

Saída: src/esp32/firmware/telemetria_frota/perfis_lote.h (lido pelo firmware quando compilado em modo lote).

Uso:
    python src/simulacao/gerar_perfis_telemetria.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from frota_pulse.config import GRUPOS, PERFIL_OPERACAO, RAIZ, SEMENTE, SINTETICO  # noqa: E402

SAIDA = RAIZ / "src" / "esp32" / "firmware" / "telemetria_frota" / "perfis_lote.h"
CLASSE = {"leve": 0, "medio": 1, "pesado": 2}
OPERACAO = {"urbana": 0, "mista": 1, "rodoviaria": 2}


def grupo_do_veiculo(classe: str, operacao: str, categoria: str) -> str:
    return GRUPOS[(classe, operacao, categoria)][0]


def main() -> None:
    rng = np.random.default_rng(SEMENTE)
    veic = (pd.read_csv(SINTETICO / "veiculos.csv")
            .merge(pd.read_csv(SINTETICO / "frotas.csv"), on="frota_id")
            .merge(pd.read_csv(SINTETICO / "categorias_veiculo.csv"), on="categoria_id"))
    veic["operacao"] = veic.modalidade_operacional.map(PERFIL_OPERACAO)
    veic["grupo"] = [grupo_do_veiculo(c, o, k) for c, o, k in zip(veic.classe_peso, veic.operacao, veic.categoria_id)]

    desp = pd.read_csv(SINTETICO / "despesas.csv")
    abast = pd.read_csv(SINTETICO / "abastecimentos.csv").merge(desp[["despesa_id", "veiculo_id"]], on="despesa_id")
    abast = abast[abast.litros > 0]
    abast["competencia"] = abast.data_hora.str[:7]
    litros = abast.groupby(["veiculo_id", "competencia"]).litros.sum().rename("litros")

    manut = pd.read_csv(SINTETICO / "manutencoes.csv").merge(
        desp[["despesa_id", "veiculo_id", "competencia_inicio"]], on="despesa_id")
    critico = manut[(manut.tipo == "corretiva") & manut.sistema.isin(["motor", "arrefecimento"])]
    meses_criticos = set(zip(critico.veiculo_id, critico.competencia_inicio))

    uso = pd.read_csv(SINTETICO / "uso_veiculo_mensal.csv")
    uso = uso[(uso.status_valor == "OBSERVADO") & (uso.km_rodados > 0)]
    base = uso.merge(litros, left_on=["veiculo_id", "competencia"], right_index=True, how="left").merge(
        veic[["veiculo_id", "grupo", "classe_peso", "operacao", "ano_fabricacao", "capacidade_tanque_l"]],
        on="veiculo_id")
    base["km_l"] = base.km_rodados / base.litros
    base["ref"] = base.groupby(["grupo", "competencia"]).km_l.transform("median")
    base["desvio"] = (1 - base.km_l / base.ref).clip(lower=0).fillna(0)  # quanto pior que a mediana do grupo

    n = len(base)
    ruido = lambda s: rng.normal(0, s, n)  # noqa: E731
    base["agress"] = np.clip(0.06 + 1.8 * base.desvio + ruido(0.03), 0.01, 0.6)
    base["lenta"] = np.clip(np.where(base.operacao == "urbana", 0.14, 0.07) + 0.9 * base.desvio + ruido(0.03),
                            0.02, 0.45)
    base["excesso"] = np.clip(0.02 + 0.6 * base.desvio + ruido(0.02), 0.0, 0.3)
    idade = 2026 - base.ano_fabricacao
    critico_mes = [(v, c) in meses_criticos for v, c in zip(base.veiculo_id, base.competencia)]
    base["aquec"] = np.clip(np.where(critico_mes, 0.7, 0.03 + 0.008 * idade.clip(lower=0)), 0, 0.9)
    base["comb_ini"] = rng.uniform(18, 96, n).round(1)
    base["semente"] = rng.integers(1, 2**31 - 1, n)

    linhas = []
    for r in base.sort_values(["veiculo_id", "competencia"]).itertuples():
        linhas.append(f'  {{"{r.veiculo_id}", "{r.competencia}", {CLASSE[r.classe_peso]}, {OPERACAO[r.operacao]}, '
                      f'{float(r.capacidade_tanque_l):.1f}f, {r.ref:.3f}f, {r.agress:.3f}f, {r.lenta:.3f}f, {r.excesso:.3f}f, '
                      f'{r.aquec:.3f}f, {r.comb_ini:.1f}f, {r.semente}u}},')
    cab = ("// Gerado por src/simulacao/gerar_perfis_telemetria.py. Não editar à mão.\n"
           "// Um perfil por veículo-mês: classe, operação, tanque (L), km/L de referência do grupo, probabilidades de\n"
           "// rotação alta, marcha lenta, excesso de velocidade e superaquecimento, nível inicial de combustível, semente.\n"
           "#pragma once\n#include \"perfil.h\"\n\n"
           f"const int TOTAL_PERFIS = {len(linhas)};\nconst Perfil PERFIS[TOTAL_PERFIS] = {{\n")
    SAIDA.write_text(cab + "\n".join(linhas) + "\n};\n", encoding="utf-8")
    print(f"ok: {len(linhas)} perfis em {SAIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
