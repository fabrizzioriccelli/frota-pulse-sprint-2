"""Relatórios em Markdown gerados a partir dos resultados (os números nunca são digitados à mão)."""
from __future__ import annotations

import pandas as pd

from .config import CATEGORIAS, LIMITE_ATENCAO, LIMITE_INEFICIENTE, NOME_CATEGORIA


def br(v, casas: int = 2) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "-"
    if isinstance(v, (int,)) and not isinstance(v, bool):
        return f"{v:,}".replace(",", ".")
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def tabela_md(df: pd.DataFrame, formatos: dict | None = None) -> str:
    formatos = formatos or {}
    linhas = ["| " + " | ".join(str(c) for c in df.columns) + " |", "|" + "---|" * len(df.columns)]
    for r in df.itertuples(index=False):
        cel = []
        for c, v in zip(df.columns, r):
            f = formatos.get(c)
            texto = f(v) if f else ("-" if (isinstance(v, float) and pd.isna(v)) else str(v))
            cel.append(texto.replace("|", "\\|"))
        linhas.append("| " + " | ".join(cel) + " |")
    return "\n".join(linhas)


def qualidade_md(resumo_arquivos: pd.DataFrame, ocorrencias: pd.DataFrame) -> str:
    por_tipo = (ocorrencias.groupby(["descricao_tipo", "regra", "tratamento"]).size().rename("ocorrencias")
                .reset_index().sort_values(["descricao_tipo", "regra"]))
    justif = ocorrencias.drop_duplicates(["regra", "tratamento", "justificativa"])[
        ["regra", "descricao_tipo", "tratamento", "justificativa"]].sort_values("regra")
    exemplos = ocorrencias.groupby("regra").head(1)[["id", "regra", "arquivo", "linha", "registro", "campo",
                                                     "valor_encontrado", "tratamento"]]
    total = int(resumo_arquivos.registros_lidos.sum())
    return "\n\n".join([
        "# Relatório de qualidade dos dados",
        "Gerado por `src/executar_pipeline.py`. Dados simulados. A lista completa, uma linha por ocorrência, está em "
        "`outputs/reports/relatorio_qualidade.csv`.",
        f"**Registros analisados:** {br(total)} em {len(resumo_arquivos)} arquivos. "
        f"**Ocorrências:** {br(len(ocorrencias))}.",
        "## Por arquivo de origem", tabela_md(resumo_arquivos, {"registros_lidos": br}),
        "## Por tipo de inconsistência e tratamento", tabela_md(por_tipo),
        "## Tratamento aplicado e justificativa", tabela_md(justif),
        "## Um exemplo de cada regra (registro afetado)", tabela_md(exemplos),
    ]) + "\n"


