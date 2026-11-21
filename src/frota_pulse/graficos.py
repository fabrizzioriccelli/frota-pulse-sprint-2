"""Gráficos da Sprint 2 (PNG em outputs/charts/), gerados a partir dos resultados calculados.

Convenções visuais (as mesmas da Sprint 1): paleta categórica validada em ordem fixa, cores de estado reservadas para
os níveis do diagnóstico e sempre acompanhadas de rótulo, texto em tinta neutra (nunca na cor da série), grade fina e
recessiva, um único eixo vertical por gráfico. Cada gráfico tem uma tabela equivalente em outputs/reports/.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .config import CATEGORIAS, LIMITE_ATENCAO, LIMITE_INEFICIENTE, LIMITES_TELEMETRIA, NOME_CATEGORIA  # noqa: E402

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
ESTADO = {"Eficiente": "#0ca30c", "Atenção": "#fab219", "Ineficiente": "#d03b3b", "Sem referência": "#b5b3ab"}
TINTA, TINTA2, MUDO, GRADE, SUPERFICIE = "#0b0b0b", "#52514e", "#6f6e69", "#e1e0d9", "#fcfcfb"

plt.rcParams.update({
    "font.family": ["Inter", "DejaVu Sans"], "font.size": 10, "axes.edgecolor": GRADE, "axes.labelcolor": TINTA2,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlecolor": TINTA, "axes.titlelocation": "left",
    "axes.titlepad": 30, "xtick.color": MUDO, "ytick.color": MUDO, "axes.grid": True, "grid.color": GRADE,
    "grid.linewidth": 0.6, "axes.axisbelow": True, "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False, "savefig.dpi": 150,
    "savefig.bbox": "tight", "savefig.facecolor": SUPERFICIE,
})


def _br(v: float, casas: int = 2) -> str:
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _nota(fig, texto: str) -> None:
    fig.text(0.01, -0.02, texto, color=MUDO, fontsize=8.5, ha="left", va="top")


def qualidade(ocorrencias: pd.DataFrame, caminho) -> None:
    cont = ocorrencias.groupby(["descricao_tipo", "tratamento"]).size().unstack(fill_value=0)
    ordem = cont.sum(axis=1).sort_values().index
    cont = cont.loc[ordem]
    trat = [t for t in ["EXCLUIDO", "QUARENTENA", "CORRIGIDO", "IMPUTADO", "ALERTA", "REJEITADO"] if t in cont]
    fig, ax = plt.subplots(figsize=(8.5, 4))
    esquerda = np.zeros(len(cont))
    for i, t in enumerate(trat):
        ax.barh(cont.index, cont[t], left=esquerda, height=0.6, color=SERIES[i], label=t.capitalize(),
                edgecolor=SUPERFICIE, linewidth=1.5)
        esquerda += cont[t].to_numpy()
    for y, tot in enumerate(esquerda):
        ax.text(tot + 2, y, f"{int(tot)}", va="center", color=TINTA2, fontsize=9)
    ax.set_title("Ocorrências de qualidade por tipo e tratamento")
    ax.set_xlabel("ocorrências")
    ax.grid(axis="y", visible=False)
    ax.legend(ncol=len(trat), loc="lower left", bbox_to_anchor=(0, 1.0), borderaxespad=0.2, fontsize=8.5)
    _nota(fig, "Nenhum registro é apagado: cada ocorrência tem arquivo, linha, tratamento e justificativa em "
               "outputs/reports/relatorio_qualidade.csv.")
    fig.savefig(caminho)
    plt.close(fig)


def custo_km_grupos(diag: pd.DataFrame, est: pd.DataFrame, caminho) -> None:
    validos = est[(est.indicador == "custo_km") & est.referencia_valida].sort_values("mediana")
    fig, ax = plt.subplots(figsize=(9, 4.6))
    rng = np.random.default_rng(3)
    for y, r in enumerate(validos.itertuples()):
        g = diag[(diag.grupo == r.grupo) & diag.gap_custo_km_pct.notna()]
        ax.plot([r.q1, r.q3], [y, y], color=GRADE, linewidth=8, solid_capstyle="round", zorder=1)
        ax.plot([r.mediana] * 2, [y - 0.28, y + 0.28], color=TINTA, linewidth=2, zorder=3)
        jitter = rng.uniform(-0.16, 0.16, len(g))
        for nivel_, cor in ESTADO.items():
            s = g.nivel_regras == nivel_
            ax.scatter(g.custo_km[s], y + jitter[s.to_numpy()], s=34, color=cor, edgecolor=SUPERFICIE, linewidth=1,
                       zorder=4, label=nivel_ if y == 0 else None)
        ax.text(r.mediana, y + 0.36, f"mediana R$ {_br(r.mediana)}", ha="center", color=TINTA2, fontsize=8.5)
    ax.set_yticks(range(len(validos)), [f"{n} (n={k})" for n, k in zip(validos.nome_grupo, validos.n)])
    ax.set_xlabel("custo por km no período (R$/km)")
    ax.set_title("Custo por km: cada ponto é um veículo, comparado só com o seu grupo")
    ax.grid(axis="y", visible=False)
    h, lbl = ax.get_legend_handles_labels()
    ax.legend(h, lbl, ncol=4, loc="lower left", bbox_to_anchor=(0, 1.0), borderaxespad=0.2, fontsize=8.5, title=None)
    _nota(fig, "Faixa cinza: do 1º ao 3º quartil do grupo. Traço preto: mediana (referência). Veículos locados ficam "
               "fora do custo total. Cor = nível do diagnóstico por regras.")
    fig.savefig(caminho)
    plt.close(fig)


def ranking_gaps(diag: pd.DataFrame, caminho, n: int = 12) -> None:
    r = diag[diag.pior_gap_pct.notna()].sort_values("pior_gap_pct", ascending=False).head(n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    cores = r.nivel_regras.map(ESTADO)
    ax.barh(r.veiculo_id, r.pior_gap_pct, height=0.6, color=cores, edgecolor=SUPERFICIE)
    for y, rr in enumerate(r.itertuples()):
        extra = " · baixa utilização" if rr.baixa_utilizacao else ""
        ax.text(rr.pior_gap_pct + 1.5, y, f"{_br(rr.pior_gap_pct, 1)}% ({rr.indicador_decisivo}){extra}",
                va="center", color=TINTA2, fontsize=8.5)
    for lim in (LIMITE_ATENCAO, LIMITE_INEFICIENTE):
        ax.axvline(lim, color=MUDO, linewidth=1, linestyle=(0, (3, 3)))
        ax.text(lim, -0.9, f"{lim:.0f}%", color=MUDO, fontsize=8, ha="center", va="top")
    ax.set_xlim(0, r.pior_gap_pct.max() * 1.45)
    ax.set_xlabel("pior gap desfavorável em relação à mediana do grupo (%)")
    ax.set_title(f"Ranking dos {n} veículos com maiores gaps de eficiência")
    ax.grid(axis="y", visible=False)
    _nota(fig, "Cor = nível do diagnóstico (vermelho: ineficiente; amarelo: atenção; verde: eficiente). Linhas "
               "tracejadas: limites de 5% (atenção) e 15% (ineficiente). O texto indica qual indicador decidiu.")
    fig.savefig(caminho)
    plt.close(fig)


def participacao(por_cat: pd.DataFrame, caminho) -> None:
    p = por_cat.pivot(index="grupo", columns="categoria", values="participacao_pct").reindex(columns=CATEGORIAS)
    p = p.loc[p.COMBUSTIVEL.sort_values().index]
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    esquerda = np.zeros(len(p))
    for i, c in enumerate(CATEGORIAS):
        ax.barh(p.index, p[c], left=esquerda, height=0.62, color=SERIES[i], label=NOME_CATEGORIA[c],
                edgecolor=SUPERFICIE, linewidth=2)
        for y, (x0, w) in enumerate(zip(esquerda, p[c])):
            if w >= 6:
                cor_txt = "#ffffff" if SERIES[i] in ("#2a78d6", "#008300", "#eb6834") else TINTA
                ax.text(x0 + w / 2, y, f"{w:.0f}%", ha="center", va="center", color=cor_txt, fontsize=8.5)
        esquerda += p[c].fillna(0).to_numpy()
    ax.set_xlim(0, 100)
    ax.set_xlabel("participação no custo total do grupo (%)")
    ax.set_title("Participação de cada categoria no custo, por grupo")
    ax.grid(axis="y", visible=False)
    ax.legend(ncol=6, loc="lower left", bbox_to_anchor=(0, 1.0), borderaxespad=0.2, fontsize=8.5)
    _nota(fig, "Participação = custo da categoria ÷ custo total × 100. Rótulos só em segmentos de 6% ou mais; "
               "valores completos em outputs/reports/custos_por_categoria.csv.")
    fig.savefig(caminho)
    plt.close(fig)


def conducao_vs_consumo(mensal: pd.DataFrame, caminho) -> None:
    d = mensal[mensal.gap_km_l_pct.notna() & mensal.pct_rpm_acima_verde.notna()]
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.6), sharey=True)
    for ax, col, nome in zip(axs, ["pct_rpm_acima_verde", "pct_marcha_lenta", "pct_excesso_velocidade"],
                             ["rotação acima da faixa verde (%)", "tempo em marcha lenta (%)",
                              "leituras com excesso de velocidade (%)"]):
        ax.scatter(d[col], d.gap_km_l_pct, s=9, color=SERIES[0], alpha=0.45, edgecolor="none")
        r = d[[col, "gap_km_l_pct"]].corr().iloc[0, 1]
        ax.set_xlabel(nome)
        ax.text(0.03, 0.95, f"correlação {_br(r, 2)}", transform=ax.transAxes, color=TINTA2, fontsize=9, va="top")
        ax.axhline(LIMITE_ATENCAO, color=MUDO, linewidth=1, linestyle=(0, (3, 3)))
    axs[0].set_ylabel("gap de consumo no mês (%)\n(positivo = pior que o grupo)")
    fig.suptitle("Sinais de condução do ESP32 x consumo do mês (cada ponto é um veículo-mês)", x=0.01, ha="left",
                 fontsize=12, fontweight="bold", color=TINTA)
    _nota(fig, "Linha tracejada: limite de 5% usado como rótulo do modelo. Dados simulados: a relação foi construída "
               "na simulação e não prova causalidade em frotas reais.")
    fig.savefig(caminho)
    plt.close(fig)


def telemetria_exemplo(leituras: pd.DataFrame, veiculo: str, competencia: str, classe: str, caminho) -> None:
    t = leituras[(leituras.veiculo_id == veiculo) & (leituras.competencia == competencia)].sort_values("leitura")
    lim = LIMITES_TELEMETRIA[classe]
    series = [("velocidade_kmh", "velocidade (km/h)", lim["vel_max_rodovia"], "VEL_EXCESSO"),
              ("rpm", "rotação (RPM)", lim["rpm_limite"], "RPM_ALTO"),
              ("temperatura_c", "temperatura (°C)", lim["temp_limite"], "TEMP_ALTA"),
              ("nivel_combustivel_pct", "combustível (%)", lim["comb_min"], "COMB_BAIXO")]
    fig, axs = plt.subplots(4, 1, figsize=(9, 7.2), sharex=True)
    for ax, (col, nome, limite, codigo) in zip(axs, series):
        ax.plot(t.leitura, t[col], color=SERIES[0], linewidth=2)
        ax.axhline(limite, color=ESTADO["Ineficiente"], linewidth=1, linestyle=(0, (3, 3)))
        ax.text(t.leitura.max() + 0.8, limite, f"limite {limite}", color=TINTA2, fontsize=8, va="center")
        alerta = t.alertas.str.contains(codigo, na=False)
        ax.scatter(t.leitura[alerta], t[col][alerta], s=30, color=ESTADO["Ineficiente"], edgecolor=SUPERFICIE,
                   zorder=3, label="leitura com alerta da grandeza" if col == "velocidade_kmh" else None)
        ax.text(0.005, 0.92, f"{int(alerta.sum())} alerta(s) {codigo}", transform=ax.transAxes, color=TINTA2,
                fontsize=8)
        ax.set_ylabel(nome, fontsize=9)
    axs[0].legend(loc="lower left", bbox_to_anchor=(0, 1.0), borderaxespad=0.2, fontsize=8.5)
    axs[-1].set_xlabel("leitura (1 por minuto simulado)")
    fig.suptitle(f"Telemetria do ESP32: {veiculo}, {competencia} (60 leituras)", x=0.01, ha="left", fontsize=12,
                 fontweight="bold", color=TINTA)
    fig.tight_layout()
    fig.savefig(caminho)
    plt.close(fig)


def modelo(res: dict, caminho) -> None:
    imp = res["importancias"].sort_values()
    cm = res["matriz_confusao"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 3.8), gridspec_kw={"width_ratios": [1.3, 1]})
    a1.barh([i.replace("_", " ") for i in imp.index], imp.values, height=0.55, color=SERIES[0])
    for y, v in enumerate(imp.values):
        a1.text(v + 0.01, y, _br(v, 2), va="center", color=TINTA2, fontsize=8.5)
    a1.set_xlim(0, imp.max() * 1.25)
    a1.set_title("Importância dos atributos na árvore")
    a1.grid(axis="y", visible=False)
    matriz = np.array([[cm["vn"], cm["fp"]], [cm["fn"], cm["vp"]]])
    a2.imshow(matriz, cmap=matplotlib.colors.LinearSegmentedColormap.from_list("azul", ["#eef4fd", "#2a78d6"]))
    for i in range(2):
        for j in range(2):
            a2.text(j, i, str(matriz[i, j]), ha="center", va="center", fontsize=14,
                    color="#ffffff" if matriz[i, j] > matriz.max() * 0.6 else TINTA)
    a2.set_xticks([0, 1], ["previsto: dentro", "previsto: acima"])
    a2.set_yticks([0, 1], ["real: dentro", "real: acima"])
    a2.grid(False)
    a2.set_title("Matriz de confusão (teste)")
    m = res["comparacao_modelos"]["arvore_decisao"]["teste"]
    _nota(fig, f"Conjunto de teste: {res['tamanhos']['teste']} veículo-mês de {res['tamanhos']['veiculos_teste']} "
               f"veículos que o modelo nunca viu. Acurácia {_br(100 * m['acuracia'], 1)}% (linha de base "
               f"{_br(100 * res['linha_de_base_teste'], 1)}%), recall {_br(100 * m['recall_ineficiente'], 1)}%.")
    fig.tight_layout()
    fig.savefig(caminho)
    plt.close(fig)
