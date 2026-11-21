import numpy as np
import pandas as pd
import pytest

from frota_pulse import benchmark, diagnostico
from frota_pulse.indicadores import dividir


def test_divisao_por_zero_vira_nan():
    assert np.isnan(dividir(10, 0)) and np.isnan(dividir(10, np.nan)) and dividir(10, 4) == 2.5


def test_custo_por_km_e_consumo_conferidos_a_mao(pipeline):
    base = pipeline["integ"]["base_mensal"]
    v = pipeline["veiculos"].set_index("veiculo_id")
    m = base[(base.veiculo_id == "B-V23") & (base.km > 0)]
    assert v.loc["B-V23", "custo_km"] == pytest.approx(m.custo_total.sum() / m.km.sum())
    ml = m[m.litros > 0]
    assert v.loc["B-V23", "km_l"] == pytest.approx(ml.km.sum() / ml.litros.sum())


def test_participacoes_somam_100(pipeline):
    v = pipeline["veiculos"]
    soma = v[[c for c in v.columns if c.startswith("part_")]].sum(axis=1)
    assert np.allclose(soma[v.custo_total > 0], 100, atol=0.05)


def test_ipva_anual_e_rateado_em_12_meses(pipeline):
    c = pipeline["tratadas"]["custos"]
    r = c[(c.subcategoria == "ipva") & (c.status_qualidade == "OK")].iloc[0]
    rat = pipeline["integ"]["custos_rateados"]
    parcelas = rat[rat.registro_id == r.registro_id]
    assert parcelas.valor_brl.round(6).nunique() == 1
    assert parcelas.valor_brl.iloc[0] == pytest.approx(r.valor_brl / 12)


def _df(valores, ind):
    return pd.DataFrame({"veiculo_id": [f"V{i}" for i in range(len(valores))], "grupo": "G", "nome_grupo": "G",
                         ind: valores, "meses_com_km": 12, "comparavel_custo_total": True})


def test_direcao_do_gap_custo_menor_e_melhor():
    v = _df([1.0, 1.0, 1.0, 1.0, 1.2], "custo_km")
    for c in benchmark.INDICADORES:
        if c not in v:
            v[c] = np.nan
    g = benchmark.gaps(v, benchmark.estatisticas(v))
    assert g.gap_custo_km_pct.iloc[-1] == pytest.approx(20.0)  # 20% mais caro = gap +20%


def test_direcao_do_gap_consumo_maior_e_melhor():
    v = _df([10.0, 10.0, 10.0, 10.0, 8.0], "km_l")
    for c in benchmark.INDICADORES:
        if c not in v:
            v[c] = np.nan
    g = benchmark.gaps(v, benchmark.estatisticas(v))
    assert g.gap_km_l_pct.iloc[-1] == pytest.approx(20.0)  # rende 20% menos = gap +20% (pior)
    assert g.gap_km_l.iloc[-1] == pytest.approx(2.0)


def test_grupo_pequeno_nao_tem_referencia(pipeline):
    d = pipeline["diagnostico"]
    assert set(d[d.grupo.str.startswith("LEVE_URBANA")].nivel_regras) == {"Sem referência"}


def test_limites_das_regras():
    n = diagnostico.nivel(pd.Series([-3, 5.0, 5.01, 15.0, 15.01, np.nan]))
    assert list(n) == ["Eficiente", "Eficiente", "Atenção", "Atenção", "Ineficiente", "Sem referência"]


def test_custo_total_alto_nao_basta_para_ser_ineficiente(pipeline):
    d = pipeline["diagnostico"]
    maior = d.sort_values("custo_total").iloc[-1]
    assert maior.nivel_regras != "Ineficiente"


def test_baixa_utilizacao_e_explicada(pipeline):
    d = pipeline["diagnostico"].set_index("veiculo_id")
    for v in ("B-V28", "B-V29", "B-V30"):
        assert d.loc[v, "baixa_utilizacao"] and "baixa utilização" in d.loc[v, "justificativa"]
