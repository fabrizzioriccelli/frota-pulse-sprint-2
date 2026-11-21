"""Etapa 8 — Classificação supervisionada: prever, só com a telemetria, se o consumo do veículo no mês ficará acima
da referência do grupo.

Finalidade no diagnóstico: o consumo real (km/L) só é conhecido quando o extrato do cartão-combustível fecha o mês.
A telemetria do ESP32 chega no mesmo dia. Um modelo que reconheça, nos sinais de condução, o padrão dos meses de
consumo ruim serve de alerta antecipado e ajuda a separar duas causas que as regras não distinguem sozinhas:
ineficiência de CONDUÇÃO (visível na telemetria) e ineficiência de CUSTO (manutenção, pedágio, preço, baixa
utilização), que a telemetria não enxerga. O modelo não substitui as regras: quando o custo chega, elas decidem.

Por que este alvo: o primeiro experimento usou como rótulo a própria regra mensal (pior gap de custo por km ou de
consumo > 15%). O resultado ficou praticamente igual ao de sempre prever a classe majoritária, porque o custo mensal
oscila com faturas de manutenção e pedágio que nenhum sinal de condução antecipa (correlação 0,03 entre os atributos
de telemetria e o gap de custo, contra 0,4 a 0,5 com o gap de consumo). Os dois experimentos são reportados.

Desenho (detalhes e limitações em docs/machine-learning.md):
  unidade      veículo-mês com telemetria, km, litros e referência de grupo válida
  rótulo       1 = consumo do mês mais de 5% pior que a mediana do grupo no mesmo mês (limite de "Atenção");
               0 = dentro da variação típica ou melhor
  atributos    só telemetria do ESP32 e idade do veículo (nunca custo, litros, km/L ou preço, que formam o rótulo)
  separação    por VEÍCULO, estratificada por grupo: todos os meses de um veículo ficam no treino ou no teste;
               separar por linha deixaria meses do mesmo veículo dos dois lados e inflaria o acerto
  modelo       árvore de decisão de profundidade 3, escolhida pela interpretabilidade; regressão logística e
               floresta aleatória são avaliadas no mesmo teste, só para comparação
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text

from .config import FRACAO_TESTE, LIMITE_ATENCAO, LIMITE_INEFICIENTE, NOME_CATEGORIA, SEMENTE

ATRIBUTOS_TELEMETRIA = ["pct_rpm_acima_verde", "pct_marcha_lenta", "pct_excesso_velocidade", "velocidade_media_kmh",
                        "alertas_temperatura", "temperatura_max_c"]
ATRIBUTOS_CADASTRO = ["idade_anos"]
ALVOS = {
    "consumo": "consumo do mês mais de 5% pior que a mediana do grupo (alvo adotado)",
    "regras_custo_total": "regra mensal completa: pior gap de custo por km ou de consumo acima de 15%",
}
PROIBIDOS = ["custo", "litros", "km_l", "preco", "gap", "nivel", "pior"]  # nunca entram como atributo


def preparar(mensal: pd.DataFrame, alvo: str = "consumo") -> tuple[pd.DataFrame, list[str]]:
    d = mensal[mensal.leituras.notna()].copy()
    if alvo == "consumo":
        d = d[d.gap_km_l_pct.notna()]
        d["rotulo"] = (d.gap_km_l_pct > LIMITE_ATENCAO).astype(int)
    else:
        d = d[d.pior_gap_pct.notna()]
        d["rotulo"] = (d.pior_gap_pct > LIMITE_INEFICIENTE).astype(int)
    grupos = pd.get_dummies(d.grupo, prefix="grupo", dtype=int)
    d = pd.concat([d, grupos], axis=1)
    atributos = ATRIBUTOS_TELEMETRIA + ATRIBUTOS_CADASTRO + list(grupos.columns)
    assert not any(p in a for a in atributos for p in PROIBIDOS if not a.startswith("grupo_")), "vazamento"
    return d.reset_index(drop=True), atributos


def separar_por_veiculo(d: pd.DataFrame) -> tuple[pd.Index, pd.Index]:
    """30% dos veículos de cada grupo vão para teste (pelo menos 1), sorteados com semente fixa."""
    rng = np.random.default_rng(SEMENTE)
    teste = []
    for _, g in d.groupby("grupo"):
        veics = sorted(g.veiculo_id.unique())
        k = max(1, round(FRACAO_TESTE * len(veics)))
        teste += list(rng.choice(veics, k, replace=False))
    eh_teste = d.veiculo_id.isin(teste)
    return d.index[~eh_teste], d.index[eh_teste]


def metricas(y, p) -> dict:
    prec, rec, f1, _ = precision_recall_fscore_support(y, p, labels=[1], zero_division=0)
    return {"acuracia": round(accuracy_score(y, p), 3), "acuracia_balanceada": round(balanced_accuracy_score(y, p), 3),
            "precisao_ineficiente": round(float(prec[0]), 3), "recall_ineficiente": round(float(rec[0]), 3),
            "f1_ineficiente": round(float(f1[0]), 3)}


def treinar(mensal: pd.DataFrame, alvo: str = "consumo") -> dict:
    d, atributos = preparar(mensal, alvo)
    itr, ite = separar_por_veiculo(d)
    X, y = d[atributos], d.rotulo
    modelos = {
        "arvore_decisao": DecisionTreeClassifier(max_depth=3, min_samples_leaf=10, class_weight="balanced",
                                                 random_state=SEMENTE),
        "regressao_logistica": make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced",
                                                                                  max_iter=2000)),
        "floresta_aleatoria": RandomForestClassifier(n_estimators=200, max_depth=5, min_samples_leaf=5,
                                                     class_weight="balanced", random_state=SEMENTE),
    }
    comparacao = {}
    for nome, mdl in modelos.items():
        mdl.fit(X.loc[itr], y.loc[itr])
        comparacao[nome] = {"treino": metricas(y.loc[itr], mdl.predict(X.loc[itr])),
                            "teste": metricas(y.loc[ite], mdl.predict(X.loc[ite]))}
    arvore = modelos["arvore_decisao"]
    d["conjunto"] = np.where(d.index.isin(ite), "teste", "treino")
    d["previsao_ml"] = arvore.predict(X)
    d["prob_ineficiente_ml"] = arvore.predict_proba(X)[:, 1].round(3)
    maioria = int(y.loc[itr].mode()[0])
    importancias = pd.Series(arvore.feature_importances_, index=atributos).sort_values(ascending=False)
    cm = confusion_matrix(y.loc[ite], d.loc[ite, "previsao_ml"], labels=[0, 1])
    return {
        "alvo": alvo, "descricao_alvo": ALVOS[alvo], "dados": d, "atributos": atributos, "modelo": arvore,
        "regras_arvore": export_text(arvore, feature_names=atributos, decimals=1),
        "importancias": importancias[importancias > 0].round(3),
        "comparacao_modelos": comparacao,
        "linha_de_base_teste": round(float((y.loc[ite] == maioria).mean()), 3),
        "matriz_confusao": {"vn": int(cm[0, 0]), "fp": int(cm[0, 1]), "fn": int(cm[1, 0]), "vp": int(cm[1, 1])},
        "tamanhos": {"veiculo_meses": len(d), "treino": len(itr), "teste": len(ite),
                     "veiculos_treino": int(d.loc[itr].veiculo_id.nunique()),
                     "veiculos_teste": int(d.loc[ite].veiculo_id.nunique()),
                     "taxa_ineficiente_treino": round(float(y.loc[itr].mean()), 3),
                     "taxa_ineficiente_teste": round(float(y.loc[ite].mean()), 3)},
    }


def exemplos(res: dict, n: int = 3) -> pd.DataFrame:
    """Previsões corretas e incorretas do conjunto de teste, com os atributos que a árvore usou."""
    d = res["dados"]
    t = d[d.conjunto == "teste"].copy()
    t["resultado"] = np.where(t.rotulo == t.previsao_ml, "correta", "incorreta")
    usados = [a for a in res["importancias"].index]
    cols = ["veiculo_id", "competencia", "nome_grupo", "rotulo", "previsao_ml", "prob_ineficiente_ml", "resultado",
            "gap_custo_km_pct", "gap_km_l_pct", *usados]
    linhas = []
    for (res_, rot), g in t.groupby(["resultado", "rotulo"]):
        linhas.append(g.sort_values("prob_ineficiente_ml", ascending=rot == 0).head(n))
    return pd.concat(linhas)[cols].reset_index(drop=True)


def explicar_divergencia(r) -> str:
    if r.rotulo == 1 and r.previsao_ml == 0:
        return ("Consumo do mês acima da referência sem sinal forte na amostra de telemetria: causa provável fora "
                "da condução (rota, carga, abastecimento registrado em outro mês)")
    if r.rotulo == 0 and r.previsao_ml == 1:
        return ("Telemetria com sinais de condução agressiva, mas o consumo do mês ficou dentro da faixa do grupo "
                "(sinal a acompanhar no mês seguinte)")
    return ""


def comparar_com_regras(res: dict, diagnostico: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compara, nos veículos de teste, o diagnóstico por regras do período com a leitura do modelo.

    Leitura do modelo para o veículo = "Condução ineficiente" se a árvore previu consumo acima da referência em pelo
    menos metade dos meses de teste do veículo; caso contrário, "Condução dentro do padrão".
    """
    d = res["dados"]
    t = d[d.conjunto == "teste"].copy()
    t["explicacao"] = [explicar_divergencia(r) for r in t.itertuples()]
    por_veic = t.groupby("veiculo_id").agg(meses=("rotulo", "size"), meses_consumo_ruim_real=("rotulo", "sum"),
                                           meses_consumo_ruim_previstos=("previsao_ml", "sum"))
    por_veic["leitura_ml"] = np.where(por_veic.meses_consumo_ruim_previstos >= por_veic.meses / 2,
                                      "Condução ineficiente", "Condução dentro do padrão")
    por_veic = por_veic.join(diagnostico.set_index("veiculo_id")[[
        "nome_grupo", "nivel_regras", "indicador_decisivo", "pior_gap_pct", "gap_custo_km_pct", "gap_km_l_pct",
        "categoria_maior_gap", "baixa_utilizacao"]])
    regra_ruim = por_veic.nivel_regras.isin(["Atenção", "Ineficiente"])
    ml_ruim = por_veic.leitura_ml.eq("Condução ineficiente")
    por_veic["concordam"] = regra_ruim == ml_ruim
    por_veic["interpretacao"] = [_interpretar(r) for r in por_veic.itertuples()]
    return por_veic.reset_index(), t


def _interpretar(r) -> str:
    regra_ruim = r.nivel_regras in ("Atenção", "Ineficiente")
    ml_ruim = r.leitura_ml == "Condução ineficiente"
    if regra_ruim and ml_ruim:
        return "Concordam: desvio com componente de condução; investigar hábitos de direção e consumo"
    if not regra_ruim and not ml_ruim:
        return "Concordam: dentro da referência nas duas leituras"
    if regra_ruim and not ml_ruim:
        causa = "baixa utilização (custo fixo em poucos km)" if r.baixa_utilizacao else (
            f"custo de {NOME_CATEGORIA[r.categoria_maior_gap].lower()}" if isinstance(r.categoria_maior_gap, str)
            else "custo")
        return f"Divergem: as regras apontam desvio, mas a telemetria não mostra condução ruim; causa provável: {causa}"
    return ("Divergem: a telemetria sugere condução ruim, mas custo e consumo do período ficaram dentro da faixa; "
            "acompanhar")
