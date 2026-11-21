"""Etapa 2 — Normalização: transforma cada fonte em um esquema comum, com tipos, unidades e categorias padronizados.

Regras gerais (detalhadas em docs/metodologia.md):
  * colunas renomeadas para o esquema canônico (veiculo_id, data_evento, valor_brl, litros, ...);
  * números no formato brasileiro ("R$ 1.234,56") ou internacional ("1234.56") convertidos para float;
  * datas em dd/mm/aaaa, aaaa-mm-dd ou ISO com hora convertidas para data; texto que não é uma data válida vira
    NaT, e o texto original é guardado em `data_texto` para o relatório de qualidade;
  * competência (mês a que o custo pertence) no formato AAAA-MM; impostos e seguro trazem início e fim;
  * distâncias em metros convertidas para km; valores em reais; volumes em litros;
  * categoria de custo em uma das seis categorias do projeto, a partir do campo de origem ou do texto do lançamento.
Nada é descartado aqui: valores problemáticos seguem para a etapa de qualidade, que decide o tratamento.
"""
from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd

from .config import GRUPOS, MAPA_CATEGORIA, PERFIL_OPERACAO
from .ingestao import Lote

COLUNAS_CUSTO = ["registro_id", "fonte", "_arquivo", "_linha", "veiculo_id", "centro_custo", "data_evento",
                 "data_texto", "competencia_inicio", "competencia_fim", "categoria", "subcategoria", "valor_brl",
                 "valor_texto", "litros", "preco_litro", "odometro_km", "produto", "tipo_lancamento", "natureza",
                 "local", "itens_negativos"]


def sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().lower()


def numero(texto) -> float:
    """'R$ 1.234,56' -> 1234.56; '1234.56' -> 1234.56; '' ou None -> NaN."""
    if texto is None or (isinstance(texto, float) and np.isnan(texto)):
        return np.nan
    if isinstance(texto, (int, float, np.number)):
        return float(texto)
    s = str(texto).replace("R$", "").replace(" ", "").strip()
    if not s:
        return np.nan
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return np.nan


def numeros(serie: pd.Series) -> pd.Series:
    return serie.map(numero).astype(float)


def datas(serie: pd.Series, formatos: list[str]) -> pd.Series:
    """Converte texto em data tentando cada formato, de forma estrita: '31/02/2026' resulta em NaT."""
    texto = serie.fillna("").astype(str).str.strip()
    saida = pd.Series(pd.NaT, index=serie.index, dtype="datetime64[ns]")
    for fmt in formatos:
        faltam = saida.isna()
        saida[faltam] = pd.to_datetime(texto[faltam], format=fmt, errors="coerce")
    return saida


def competencia_de(texto: str | None) -> str | None:
    """'03/2026' ou '2026-03' -> '2026-03'; mês inexistente -> None."""
    if not texto:
        return None
    m = re.fullmatch(r"(\d{2})/(\d{4})", texto) or re.fullmatch(r"(\d{4})-(\d{2})", texto)
    if not m:
        return None
    a, mes = (m.group(2), m.group(1)) if "/" in texto else (m.group(1), m.group(2))
    return f"{a}-{mes}" if 1 <= int(mes) <= 12 else None


def mes(datas_: pd.Series) -> pd.Series:
    return datas_.dt.strftime("%Y-%m").where(datas_.notna(), None)


def categoria_por_texto(texto: str) -> str:
    t = sem_acento(texto)
    return next((cat for termo, cat in MAPA_CATEGORIA if termo in t), "OUTROS")


def produto_padrao(texto: str) -> str:
    t = sem_acento(texto)
    if "s500" in t:
        return "diesel_s500"
    if "diesel" in t:
        return "diesel_s10"
    if "gasolina" in t:
        return "gasolina"
    if "etanol" in t:
        return "etanol"
    return "ajuste" if "ajuste" in t else t or ""


def _base(df: pd.DataFrame, fonte: str) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index, columns=COLUNAS_CUSTO, dtype=object)
    out["fonte"] = fonte
    out["_arquivo"] = df["_arquivo"]
    out["_linha"] = df["_linha"]
    out["natureza"] = "proprio"
    out["itens_negativos"] = 0
    return out


# ---------------------------------------------------------------- por fonte

