"""Etapa 4 — Integração: junta cadastro, custos, quilometragem e telemetria em uma base por veículo-mês.

Chave comum: veiculo_id + competencia (AAAA-MM). Regras:
  * entram só custos com tratamento OK, ALERTA, IMPUTADO ou CORRIGIDO; QUARENTENA e EXCLUIDO ficam de fora;
  * custo pago por terceiro (pedágio de viagem com Vale-Pedágio do embarcador) não é custo da frota;
  * custo com competência de vários meses (IPVA, seguro anual) é dividido igualmente entre os meses (rateio);
  * custo sem veículo (apólice coletiva, rastreamento da frota) é dividido entre os veículos da frota no mês;
  * só entram os meses da janela de análise de cada empresa (config.JANELAS).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import CATEGORIAS, JANELAS, LIMITES_TELEMETRIA

VALIDOS = ["OK", "ALERTA", "IMPUTADO", "CORRIGIDO"]


def meses(inicio: str, fim: str) -> list[str]:
    return [p.strftime("%Y-%m") for p in pd.period_range(inicio, fim, freq="M")]


def grade(veiculos: pd.DataFrame) -> pd.DataFrame:
    """Todas as combinações veículo x mês dentro da janela da empresa."""
    linhas = [(v.veiculo_id, m) for v in veiculos.itertuples() for m in meses(*JANELAS[v.empresa_id])]
    return pd.DataFrame(linhas, columns=["veiculo_id", "competencia"])


def ratear(custos: pd.DataFrame, veiculos: pd.DataFrame) -> pd.DataFrame:
    """Expande cada custo para os meses de competência e distribui custos de frota entre os veículos."""
    c = custos[custos.status_qualidade.isin(VALIDOS) & custos.natureza.eq("proprio")].copy()
    frota_de = veiculos.set_index("veiculo_id").frota_id
    frota_por_codigo = veiculos.groupby("frota_id").veiculo_id.apply(list)
    linhas = []
    for r in c.itertuples():
        ms = meses(r.competencia_inicio, r.competencia_fim)
        if isinstance(r.veiculo_id, str):
            alvos = [r.veiculo_id]
        else:
            alvos = frota_por_codigo.get(r.centro_custo, [])
        if not alvos:
            continue
        parcela = r.valor_brl / (len(ms) * len(alvos))
        litros = (r.litros / len(ms)) if r.categoria == "COMBUSTIVEL" and pd.notna(r.litros) else np.nan
        for m in ms:
            for v in alvos:
                linhas.append((v, m, r.categoria, r.subcategoria, parcela, litros, r.registro_id))
    rateado = pd.DataFrame(linhas, columns=["veiculo_id", "competencia", "categoria", "subcategoria", "valor_brl",
                                            "litros", "registro_id"])
    rateado["frota_id"] = rateado.veiculo_id.map(frota_de)
    return rateado


def telemetria_mensal(t: pd.DataFrame, veiculos: pd.DataFrame) -> pd.DataFrame:
    """Resume as leituras do ESP32 por veículo-mês (atributos usados no modelo e no diagnóstico)."""
    t = t[t.status_qualidade != "QUARENTENA"].copy()
    classe = t.veiculo_id.map(veiculos.set_index("veiculo_id").classe_peso)
    verde = classe.map(lambda c: LIMITES_TELEMETRIA[c]["rpm_max_verde"])
    mov = t.velocidade_kmh > 0
    t["parado"] = ~mov
    t["rpm_acima_verde"] = np.where(mov & t.rpm.notna(), (t.rpm > verde).astype(float), np.nan)
    for a in ("TEMP_ALTA", "RPM_ALTO", "VEL_EXCESSO", "COMB_BAIXO"):
        t[a] = t.alertas.str.contains(a, na=False)
    t["critico"] = t.status.eq("CRITICO")
    g = t.groupby(["veiculo_id", "competencia"])
    return pd.DataFrame({
        "leituras": g.size(),
        "velocidade_media_kmh": g.velocidade_kmh.mean().round(1),
        "pct_marcha_lenta": (g.parado.mean() * 100).round(1),
        "pct_rpm_acima_verde": (g.rpm_acima_verde.mean() * 100).round(1),
        "pct_excesso_velocidade": (g.VEL_EXCESSO.mean() * 100).round(1),
        "alertas_temperatura": g.TEMP_ALTA.sum().astype(int),
        "alertas_rpm": g.RPM_ALTO.sum().astype(int),
        "alertas_combustivel": g.COMB_BAIXO.sum().astype(int),
        "temperatura_max_c": g.temperatura_c.max().round(1),
        "leituras_criticas": g.critico.sum().astype(int),
    }).reset_index()


def integrar(tratadas: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    veiculos = tratadas["veiculos"]
    veiculos = veiculos[veiculos.status_qualidade != "EXCLUIDO"].reset_index(drop=True)
    rateado = ratear(tratadas["custos"], veiculos)
    base = grade(veiculos)
    janela = set(zip(base.veiculo_id, base.competencia))
    rateado = rateado[[k in janela for k in zip(rateado.veiculo_id, rateado.competencia)]]

    por_cat = rateado.pivot_table(index=["veiculo_id", "competencia"], columns="categoria", values="valor_brl",
                                  aggfunc="sum", fill_value=0.0)
    por_cat = por_cat.reindex(columns=CATEGORIAS, fill_value=0.0)
    por_cat.columns = [f"custo_{c.lower()}" for c in por_cat.columns]
    litros = rateado[rateado.categoria == "COMBUSTIVEL"].groupby(["veiculo_id", "competencia"]).litros.sum(min_count=1)
    locacao = rateado[rateado.subcategoria.str.contains("locacao", na=False)].groupby(
        ["veiculo_id", "competencia"]).valor_brl.sum()

    km = tratadas["km"].groupby(["veiculo_id", "competencia"]).km.sum(min_count=1)
    base = (base.merge(veiculos[["veiculo_id", "empresa_id", "frota_id", "categoria_id", "classe_peso", "perfil_operacao",
                                 "ano_fabricacao", "propriedade", "grupo", "nome_grupo"]], on="veiculo_id")
            .join(por_cat, on=["veiculo_id", "competencia"])
            .join(litros.rename("litros"), on=["veiculo_id", "competencia"])
            .join(locacao.rename("custo_locacao"), on=["veiculo_id", "competencia"])
            .join(km.rename("km"), on=["veiculo_id", "competencia"]))
    cols_custo = [f"custo_{c.lower()}" for c in CATEGORIAS]
    base[cols_custo] = base[cols_custo].fillna(0.0)
    base["custo_locacao"] = base.custo_locacao.fillna(0.0)
    base["custo_total"] = base[cols_custo].sum(axis=1)
    tel = telemetria_mensal(tratadas["telemetria"], veiculos)
    base = base.merge(tel, on=["veiculo_id", "competencia"], how="left")
    base["idade_anos"] = pd.to_datetime(base.competencia).dt.year - base.ano_fabricacao
    return {"base_mensal": base, "custos_rateados": rateado, "veiculos": veiculos, "telemetria_mensal": tel}
