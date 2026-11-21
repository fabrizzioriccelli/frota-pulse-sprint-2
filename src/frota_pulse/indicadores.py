"""Etapa 5 — Indicadores de custo e eficiência, por veículo (no período) e por veículo-mês.

Fórmulas (todas documentadas em docs/metodologia.md):
  custo por km (R$/km)        = custo total dos meses com km conhecido / km desses meses
  consumo médio (km/L)        = km dos meses com km e litros conhecidos / litros desses meses
  preço médio (R$/L)          = custo de combustível / litros
  participação da categoria   = custo da categoria / custo total x 100
  custo por km da categoria   = custo da categoria nos meses com km / km desses meses
O numerador e o denominador usam sempre os mesmos meses: um mês sem km não entra no R$/km, senão o custo desse mês
seria dividido pela quilometragem de outros meses.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import CATEGORIAS

COLS_CUSTO = [f"custo_{c.lower()}" for c in CATEGORIAS]


def dividir(a, b):
    """Divisão que devolve NaN quando o denominador é zero ou ausente (nunca infinito)."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = a / b
    return np.where((b > 0) & np.isfinite(r), r, np.nan)


def por_veiculo_mes(base: pd.DataFrame) -> pd.DataFrame:
    m = base.copy()
    m["custo_km"] = dividir(m.custo_total, m.km)
    m["km_l"] = dividir(m.km, m.litros)
    m["preco_medio_l"] = dividir(m.custo_combustivel, m.litros)
    return m


def por_veiculo(base: pd.DataFrame) -> pd.DataFrame:
    """Indicadores do período inteiro de cada veículo."""
    com_km = base[base.km > 0]
    com_km_litros = com_km[com_km.litros > 0]
    g_todos = base.groupby("veiculo_id")
    g_km = com_km.groupby("veiculo_id")
    atributos = g_todos[["empresa_id", "frota_id", "categoria_id", "classe_peso", "perfil_operacao", "propriedade",
                         "grupo", "nome_grupo", "ano_fabricacao"]].first()
    v = atributos.assign(
        meses_na_janela=g_todos.size(),
        meses_com_km=g_km.size(),
        km_total=g_km.km.sum(),
        custo_total=g_todos.custo_total.sum(),
        **{c: g_todos[c].sum() for c in COLS_CUSTO},
        custo_meses_com_km=g_km.custo_total.sum(),
        litros_total=g_todos.litros.sum(min_count=1),
        km_com_litros=com_km_litros.groupby("veiculo_id").km.sum(),
        litros_com_km=com_km_litros.groupby("veiculo_id").litros.sum(),
        custo_locacao=g_todos.custo_locacao.sum(),
    )
    v["meses_com_km"] = v.meses_com_km.fillna(0).astype(int)
    v["custo_km"] = dividir(v.custo_meses_com_km, v.km_total)
    v["km_l"] = dividir(v.km_com_litros, v.litros_com_km)
    v["preco_medio_l"] = dividir(v.custo_combustivel, v.litros_total)
    for c in CATEGORIAS:
        col = f"custo_{c.lower()}"
        v[f"part_{c.lower()}_pct"] = np.round(dividir(v[col], v.custo_total) * 100, 2)
        v[f"{c.lower()}_km"] = dividir(g_km[col].sum().reindex(v.index), v.km_total)
    # Veículo locado: a mensalidade embute manutenção, seguro, impostos e depreciação. Comparar o custo total com o
    # de veículos próprios seria injusto (para os dois lados); ele é comparado só em consumo e custos variáveis.
    v["comparavel_custo_total"] = v.custo_locacao.eq(0)
    v["idade_anos"] = 2026 - v.ano_fabricacao
    return v.reset_index()


def por_categoria(veiculos: pd.DataFrame) -> pd.DataFrame:
    """Custo total por categoria e participação, por grupo."""
    linhas = []
    for grupo, g in veiculos.groupby("nome_grupo"):
        total = g.custo_total.sum()
        for c in CATEGORIAS:
            valor = g[f"custo_{c.lower()}"].sum()
            linhas.append({"grupo": grupo, "categoria": c, "custo_brl": round(valor, 2),
                           "participacao_pct": round(100 * valor / total, 2) if total else np.nan})
    return pd.DataFrame(linhas)
