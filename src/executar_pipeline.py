#!/usr/bin/env python3
"""Executa o pipeline completo da Sprint 2, das fontes brutas ao diagnóstico, e grava todas as saídas.

Fluxo: arquivos de entrada -> ingestão -> normalização -> qualidade -> integração -> indicadores -> benchmark ->
gap de eficiência -> diagnóstico por regras -> modelo supervisionado -> comparação -> relatórios e gráficos.

Entradas: data/raw/ (CSV, TXT, JSON) e data/telemetria/telemetria_esp32.csv
Saídas:   data/processed/ (bases tratadas), outputs/reports/, outputs/charts/, outputs/predictions/

Uso:
    python src/executar_pipeline.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402

from frota_pulse import benchmark, diagnostico, graficos, indicadores, ingestao, integracao, modelo  # noqa: E402
from frota_pulse import normalizacao, qualidade, relatorios  # noqa: E402
from frota_pulse.config import GRAFICOS, PREVISOES, PROCESSADOS, RAIZ, RELATORIOS  # noqa: E402

LOG: list[str] = []


def etapa(n: int, nome: str, detalhe: str, inicio: float) -> None:
    linha = f"[{n:02d}] {nome:<28} {detalhe}  ({time.perf_counter() - inicio:.2f} s)"
    LOG.append(linha)
    print(linha, flush=True)


def salvar(df: pd.DataFrame, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho, index=False, float_format="%.4f")


def main() -> dict:
    for p in (PROCESSADOS, RELATORIOS, GRAFICOS, PREVISOES):
        p.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    print("Frota Pulse — pipeline da Sprint 2 (dados simulados)\n")

    lotes = ingestao.ingerir()
    res_ing = ingestao.resumo(lotes)
    formatos = res_ing.groupby("formato").arquivo.count().to_dict()
    etapa(1, "Ingestão", f"{len(lotes)} arquivos ({', '.join(f'{v} {k.upper()}' for k, v in formatos.items())}), "
                         f"{relatorios.br(int(res_ing.registros.sum()))} registros lidos", t0)

    tabelas = normalizacao.normalizar(lotes)
    etapa(2, "Normalização", f"{relatorios.br(len(tabelas['custos']))} lançamentos de custo em 6 categorias, "
                             f"{len(tabelas['veiculos'])} linhas de cadastro, {len(tabelas['km'])} meses de km", t0)

    tratadas, ocorrencias = qualidade.verificar(lotes, tabelas)
    resumo_q = qualidade.resumo_por_arquivo(lotes, ocorrencias)
    trat = ocorrencias.tratamento.value_counts()
    etapa(3, "Qualidade", f"{len(ocorrencias)} ocorrências: " + ", ".join(f"{v} {k.lower()}" for k, v in trat.items()), t0)

    integ = integracao.integrar(tratadas)
    base = integ["base_mensal"]
    etapa(4, "Integração", f"{len(base)} veículo-mês, {base.veiculo_id.nunique()} veículos, "
                           f"custo total R$ {relatorios.br(base.custo_total.sum())}", t0)

    v = indicadores.por_veiculo(base)
    por_cat = indicadores.por_categoria(v)
    etapa(5, "Indicadores", f"custo/km, km/L, R$/L e participação de {len(v)} veículos", t0)

    est = benchmark.estatisticas(v)
    validos = est[(est.indicador == "custo_km") & est.referencia_valida]
    g = benchmark.gaps(v, est)
    etapa(6, "Benchmark", f"{len(validos)} grupos com referência válida (n >= 5); mediana como referência", t0)
    etapa(7, "Gap de eficiência", f"{int(g.gap_custo_km_pct.notna().sum())} veículos com gap de custo por km e "
                                  f"{int(g.gap_km_l_pct.notna().sum())} com gap de consumo", t0)

    diag = diagnostico.classificar(g)
    niv = diag.nivel_regras.value_counts()
    etapa(8, "Diagnóstico por regras", ", ".join(f"{k} {v}" for k, v in niv.items()), t0)

    mensal = diagnostico.classificar_mensal(benchmark.gaps_mensais(indicadores.por_veiculo_mes(base), v))
    res = modelo.treinar(mensal, "consumo")
    res1 = modelo.treinar(mensal, "regras_custo_total")
    mt = res["comparacao_modelos"]["arvore_decisao"]["teste"]
    etapa(9, "Modelo (árvore de decisão)", f"teste com {res['tamanhos']['teste']} veículo-mês de "
                                          f"{res['tamanhos']['veiculos_teste']} veículos: acurácia "
                                          f"{relatorios.br(100 * mt['acuracia'], 1)}% (linha de base "
                                          f"{relatorios.br(100 * res['linha_de_base_teste'], 1)}%), recall "
                                          f"{relatorios.br(100 * mt['recall_ineficiente'], 1)}%", t0)
    cmp_, teste = modelo.comparar_com_regras(res, diag)
    etapa(10, "Regras x modelo", f"concordam em {int(cmp_.concordam.sum())} de {len(cmp_)} veículos de teste", t0)

    # ------------------------------------------------------------ gravação
    salvar(tratadas["veiculos"], PROCESSADOS / "cadastro_tratado.csv")
    custos = tratadas["custos"]
    salvar(custos, PROCESSADOS / "custos_tratados.csv")
    salvar(custos[custos.status_qualidade.isin(["QUARENTENA"])], PROCESSADOS / "quarentena.csv")
    salvar(tratadas["km"], PROCESSADOS / "km_mensal_tratado.csv")
    salvar(integ["telemetria_mensal"], PROCESSADOS / "telemetria_mensal.csv")
    salvar(base, PROCESSADOS / "base_consolidada_veiculo_mes.csv")
    (PROCESSADOS / "indicadores_veiculo.json").write_text(
        diag[["veiculo_id", "empresa_id", "nome_grupo", "km_total", "custo_total", "custo_km", "km_l", "preco_medio_l",
              "gap_custo_km_pct", "gap_km_l_pct", "nivel_regras", "justificativa"]].round(4)
        .to_json(orient="records", force_ascii=False, indent=1), encoding="utf-8")

    salvar(res_ing, RELATORIOS / "resumo_ingestao.csv")
    salvar(ocorrencias, RELATORIOS / "relatorio_qualidade.csv")
    (RELATORIOS / "relatorio_qualidade.md").write_text(relatorios.qualidade_md(resumo_q, ocorrencias), encoding="utf-8")
    salvar(diag, RELATORIOS / "indicadores_e_diagnostico_veiculo.csv")
    salvar(por_cat, RELATORIOS / "custos_por_categoria.csv")
    salvar(est, RELATORIOS / "benchmark_grupos.csv")
    salvar(benchmark.ranking(g, "custo_km", 15), RELATORIOS / "ranking_gap_custo_km.csv")
    salvar(benchmark.ranking(g, "km_l", 15), RELATORIOS / "ranking_gap_consumo.csv")
    salvar(benchmark.ranking_categorias(g), RELATORIOS / "ranking_gap_por_categoria.csv")
    salvar(diagnostico.resumo(diag).reset_index(), RELATORIOS / "diagnostico_resumo_grupos.csv")
    salvar(cmp_, RELATORIOS / "comparacao_regras_ml.csv")

    d = res["dados"]
    salvar(d[["veiculo_id", "competencia", "nome_grupo", "conjunto", "rotulo", "previsao_ml", "prob_ineficiente_ml",
              "gap_km_l_pct", "gap_custo_km_pct", "nivel_regras", *res["atributos"]]],
           PREVISOES / "previsoes_veiculo_mes.csv")
    salvar(modelo.exemplos(res), PREVISOES / "exemplos_previsoes_teste.csv")
    salvar(teste[teste.explicacao != ""][["veiculo_id", "competencia", "rotulo", "previsao_ml", "gap_km_l_pct",
                                          "explicacao"]], PREVISOES / "divergencias_teste.csv")
    (PREVISOES / "arvore_decisao.txt").write_text(res["regras_arvore"], encoding="utf-8")
    (PREVISOES / "metricas_modelo.json").write_text(json.dumps({
        "alvo": res["descricao_alvo"], "atributos": res["atributos"], "tamanhos": res["tamanhos"],
        "linha_de_base_teste": res["linha_de_base_teste"], "matriz_confusao": res["matriz_confusao"],
        "comparacao_modelos": res["comparacao_modelos"], "importancias": res["importancias"].to_dict(),
        "experimento_1": {"alvo": res1["descricao_alvo"], "linha_de_base_teste": res1["linha_de_base_teste"],
                          "arvore_decisao": res1["comparacao_modelos"]["arvore_decisao"]},
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    graficos.qualidade(ocorrencias, GRAFICOS / "01_qualidade_ocorrencias.png")
    graficos.custo_km_grupos(diag, est, GRAFICOS / "02_custo_km_por_grupo.png")
    graficos.ranking_gaps(diag, GRAFICOS / "03_ranking_gaps.png")
    graficos.participacao(por_cat, GRAFICOS / "04_participacao_categorias.png")
    graficos.conducao_vs_consumo(mensal, GRAFICOS / "05_conducao_vs_consumo.png")
    graficos.telemetria_exemplo(tratadas["telemetria"], "C-V07", "2026-03", "pesado",
                                GRAFICOS / "06_telemetria_C-V07.png")
    graficos.modelo(res, GRAFICOS / "07_modelo_arvore.png")

    ctx = {"estatisticas": est, "diagnostico": diag, "modelo": res, "modelo_exp1": res1, "comparacao": cmp_,
           "ocorrencias": ocorrencias, "base_mensal": base}
    (RELATORIOS / "resultados_sprint2.md").write_text(relatorios.sprint2_md(ctx), encoding="utf-8")
    etapa(11, "Saídas", "data/processed, outputs/reports, outputs/predictions e 7 gráficos em outputs/charts", t0)
    (RELATORIOS / "log_execucao.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print(f"\nConcluído. Resumo em {(RELATORIOS / 'resultados_sprint2.md').relative_to(RAIZ)}")
    return ctx


if __name__ == "__main__":
    main()
