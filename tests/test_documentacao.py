"""Conferência da documentação: template do README, links internos e números citados contra as saídas do pipeline."""
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
README = (RAIZ / "README.md").read_text(encoding="utf-8")
DOCS = [RAIZ / "README.md", *sorted((RAIZ / "docs").glob("*.md"))]


def br(v: float, casas: int = 1) -> str:
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def sem_codigo(texto: str) -> str:
    return re.sub(r"```.*?```", "", texto, flags=re.S)


def ancoras(texto: str) -> set[str]:
    saida = set()
    for t in re.findall(r"^#{1,6} (.+)$", sem_codigo(texto), re.M):
        t = unicodedata.normalize("NFC", t.strip().lower())
        t = re.sub(r"[^\w\- ]", "", t)
        saida.add(t.replace(" ", "-"))
    return saida


def test_readme_segue_o_template_2026():
    secoes = ["# ENTERPRISE CHALLENGE - ", "## 👨‍🎓 Integrantes", "## 👩‍🏫 Professores", "### Tutor(a)", "### Coordenador(a)",
              "## 📜 Descrição", "## 📁 Estrutura de pastas", "## 📎 Links e Observações", "### Listagem de Links",
              "### Explicação de decisões técnicas", "### Observações Gerais", "### Detalhamento da ideia",
              "### Avanços e ajustes", "## 🔧 Como executar o código", "## 🗃 Histórico de lançamentos", "## 📋 Licença"]
    assert [s for s in secoes if s not in README] == []
    assert "OBSERVAÇÃO DO TUTOR" not in README
    assert re.search(r"\[[xX]\] Sim, aceitamos participar", README)
    assert len(re.findall(r"RM \d{6}", README.split("## 👩‍🏫")[0])) == 5


def test_descricao_tem_ate_600_palavras():
    descricao = README.split("## 📜 Descrição")[1].split("## 📁")[0]
    descricao = re.sub(r"\]\([^)]*\)", "]", descricao)
    assert len(re.findall(r"\w+", descricao)) <= 600


def test_links_e_ancoras_internos_existem():
    quebrados = []
    for md in DOCS:
        texto = sem_codigo(md.read_text(encoding="utf-8"))
        for alvo in re.findall(r"\]\(([^)\s]+)\)", texto) + re.findall(r'src="([^"]+)"', texto):
            if alvo.startswith(("http://", "https://", "mailto:")):
                continue
            caminho, _, ancora = alvo.partition("#")
            destino = (md.parent / caminho).resolve() if caminho else md
            if not destino.exists():
                quebrados.append(f"{md.name}: {alvo}")
            elif ancora and destino.suffix == ".md" and ancora not in ancoras(destino.read_text(encoding="utf-8")):
                quebrados.append(f"{md.name}: âncora {alvo}")
    assert quebrados == []


def test_numeros_do_readme_conferem_com_as_saidas():
    m = json.loads((RAIZ / "outputs" / "predictions" / "metricas_modelo.json").read_text(encoding="utf-8"))
    teste = m["comparacao_modelos"]["arvore_decisao"]["teste"]
    qualidade = pd.read_csv(RAIZ / "outputs" / "reports" / "relatorio_qualidade.csv")
    niveis = pd.read_csv(RAIZ / "outputs" / "reports" / "indicadores_e_diagnostico_veiculo.csv")["nivel_regras"].value_counts()
    comp = pd.read_csv(RAIZ / "outputs" / "reports" / "comparacao_regras_ml.csv")
    citados = [
        f"{br(len(qualidade), 0)} ocorrências",
        f"{niveis['Eficiente']} veículos eficientes, {niveis['Atenção']} em atenção, {niveis['Ineficiente']} ineficientes "
        f"e {niveis['Sem referência']} sem referência",
        f"{br(teste['acuracia'] * 100)}%",
        f"{br(m['linha_de_base_teste'] * 100)}%",
        f"{int(comp['concordam'].sum())} de {len(comp)} veículos",
    ]
    assert [c for c in citados if c not in README] == []


def test_sem_dados_pessoais_ou_segredos():
    padroes = [r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b", r"-----BEGIN [A-Z ]*PRIVATE KEY",
               r"\bgh[pousr]_[A-Za-z0-9]{30,}", r"[\w.+-]+@[\w-]+\.(?:com|br|org)\b"]
    achados = []
    for p in [*DOCS, *(RAIZ / "data" / "raw").rglob("*.*"), *(RAIZ / "src").rglob("*.py")]:
        texto = p.read_text(encoding="utf-8", errors="replace")
        achados += [f"{p.name}: {x}" for rx in padroes for x in re.findall(rx, texto)]
    assert achados == []
