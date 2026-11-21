"""Fixtures compartilhadas: o pipeline é executado uma vez, em memória, sobre a base de demonstração."""
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from frota_pulse import benchmark, diagnostico, indicadores, ingestao, integracao, modelo  # noqa: E402
from frota_pulse import normalizacao, qualidade  # noqa: E402


@pytest.fixture(scope="session")
def pipeline():
    lotes = ingestao.ingerir()
    tabelas = normalizacao.normalizar(lotes)
    tratadas, ocorrencias = qualidade.verificar(lotes, tabelas)
    integ = integracao.integrar(tratadas)
    v = indicadores.por_veiculo(integ["base_mensal"])
    est = benchmark.estatisticas(v)
    diag = diagnostico.classificar(benchmark.gaps(v, est))
    mensal = diagnostico.classificar_mensal(
        benchmark.gaps_mensais(indicadores.por_veiculo_mes(integ["base_mensal"]), v))
    res = modelo.treinar(mensal, "consumo")
    return {"lotes": lotes, "tabelas": tabelas, "tratadas": tratadas, "ocorrencias": ocorrencias, "integ": integ,
            "veiculos": v, "estatisticas": est, "diagnostico": diag, "mensal": mensal, "modelo": res}


@pytest.fixture(scope="session")
def gabarito_s1():
    d = RAIZ / "data" / "sintetico"
    return pd.read_csv(d / "gabarito_registros.csv")
