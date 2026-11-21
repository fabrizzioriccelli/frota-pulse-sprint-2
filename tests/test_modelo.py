from frota_pulse import modelo


def test_treino_e_teste_nao_compartilham_veiculos(pipeline):
    d = pipeline["modelo"]["dados"]
    treino = set(d[d.conjunto == "treino"].veiculo_id)
    teste = set(d[d.conjunto == "teste"].veiculo_id)
    assert treino and teste and not treino & teste


def test_atributos_nao_revelam_o_rotulo(pipeline):
    for a in pipeline["modelo"]["atributos"]:
        assert not any(p in a for p in modelo.PROIBIDOS) or a.startswith("grupo_"), a


def test_modelo_supera_a_linha_de_base(pipeline):
    res = pipeline["modelo"]
    assert res["comparacao_modelos"]["arvore_decisao"]["teste"]["acuracia"] > res["linha_de_base_teste"]


def test_resultado_reprodutivel(pipeline):
    res2 = modelo.treinar(pipeline["mensal"], "consumo")
    assert (res2["dados"].previsao_ml == pipeline["modelo"]["dados"].previsao_ml).all()


def test_exemplos_tem_acertos_e_erros(pipeline):
    ex = modelo.exemplos(pipeline["modelo"])
    assert set(ex.resultado) == {"correta", "incorreta"}