def sprint2_md(ctx: dict) -> str:
    est, diag, res, res1, cmp_ = ctx["estatisticas"], ctx["diagnostico"], ctx["modelo"], ctx["modelo_exp1"], ctx["comparacao"]
    oc, base = ctx["ocorrencias"], ctx["base_mensal"]
    ref = est[est.indicador.isin(["custo_km", "km_l"])].pivot_table(
        index=["nome_grupo"], columns="indicador", values=["n", "media", "mediana", "q1", "q3"])
    linhas_ref = []
    for g, r in ref.iterrows():
        linhas_ref.append({"Grupo": g, "n (custo)": int(r[("n", "custo_km")]),
                           "R$/km média": br(r[("media", "custo_km")], 3), "R$/km mediana": br(r[("mediana", "custo_km")], 3),
                           "R$/km Q1–Q3": f"{br(r[('q1', 'custo_km')], 3)} a {br(r[('q3', 'custo_km')], 3)}",
                           "km/L mediana": br(r[("mediana", "km_l")], 2),
                           "km/L Q1–Q3": f"{br(r[('q1', 'km_l')], 2)} a {br(r[('q3', 'km_l')], 2)}",
                           "Referência válida": "sim" if r[("n", "custo_km")] >= 5 else "não (n < 5)"})
    niveis = diag.nivel_regras.value_counts()
    gaps = diag.gap_custo_km_pct.dropna()
    gaps_kml = diag.gap_km_l_pct.dropna()
    t = res["comparacao_modelos"]
    comp_modelos = pd.DataFrame([{"Modelo": n.replace("_", " "), "Acurácia teste": br(100 * m["teste"]["acuracia"], 1) + "%",
                                  "Acurácia balanceada": br(100 * m["teste"]["acuracia_balanceada"], 1) + "%",
                                  "Precisão (acima)": br(100 * m["teste"]["precisao_ineficiente"], 1) + "%",
                                  "Recall (acima)": br(100 * m["teste"]["recall_ineficiente"], 1) + "%"}
                                 for n, m in t.items()])
    ineficientes = diag[diag.nivel_regras.isin(["Ineficiente", "Atenção"])].sort_values("pior_gap_pct", ascending=False)
    custo_cat = base.groupby("empresa_id")[[f"custo_{c.lower()}" for c in CATEGORIAS]].sum()
    custo_cat.columns = [NOME_CATEGORIA[c] for c in CATEGORIAS]
    custo_cat["Total"] = custo_cat.sum(axis=1)
    custo_cat = custo_cat.reset_index().rename(columns={"empresa_id": "Empresa"})
    conc = cmp_.concordam.mean()
    partes = [
        "# Resultados da Sprint 2 (gerado automaticamente)",
        "Todos os números abaixo foram calculados por `src/executar_pipeline.py` sobre **dados simulados** de três "
        "frotas fictícias. Não representam clientes reais da Sem Parar Empresas.",
        "## 1. Qualidade",
        f"{br(len(oc))} ocorrências: " + ", ".join(f"{k.lower()} {v}" for k, v in oc.tratamento.value_counts().items())
        + ". Detalhe em `relatorio_qualidade.md`.",
        "## 2. Custo total por categoria (R$, competência na janela de análise)",
        tabela_md(custo_cat, {c: lambda v: br(v, 0) for c in custo_cat.columns if c != "Empresa"}),
        "## 3. Benchmark por grupo",
        tabela_md(pd.DataFrame(linhas_ref)),
        f"Dispersão dos gaps entre veículos semelhantes: mediana do gap absoluto de custo por km = "
        f"{br(gaps.abs().median(), 1)}%, de consumo = {br(gaps_kml.abs().median(), 1)}%; percentil 90 do gap de custo = "
        f"{br(gaps.quantile(0.9), 1)}%, de consumo = {br(gaps_kml.quantile(0.9), 1)}%. Esses valores sustentam os limites "
        f"de {br(LIMITE_ATENCAO, 0)}% (atenção) e {br(LIMITE_INEFICIENTE, 0)}% (ineficiente).",
        "## 4. Diagnóstico por regras",
        ", ".join(f"{k}: {v}" for k, v in niveis.items()) + ".",
        tabela_md(ineficientes[["veiculo_id", "nome_grupo", "nivel_regras", "pior_gap_pct", "justificativa"]].rename(
            columns={"veiculo_id": "Veículo", "nome_grupo": "Grupo", "nivel_regras": "Nível", "pior_gap_pct": "Pior gap %",
                     "justificativa": "Justificativa"}), {"Pior gap %": lambda v: br(v, 1)}),
        "## 5. Modelo supervisionado",
        f"Alvo: {res['descricao_alvo']}. {res['tamanhos']['veiculo_meses']} veículo-mês; treino "
        f"{res['tamanhos']['treino']} ({res['tamanhos']['veiculos_treino']} veículos), teste {res['tamanhos']['teste']} "
        f"({res['tamanhos']['veiculos_teste']} veículos). Proporção da classe positiva no teste: "
        f"{br(100 * res['tamanhos']['taxa_ineficiente_teste'], 1)}%. Linha de base (sempre prever a classe majoritária): "
        f"{br(100 * res['linha_de_base_teste'], 1)}%.",
        tabela_md(comp_modelos),
        f"Matriz de confusão da árvore (teste): verdadeiros negativos {res['matriz_confusao']['vn']}, falsos positivos "
        f"{res['matriz_confusao']['fp']}, falsos negativos {res['matriz_confusao']['fn']}, verdadeiros positivos "
        f"{res['matriz_confusao']['vp']}.",
        f"**Experimento 1 (descartado):** alvo = {res1['descricao_alvo']}. Acurácia da árvore no teste "
        f"{br(100 * res1['comparacao_modelos']['arvore_decisao']['teste']['acuracia'], 1)}% contra linha de base "
        f"{br(100 * res1['linha_de_base_teste'], 1)}%: a telemetria não antecipa custos de manutenção, pedágio e "
        "custo fixo.",
        "Regras aprendidas pela árvore:", "```\n" + res["regras_arvore"] + "```",
        "## 6. Regras x modelo (veículos de teste)",
        f"Concordância: {int(cmp_.concordam.sum())} de {len(cmp_)} veículos ({br(100 * conc, 0)}%).",
        tabela_md(cmp_[["veiculo_id", "nivel_regras", "leitura_ml", "meses", "meses_consumo_ruim_real",
                        "meses_consumo_ruim_previstos", "interpretacao"]].rename(columns={
            "veiculo_id": "Veículo", "nivel_regras": "Regras", "leitura_ml": "Modelo", "meses": "Meses",
            "meses_consumo_ruim_real": "Meses consumo ruim (real)", "meses_consumo_ruim_previstos": "(previstos)",
            "interpretacao": "Interpretação"})),
    ]
    return "\n\n".join(partes) + "\n"
