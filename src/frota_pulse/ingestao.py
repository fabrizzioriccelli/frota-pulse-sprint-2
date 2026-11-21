"""Etapa 1 — Ingestão: lê os arquivos de entrada (CSV, TXT e JSON) sem alterar nenhum valor.

Cada arquivo vira um `Lote`: os registros lidos (todos como texto, exatamente como estão no arquivo), a fonte, o
formato, o hash SHA-256 do conteúdo e as linhas que não puderam ser lidas. Toda linha recebe `_arquivo` e `_linha`,
que acompanham o registro até o relatório final: qualquer número calculado pode ser rastreado até a linha de origem.
"""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .config import BRUTOS, RAIZ, TELEMETRIA

# Padrão de nome de arquivo -> (fonte, formato). A ordem importa: o primeiro padrão que casar decide.
FONTES = [
    ("cadastro/*.csv", "cadastro", "csv"),
    ("combustivel/abastecimentos_cartao*.csv", "combustivel", "csv"),
    ("combustivel/notas_fiscais*.json", "nfe_combustivel", "json"),
    ("pedagio/*.txt", "pedagio", "txt"),
    ("manutencao/*.json", "manutencao", "json"),
    ("multas/*.json", "multas", "json"),
    ("financeiro/*.csv", "financeiro", "csv"),
    ("operacao/*.json", "quilometragem", "json"),
]


@dataclass
class Lote:
    fonte: str
    formato: str
    arquivo: str            # caminho relativo à raiz do repositório
    hash_sha256: str
    dados: pd.DataFrame
    metadados: dict = field(default_factory=dict)
    rejeitadas: list[dict] = field(default_factory=list)  # linhas que não puderam ser interpretadas

    @property
    def registros(self) -> int:
        return len(self.dados)


def _hash(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def _rel(caminho: Path) -> str:
    return caminho.relative_to(RAIZ).as_posix()


def ler_csv(caminho: Path) -> pd.DataFrame:
    """CSV com separador detectado na primeira linha (vírgula ou ponto e vírgula). Tudo é lido como texto."""
    with open(caminho, encoding="utf-8", newline="") as f:
        sep = csv.Sniffer().sniff(f.readline(), delimiters=",;").delimiter
    df = pd.read_csv(caminho, sep=sep, dtype=str, keep_default_na=False)
    df.insert(0, "_linha", range(2, len(df) + 2))  # linha 1 é o cabeçalho
    return df


def ler_txt_extrato(caminho: Path) -> tuple[pd.DataFrame, list[dict], dict]:
    """Extrato em texto com campos separados por ' | '. Linhas de título, período e totais são ignoradas; linhas de
    dados com quantidade errada de campos são rejeitadas e registradas (não são descartadas em silêncio)."""
    colunas, registros, rejeitadas, meta = None, [], [], {}
    for n, linha in enumerate(caminho.read_text(encoding="utf-8").splitlines(), 1):
        texto = linha.strip()
        if not texto or set(texto) == {"-"}:
            continue
        if texto.startswith("EXTRATO"):
            meta["titulo"] = texto
            continue
        if texto.startswith(("PERÍODO", "PERIODO", "TOTAL")):
            chave, _, valor = texto.partition(":")
            meta[chave.strip().lower()] = valor.strip()
            continue
        if colunas is None and " | " in texto:
            colunas = [c.strip().lower() for c in texto.split(" | ")]
            continue
        campos = [c.strip() for c in texto.split("|")]  # split em "|" preserva o último campo vazio
        if colunas is None or len(campos) != len(colunas):
            rejeitadas.append({"_linha": n, "conteudo": texto,
                               "motivo": f"{len(campos)} campos; esperados {len(colunas or [])}"})
            continue
        registros.append({"_linha": n, **dict(zip(colunas, campos))})
    return pd.DataFrame(registros), rejeitadas, meta


def ler_json(caminho: Path) -> tuple[pd.DataFrame, dict]:
    """JSON como lista de objetos ou como objeto com uma lista dentro. Ordens de serviço têm itens aninhados:
    cada item vira uma linha, com os dados da ordem repetidos (a normalização soma os itens)."""
    conteudo = json.loads(caminho.read_text(encoding="utf-8"))
    meta = {}
    if isinstance(conteudo, dict):
        chave = next(k for k, v in conteudo.items() if isinstance(v, list))
        meta = {k: v for k, v in conteudo.items() if k != chave}
        conteudo = conteudo[chave]
    for i, item in enumerate(conteudo):
        item["_linha"] = i + 1  # posição do registro na lista
    if conteudo and "itens" in conteudo[0]:
        meta_cols = [k for k in conteudo[0] if k != "itens"]
        df = pd.json_normalize(conteudo, record_path="itens", meta=meta_cols, record_prefix="item_")
    else:
        df = pd.DataFrame(conteudo)
    return df.astype(object).where(df.notna(), None), meta


def ler_arquivo(caminho: Path, fonte: str, formato: str) -> Lote:
    rejeitadas, meta = [], {}
    if formato == "csv":
        dados = ler_csv(caminho)
    elif formato == "txt":
        dados, rejeitadas, meta = ler_txt_extrato(caminho)
    elif formato == "json":
        dados, meta = ler_json(caminho)
    else:
        raise ValueError(f"formato não suportado: {formato}")
    dados.insert(0, "_arquivo", _rel(caminho))
    return Lote(fonte, formato, _rel(caminho), _hash(caminho), dados, meta, rejeitadas)


def ingerir(pasta: Path = BRUTOS, pasta_telemetria: Path = TELEMETRIA) -> list[Lote]:
    """Lê todos os arquivos reconhecidos. Arquivos não reconhecidos são ignorados e listados no lote 'ignorados'."""
    lotes, vistos = [], set()
    for padrao, fonte, formato in FONTES:
        for caminho in sorted(pasta.glob(padrao)):
            if caminho not in vistos:
                vistos.add(caminho)
                lotes.append(ler_arquivo(caminho, fonte, formato))
    for caminho in sorted(pasta_telemetria.glob("*.csv")):
        lotes.append(ler_arquivo(caminho, "telemetria", "csv"))
    return lotes


def resumo(lotes: list[Lote]) -> pd.DataFrame:
    return pd.DataFrame([{"arquivo": lt.arquivo, "fonte": lt.fonte, "formato": lt.formato, "registros": lt.registros,
                          "linhas_rejeitadas": len(lt.rejeitadas), "hash_sha256": lt.hash_sha256[:12]}
                         for lt in lotes])
