"""Etapa 7 — Diagnóstico por regras de negócio, a partir dos gaps em relação ao benchmark do grupo.

Regra (vale para o veículo no período e para o veículo-mês):
  pior gap = maior gap desfavorável entre custo por km e consumo (km/L); custo por km só conta para veículo próprio
  Eficiente     pior gap <= 5%           dentro da variação típica entre veículos semelhantes, ou melhor que ela
  Atenção       5% < pior gap <= 15%     desvio moderado: acompanhar e investigar a categoria que mais pesa
  Ineficiente   pior gap > 15%           desvio significativo e desfavorável
  Sem referência                          grupo com menos de 5 veículos comparáveis ou veículo sem km no período
Os limites vêm da distribuição observada dos gaps (docs/metodologia.md): a mediana do gap absoluto entre
veículos de um mesmo grupo fica perto de 5%, e 15% fica acima do percentil 90.

O diagnóstico nunca usa o custo total em reais: um veículo que roda mais custa mais e pode ser eficiente. A causa
provável é apontada pela categoria com maior gap em R$/km, e um veículo com quilometragem muito abaixo do grupo
recebe a observação de baixa utilização (o custo fixo se dilui em poucos km).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import CATEGORIAS, KM_MINIMO_FRACAO, LIMITE_ATENCAO, LIMITE_INEFICIENTE, NOME_CATEGORIA

NIVEIS = ["Eficiente", "Atenção", "Ineficiente"]


def nivel(pior_gap: pd.Series) -> pd.Series:
    n = pd.Series("Sem referência", index=pior_gap.index, dtype=object)
    n[pior_gap <= LIMITE_ATENCAO] = "Eficiente"
    n[(pior_gap > LIMITE_ATENCAO) & (pior_gap <= LIMITE_INEFICIENTE)] = "Atenção"
    n[pior_gap > LIMITE_INEFICIENTE] = "Ineficiente"
    return n


def classificar(v: pd.DataFrame) -> pd.DataFrame:
    d = v.copy()
    d["pior_gap_pct"] = d[["gap_custo_km_pct", "gap_km_l_pct"]].max(axis=1, skipna=True)
    d["indicador_decisivo"] = np.where(d.gap_custo_km_pct.fillna(-np.inf) >= d.gap_km_l_pct.fillna(-np.inf),
                                       "custo por km", "consumo (km/L)")
    d.loc[d.pior_gap_pct.isna(), "indicador_decisivo"] = ""
    d["nivel_regras"] = nivel(d.pior_gap_pct)
    mediana_km = d.groupby("grupo").km_total.transform("median")
    d["baixa_utilizacao"] = d.km_total < KM_MINIMO_FRACAO * mediana_km
    gaps_cat = d[[f"gap_{c.lower()}_km" for c in CATEGORIAS]]
    tem = gaps_cat.max(axis=1) > 0
    d["categoria_maior_gap"] = None
    d.loc[tem, "categoria_maior_gap"] = (gaps_cat[tem].idxmax(axis=1).str.replace("gap_", "")
                                         .str.replace("_km", "").str.upper())
    d["justificativa"] = [_justificar(r) for r in d.itertuples()]
    return d


def _pct(v: float, sinal: bool = True) -> str:
    return (f"{v:+.1f}" if sinal else f"{v:.1f}").replace(".", ",") + "%"


def _justificar(r) -> str:
    if r.nivel_regras == "Sem referência":
        if r.meses_com_km == 0:
            return "Sem quilometragem no período: indicadores por km não podem ser calculados"
        return "Grupo com menos de 5 veículos comparáveis: a mediana não é uma referência estável"
    partes = []
    if pd.notna(r.gap_custo_km_pct):
        partes.append(f"custo por km {_pct(r.gap_custo_km_pct)} em relação à mediana do grupo")
    else:
        partes.append("custo total não comparável (veículo locado)")
    if pd.notna(r.gap_km_l_pct):
        partes.append(f"consumo {_pct(r.gap_km_l_pct, False)} pior que a mediana" if r.gap_km_l_pct > 0
                      else f"consumo {_pct(-r.gap_km_l_pct, False)} melhor que a mediana")
    if r.nivel_regras != "Eficiente" and isinstance(r.categoria_maior_gap, str):
        partes.append(f"categoria com maior gap: {NOME_CATEGORIA[r.categoria_maior_gap].lower()}")
    if r.baixa_utilizacao:
        partes.append("baixa utilização: km abaixo de 25% da mediana do grupo, o custo fixo pesa em poucos km")
    return "; ".join(partes)


def classificar_mensal(m: pd.DataFrame) -> pd.DataFrame:
    """Mesma regra aplicada a cada veículo-mês (base para o rótulo do modelo supervisionado)."""
    m = m.copy()
    m["pior_gap_pct"] = m[["gap_custo_km_pct", "gap_km_l_pct"]].max(axis=1, skipna=True)
    m["nivel_regras"] = nivel(m.pior_gap_pct)
    return m


def resumo(d: pd.DataFrame) -> pd.DataFrame:
    return (d.pivot_table(index="nome_grupo", columns="nivel_regras", values="veiculo_id", aggfunc="count",
                          fill_value=0).reindex(columns=NIVEIS + ["Sem referência"], fill_value=0))
