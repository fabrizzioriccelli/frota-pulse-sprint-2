import numpy as np
import pandas as pd

from frota_pulse import normalizacao as N


def test_le_os_tres_formatos(pipeline):
    formatos = {lt.formato for lt in pipeline["lotes"]}
    assert formatos == {"csv", "txt", "json"}
    assert len(pipeline["lotes"]) == 12
    assert all(lt.registros > 0 for lt in pipeline["lotes"])


def test_cada_registro_guarda_arquivo_e_linha(pipeline):
    for lt in pipeline["lotes"]:
        assert lt.dados["_arquivo"].eq(lt.arquivo).all()
        assert lt.dados["_linha"].notna().all()


def test_linha_truncada_do_txt_e_rejeitada_e_registrada(pipeline):
    rejeitadas = [r for lt in pipeline["lotes"] for r in lt.rejeitadas]
    assert len(rejeitadas) == 1 and rejeitadas[0]["conteudo"].startswith("DSP-C-007372")


def test_json_aninhado_vira_uma_linha_por_item_e_soma_por_ordem(pipeline):
    lote = next(lt for lt in pipeline["lotes"] if lt.fonte == "manutencao")
    assert lote.registros == 2 * lote.dados.numero_os.nunique()
    custos = pipeline["tabelas"]["custos"]
    man = custos[custos.fonte == "manutencao"]
    assert len(man) == lote.dados.numero_os.nunique()


def test_numeros_em_formatos_diferentes():
    assert N.numero("R$ 1.234,56") == 1234.56
    assert N.numero("1234.56") == 1234.56
    assert N.numero("-2685,45") == -2685.45
    assert np.isnan(N.numero("")) and np.isnan(N.numero(None))


def test_datas_sao_estritas():
    s = N.datas(pd.Series(["02/07/2025 06:53", "31/02/2026 10:15", "2026-14-03 17:20"]), ["%d/%m/%Y %H:%M"])
    assert s.iloc[0] == pd.Timestamp("2025-07-02 06:53") and s.iloc[1:].isna().all()


def test_competencia():
    assert N.competencia_de("03/2026") == "2026-03"
    assert N.competencia_de("2026-03") == "2026-03"
    assert N.competencia_de("13/2025") is None


def test_categorias_por_texto_livre():
    assert N.categoria_por_texto("IPVA 2025 parcela 1/3") == "IMPOSTOS"
    assert N.categoria_por_texto("Seguro frota - parcela") == "OUTROS"
    assert N.categoria_por_texto("Reembolso de pedágio pago em dinheiro") == "PEDAGIO"
    assert N.categoria_por_texto("Lavagem") == "OUTROS"


def test_todas_as_categorias_sao_as_seis_do_projeto(pipeline):
    assert set(pipeline["tabelas"]["custos"].categoria) <= {"COMBUSTIVEL", "MANUTENCAO", "PEDAGIO", "MULTAS",
                                                            "IMPOSTOS", "OUTROS"}


def test_distancia_em_metros_vira_km(pipeline):
    lote = next(lt for lt in pipeline["lotes"] if lt.fonte == "quilometragem")
    bruto = lote.dados.iloc[0]
    km = pipeline["tabelas"]["km"].iloc[0]
    assert km.km == bruto.distancia_m / 1000