def cadastro(lote: Lote) -> pd.DataFrame:
    d = lote.dados
    v = pd.DataFrame({
        "veiculo_id": d.codigo_veiculo.str.strip().str.upper(), "empresa_id": d.empresa, "frota_id": d.codigo_frota,
        "frota": d.frota,
        "categoria_id": d.categoria, "classe_peso": d.porte,
        "perfil_operacao": d.modalidade_operacional.map(PERFIL_OPERACAO), "ano_fabricacao": d.ano_fabricacao.astype(int),
        "propriedade": d.propriedade, "combustivel": d.combustivel,
        "capacidade_tanque_l": numeros(d.capacidade_tanque_l), "situacao": d.situacao,
        "_arquivo": d._arquivo, "_linha": d._linha})
    chaves = list(zip(v.classe_peso, v.perfil_operacao, v.categoria_id))
    v["grupo"] = [GRUPOS.get(k, ("SEM_GRUPO", "Sem grupo"))[0] for k in chaves]
    v["nome_grupo"] = [GRUPOS.get(k, ("SEM_GRUPO", "Sem grupo"))[1] for k in chaves]
    return v


def combustivel(lote: Lote) -> pd.DataFrame:
    d = lote.dados
    out = _base(d, "combustivel")
    out["registro_id"] = d.ID_TRANSACAO
    out["veiculo_id"] = d.VEICULO.str.strip().str.upper().replace("", None)
    out["data_texto"] = d.DATA_HORA
    out["data_evento"] = datas(d.DATA_HORA, ["%d/%m/%Y %H:%M", "%d/%m/%Y"])
    out["competencia_inicio"] = out["competencia_fim"] = mes(out.data_evento)
    out["categoria"] = "COMBUSTIVEL"
    out["produto"] = d.PRODUTO.map(produto_padrao)
    out["subcategoria"] = out.produto
    out["tipo_lancamento"] = d.TIPO_LANCAMENTO.str.upper()
    out["valor_texto"] = d.VALOR_TOTAL
    out["valor_brl"] = numeros(d.VALOR_TOTAL)
    out["litros"] = numeros(d.LITROS)
    out["preco_litro"] = numeros(d.PRECO_LITRO)
    out["odometro_km"] = numeros(d.ODOMETRO_KM)
    out["local"] = d.POSTO
    return out


def nfe_combustivel(lote: Lote) -> pd.DataFrame:
    d = lote.dados
    out = _base(d, "nfe_combustivel")
    out["registro_id"] = d.chave_nfe
    out["veiculo_id"] = d.veiculo
    out["data_texto"] = d.emissao
    out["data_evento"] = datas(d.emissao, ["%Y-%m-%dT%H:%M", "%Y-%m-%d"])
    out["competencia_inicio"] = out["competencia_fim"] = mes(out.data_evento)
    out["categoria"] = "COMBUSTIVEL"
    out["produto"] = d["produto"].map(produto_padrao)
    out["subcategoria"] = out.produto
    out["tipo_lancamento"] = "COMPRA"
    out["valor_texto"] = d.valor_total.astype(str)
    out["valor_brl"] = numeros(d.valor_total)
    out["litros"] = numeros(d.quantidade_l)
    out["preco_litro"] = numeros(d.valor_unitario)
    return out


def pedagio(lote: Lote) -> pd.DataFrame:
    d = lote.dados
    out = _base(d, "pedagio")
    out["registro_id"] = d.transacao
    out["veiculo_id"] = d.veiculo.str.upper().replace("", None)
    out["data_texto"] = d.data_hora
    out["data_evento"] = datas(d.data_hora, ["%d/%m/%Y %H:%M"])
    out["competencia_inicio"] = out["competencia_fim"] = mes(out.data_evento)
    out["categoria"] = "PEDAGIO"
    out["subcategoria"] = np.where(d.pagador.str.contains("EMBARCADOR"), "passagem_vale_pedagio", "passagem_tag")
    out["local"] = d.praca
    out["natureza"] = np.where(d.pagador.str.contains("EMBARCADOR"), "terceiro", "proprio")
    out["valor_texto"] = d.valor
    out["valor_brl"] = numeros(d.valor)
    return out


def manutencao(lote: Lote) -> pd.DataFrame:
    """Soma os itens de cada ordem de serviço; conta itens negativos para a etapa de qualidade."""
    d = lote.dados.copy()
    d["item_valor"] = numeros(d.item_valor)
    g = d.groupby("numero_os", sort=False)
    os_ = g.first()
    os_["valor_total"] = g.item_valor.sum(min_count=1)
    os_["negativos"] = g.item_valor.apply(lambda s: int((s < 0).sum()))
    os_ = os_.reset_index()
    out = _base(os_, "manutencao")
    out["registro_id"] = os_.numero_os
    out["veiculo_id"] = os_.veiculo
    out["data_texto"] = os_.data_entrada
    out["data_evento"] = datas(os_.data_entrada, ["%Y-%m-%d"])
    out["competencia_inicio"] = out["competencia_fim"] = mes(out.data_evento)
    out["categoria"] = "MANUTENCAO"
    out["subcategoria"] = os_.natureza + "_" + os_.sistema
    out["valor_brl"] = os_.valor_total
    out["valor_texto"] = os_.valor_total.astype(str)
    out["odometro_km"] = numeros(os_.odometro_km)
    out["itens_negativos"] = os_.negativos
    return out


