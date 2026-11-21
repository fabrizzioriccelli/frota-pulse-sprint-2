import pandas as pd

from frota_pulse.config import RAIZ


def _ocorrencias_do_registro(oc, registro):
    return oc[oc.registro == registro]


def test_nenhum_registro_e_apagado(pipeline):
    assert len(pipeline["tratadas"]["custos"]) == len(pipeline["tabelas"]["custos"])
    assert len(pipeline["tratadas"]["km"]) == len(pipeline["tabelas"]["km"])


def test_todas_as_inconsistencias_da_sprint2_sao_encontradas(pipeline):
    g = pd.read_csv(RAIZ / "data" / "raw" / "gabarito_inconsistencias_sprint2.csv")
    oc = pipeline["ocorrencias"]
    for r in g.itertuples():
        if r.registro == "(arquivo inteiro)":
            achadas = oc[oc.arquivo.str.endswith(r.arquivo) & oc.regra.eq("Q01")]
            assert len(achadas) > 0, r
            continue
        achadas = _ocorrencias_do_registro(oc, r.registro)
        assert r.tipo in set(achadas.tipo), (r.tipo, r.registro, set(achadas.tipo))


def test_problemas_da_sprint1_sao_encontrados(pipeline, gabarito_s1):
    oc = pipeline["ocorrencias"]
    esperado = {"G01": "Q01", "G11": "Q02", "G14": "Q08", "G15": "Q12", "G16": "Q05", "G17": "Q07", "G18": "Q04",
                "G19": "Q11", "G20": "Q06", "G10": "Q09", "G02": "Q13"}
    for cen, regra in esperado.items():
        ids = set(gabarito_s1[gabarito_s1.cenario_id == cen].registro_id)
        if cen == "G11":  # as NF-e trazem a chave da nota como identificador
            assert (oc.regra == "Q02").sum() == len(ids)
            continue
        if cen == "G01":  # o reenvio é detectado pelo conteúdo, no arquivo reenviado
            achados = oc[(oc.regra == "Q01") & oc.arquivo.str.contains("reenvio")]
            assert len(achados) == len(ids)
            continue
        achados = set(oc[oc.regra == regra].registro)
        assert ids <= achados, (cen, ids - achados)


def test_estornos_legitimos_nao_sao_marcados(pipeline, gabarito_s1):
    ids = set(gabarito_s1[gabarito_s1.cenario_id == "G33"].registro_id)
    assert not ids & set(pipeline["ocorrencias"].registro)


def test_quarentena_fica_fora_da_base(pipeline):
    c = pipeline["tratadas"]["custos"]
    validos = set(c[~c.status_qualidade.isin(["QUARENTENA", "EXCLUIDO"])].registro_id)
    fora = set(c[c.status_qualidade.isin(["QUARENTENA", "EXCLUIDO"])].registro_id) - validos
    usados = set(pipeline["integ"]["custos_rateados"].registro_id)
    assert not fora & usados


def test_correcao_guarda_o_valor_original(pipeline):
    c = pipeline["tratadas"]["custos"]
    corr = c[c.motivos.str.contains("Q07")]
    assert (corr.preco_litro != corr.preco_litro_original).all()


def test_relatorio_tem_os_campos_pedidos(pipeline):
    oc = pipeline["ocorrencias"]
    for col in ("tipo", "arquivo", "registro", "tratamento", "justificativa"):
        assert oc[col].astype(str).str.len().gt(0).all(), col
