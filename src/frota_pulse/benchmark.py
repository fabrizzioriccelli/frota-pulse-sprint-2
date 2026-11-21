"""Etapa 6 — Benchmark e gap de eficiência.

Referência (benchmark) de cada indicador = MEDIANA do grupo de comparação. A mediana foi escolhida, e não a média,
porque um único veículo muito fora do padrão desloca a média e contaminaria a referência dos demais.

Direção do gap — "gap desfavorável" é sempre positivo quando o veículo está pior que a referência:
  indicador em que MENOR é melhor (R$/km, R$/L, R$/km por categoria):
      gap absoluto = veículo - referência            gap % = (veículo - referência) / referência x 100
  indicador em que MAIOR é melhor (km/L):
      gap absoluto = referência - veículo            gap % = (referência - veículo) / referência x 100
Assim, nos dois casos, +12% significa "12% pior que a mediana do grupo" e -8% significa "8% melhor".
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import CATEGORIAS, MIN_VEICULOS_GRUPO

# indicador -> True se maior é melhor
INDICADORES = {"custo_km": False, "km_l": True, "preco_medio_l": False,
               **{f"{c.lower()}_km": False for c in CATEGORIAS}}
NOMES = {"custo_km": "Custo por km (R$/km)", "km_l": "Consumo médio (km/L)", "preco_medio_l": "Preço médio (R$/L)",
         **{f"{c.lower()}_km": f"{c.capitalize()} por km (R$/km)" for c in CATEGORIAS}}


EMBUTIDOS_NA_LOCACAO = {"custo_km", "manutencao_km", "impostos_km", "outros_km"}


def elegivel(v: pd.DataFrame, indicador: str) -> pd.Series:
    """Veículos que entram na referência do indicador."""
    ok = v[indicador].notna() & (v.meses_com_km > 0)
    if indicador in EMBUTIDOS_NA_LOCACAO:
        ok &= v.comparavel_custo_total  # locados fora do custo total e das categorias que a locação embute
    return ok


def estatisticas(v: pd.DataFrame) -> pd.DataFrame:
    """Média, mediana, quartis e amplitude de cada indicador em cada grupo."""
    linhas = []
    for (grupo, nome), g in v.groupby(["grupo", "nome_grupo"]):
        for ind in INDICADORES:
            x = g.loc[elegivel(g, ind), ind]
            linhas.append({"grupo": grupo, "nome_grupo": nome, "indicador": ind, "n": int(x.size),
                           "media": x.mean(), "mediana": x.median(), "q1": x.quantile(0.25), "q3": x.quantile(0.75),
                           "minimo": x.min(), "maximo": x.max(),
                           "referencia_valida": bool(x.size >= MIN_VEICULOS_GRUPO)})
    return pd.DataFrame(linhas)


def gaps(v: pd.DataFrame, est: pd.DataFrame) -> pd.DataFrame:
    """Gap absoluto e percentual de cada veículo em relação à mediana do seu grupo, com a direção correta."""
    v = v.copy()
    ref = est.set_index(["grupo", "indicador"])
    for ind, maior_melhor in INDICADORES.items():
        chave = list(zip(v.grupo, [ind] * len(v)))
        mediana = pd.Series([ref.loc[k, "mediana"] for k in chave], index=v.index)
        valida = pd.Series([ref.loc[k, "referencia_valida"] for k in chave], index=v.index)
        usa = valida & elegivel(v, ind)
        dif = (mediana - v[ind]) if maior_melhor else (v[ind] - mediana)
        v[f"ref_{ind}"] = mediana.where(usa)
        v[f"gap_{ind}"] = dif.where(usa)
        v[f"gap_{ind}_pct"] = (dif / mediana * 100).where(usa)
    return v


def gaps_mensais(m: pd.DataFrame, veiculos: pd.DataFrame) -> pd.DataFrame:
    """Mesmo cálculo por veículo-mês, contra a mediana do grupo no mesmo mês (usado no rótulo do modelo)."""
    m = m.merge(veiculos[["veiculo_id", "comparavel_custo_total"]], on="veiculo_id", how="left")
    validos = veiculos.groupby("grupo").apply(
        lambda g: int((g.comparavel_custo_total & g.custo_km.notna()).sum()), include_groups=False)
    for ind, maior_melhor in (("custo_km", False), ("km_l", True)):
        ok = m[ind].notna() & (m.km > 0)
        if ind == "custo_km":
            ok &= m.comparavel_custo_total
        med = m[ok].groupby(["grupo", "competencia"])[ind].transform("median")
        dif = (med - m.loc[ok, ind]) if maior_melhor else (m.loc[ok, ind] - med)
        m[f"gap_{ind}_pct"] = np.nan
        m.loc[ok, f"gap_{ind}_pct"] = dif / med * 100
        m.loc[m.grupo.map(validos).fillna(0) < MIN_VEICULOS_GRUPO, f"gap_{ind}_pct"] = np.nan
    return m


def ranking(v: pd.DataFrame, indicador: str = "custo_km", n: int = 10) -> pd.DataFrame:
    col = f"gap_{indicador}_pct"
    r = v[v[col].notna()].sort_values(col, ascending=False).head(n)
    return r[["veiculo_id", "nome_grupo", indicador, f"ref_{indicador}", f"gap_{indicador}", col]].reset_index(drop=True)


def ranking_categorias(v: pd.DataFrame) -> pd.DataFrame:
    """Para cada categoria, o veículo com maior gap de R$/km em relação ao grupo."""
    linhas = []
    for c in CATEGORIAS:
        ind = f"{c.lower()}_km"
        col = f"gap_{ind}"
        x = v[v[col].notna()].sort_values(col, ascending=False).head(3)
        for r in x.itertuples():
            linhas.append({"categoria": c, "veiculo_id": r.veiculo_id, "grupo": r.nome_grupo,
                           "valor_r_km": getattr(r, ind), "referencia_r_km": getattr(r, f"ref_{ind}"),
                           "gap_r_km": getattr(r, col), "gap_pct": getattr(r, f"{col}_pct")})
    return pd.DataFrame(linhas)