def multas(lote: Lote) -> pd.DataFrame:
    d = lote.dados
    out = _base(d, "multas")
    out["registro_id"] = d.id_lancamento
    out["veiculo_id"] = d.veiculo
    # O custo da multa pertence ao mês da notificação; o pagamento pode ser posterior à data da análise
    out["data_texto"] = d.data_notificacao
    out["data_evento"] = datas(d.data_notificacao, ["%Y-%m-%d"])
    out["competencia_inicio"] = out["competencia_fim"] = mes(out.data_evento)
    out["categoria"] = "MULTAS"
    out["subcategoria"] = np.where(d.tipo.str.startswith("NIC"), "multa_nic", "infracao_" + d.gravidade.astype(str))
    out["valor_brl"] = numeros(d.valor_pago)
    out["valor_texto"] = d.valor_pago.astype(str)
    return out


def financeiro(lote: Lote) -> pd.DataFrame:
    d = lote.dados
    out = _base(d, "financeiro")
    out["registro_id"] = d.documento
    eh_veiculo = d.centro_custo.str.match(r"^[A-Z]-V\d+$")
    out["veiculo_id"] = d.centro_custo.where(eh_veiculo, None)
    out["centro_custo"] = d.centro_custo
    out["data_texto"] = d.data_lancamento
    out["data_evento"] = datas(d.data_lancamento, ["%Y-%m-%d"])
    out["competencia_inicio"] = d.competencia_inicial.map(competencia_de)
    out["competencia_fim"] = d.competencia_final.map(competencia_de)
    out["categoria"] = (d.conta + " " + d.historico).map(categoria_por_texto)
    out["subcategoria"] = d.conta.map(lambda c: sem_acento(c).replace(" ", "_"))
    out["valor_brl"] = numeros(d.valor)
    out["valor_texto"] = d.valor
    return out


def quilometragem(lote: Lote) -> pd.DataFrame:
    d = lote.dados
    fator = {"m": 0.001, "km": 1.0}[lote.metadados.get("unidade_distancia", "km")]
    return pd.DataFrame({"veiculo_id": d.veiculo, "competencia": d.mes.map(competencia_de),
                         "km": numeros(d.distancia_m) * fator, "dias_operacao": numeros(d.dias_operacao),
                         "fonte_km": d.fonte, "_arquivo": d._arquivo, "_linha": d._linha})


def telemetria(lote: Lote) -> pd.DataFrame:
    d = lote.dados
    t = pd.DataFrame({"veiculo_id": d.veiculo_id, "competencia": d.competencia, "leitura": numeros(d.leitura),
                      "velocidade_kmh": numeros(d.velocidade_kmh), "rpm": numeros(d.rpm),
                      "temperatura_c": numeros(d.temperatura_c),
                      "nivel_combustivel_pct": numeros(d.nivel_combustivel_pct), "alertas": d.alertas,
                      "status": d.status, "_arquivo": d._arquivo, "_linha": d._linha})
    return t


NORMALIZADORES = {"combustivel": combustivel, "nfe_combustivel": nfe_combustivel, "pedagio": pedagio,
                  "manutencao": manutencao, "multas": multas, "financeiro": financeiro}


def normalizar(lotes: list[Lote]) -> dict[str, pd.DataFrame]:
    """Retorna as tabelas normalizadas: veiculos, custos, km e telemetria (ainda sem tratamento de qualidade)."""
    por_fonte = {}
    for lt in lotes:
        por_fonte.setdefault(lt.fonte, []).append(lt)
    custos = [NORMALIZADORES[f](lt) for f, lts in por_fonte.items() if f in NORMALIZADORES for lt in lts]
    tabelas = {
        "veiculos": pd.concat([cadastro(lt) for lt in por_fonte["cadastro"]], ignore_index=True),
        "custos": pd.concat(custos, ignore_index=True),
        "km": pd.concat([quilometragem(lt) for lt in por_fonte["quilometragem"]], ignore_index=True),
        "telemetria": pd.concat([telemetria(lt) for lt in por_fonte.get("telemetria", [])], ignore_index=True),
    }
    c = tabelas["custos"]
    for col in ("valor_brl", "litros", "preco_litro", "odometro_km"):
        c[col] = c[col].astype(float)
    c["data_evento"] = pd.to_datetime(c.data_evento)
    c["itens_negativos"] = c.itens_negativos.fillna(0).astype(int)
    return tabelas
