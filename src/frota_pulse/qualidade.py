"""Etapa 3 — Qualidade: verifica os dados normalizados, aplica o tratamento de cada problema e registra tudo.

Princípios:
  * nada é apagado em silêncio: cada problema vira uma linha no relatório (tipo, regra, arquivo, linha, registro,
    campo, valor encontrado, tratamento e justificativa);
  * os dados originais ficam intactos em data/raw; o resultado tratado vai para data/processed;
  * tratamentos possíveis, do mais leve ao mais forte:
      ALERTA      o registro é mantido como veio, mas o problema é sinalizado;
      IMPUTADO    um campo vazio é preenchido por regra determinística (litros = valor / preço);
      CORRIGIDO   um valor é corrigido quando a correção é verificável por outro campo do mesmo registro;
      QUARENTENA  o registro fica fora dos indicadores até revisão humana;
      EXCLUIDO    o registro é duplicata de outro já considerado;
      REJEITADO   a linha não pôde ser interpretada na leitura.
Os códigos Q01 a Q16 estão descritos em docs/metodologia.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DATA_REFERENCIA, KM_DIA_MAXIMO, PRECO_LITRO, TOLERANCIA_TANQUE, TOLERANCIA_VALOR
from .ingestao import Lote

ORDEM_TRATAMENTO = ["OK", "ALERTA", "IMPUTADO", "CORRIGIDO", "QUARENTENA", "EXCLUIDO"]
TIPOS = {
    "registro_duplicado": "Registro duplicado",
    "valor_negativo": "Valor negativo indevido",
    "campo_obrigatorio_vazio": "Campo obrigatório vazio",
    "veiculo_inexistente": "Veículo inexistente no cadastro",
    "data_invalida": "Data inválida",
    "unidade_incompativel": "Valor incompatível com a unidade",
    "dado_incoerente": "Dado incoerente",
    "linha_ilegivel": "Linha ilegível",
}


class Registro:
    """Acumula as ocorrências de qualidade e aplica o tratamento mais forte a cada registro."""

    def __init__(self):
        self.ocorrencias: list[dict] = []

    def anotar(self, df: pd.DataFrame, mascara: pd.Series, tabela: str, regra: str, tipo: str, campo: str,
               tratamento: str, justificativa: str, valor: pd.Series | None = None) -> int:
        alvo = df[mascara]
        if alvo.empty:
            return 0
        valores = (valor if valor is not None else alvo[campo] if campo in alvo else pd.Series("", index=alvo.index))
        for i, r in alvo.iterrows():
            self.ocorrencias.append({
                "tabela": tabela, "regra": regra, "tipo": tipo, "descricao_tipo": TIPOS[tipo],
                "arquivo": r.get("_arquivo", ""), "linha": r.get("_linha", ""),
                "registro": r.get("registro_id", r.get("veiculo_id", "")) if tabela != "km" else
                f"{r.veiculo_id}|{r.competencia}", "campo": campo, "valor_encontrado": _texto(valores.get(i, "")),
                "tratamento": tratamento, "justificativa": justificativa})
        if "status_qualidade" in df:
            atual = df.loc[mascara, "status_qualidade"].map(ORDEM_TRATAMENTO.index)
            novo = ORDEM_TRATAMENTO.index(tratamento) if tratamento in ORDEM_TRATAMENTO else 0
            df.loc[mascara, "status_qualidade"] = [ORDEM_TRATAMENTO[max(a, novo)] for a in atual]
            df.loc[mascara, "motivos"] = (df.loc[mascara, "motivos"] + ";" + regra).str.strip(";")
        return int(mascara.sum())

    def tabela(self) -> pd.DataFrame:
        cols = ["id", "tabela", "regra", "tipo", "descricao_tipo", "arquivo", "linha", "registro", "campo",
                "valor_encontrado", "tratamento", "justificativa"]
        df = pd.DataFrame(self.ocorrencias)
        if df.empty:
            return pd.DataFrame(columns=cols)
        df.insert(0, "id", [f"QA-{i:05d}" for i in range(1, len(df) + 1)])
        return df[cols]


def _texto(v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    return str(v)


def _faixa_preco(produto: pd.Series) -> tuple[pd.Series, pd.Series]:
    lo = produto.map(lambda p: PRECO_LITRO.get(p, (np.nan, np.nan))[0])
    hi = produto.map(lambda p: PRECO_LITRO.get(p, (np.nan, np.nan))[1])
    return lo, hi


def _perto(a: pd.Series, b: pd.Series, tol: float = TOLERANCIA_VALOR) -> pd.Series:
    return (a - b).abs() <= tol * b.abs()


# ---------------------------------------------------------------- cadastro

def verificar_cadastro(v: pd.DataFrame, reg: Registro) -> pd.DataFrame:
    v = v.copy()
    v["status_qualidade"], v["motivos"] = "OK", ""
    dup = v.duplicated("veiculo_id", keep="first")
    reg.anotar(v, dup, "cadastro", "Q01", "registro_duplicado", "veiculo_id", "EXCLUIDO",
               "Mesmo veículo cadastrado mais de uma vez; mantida a primeira linha (as demais são idênticas)")
    return v


# ---------------------------------------------------------------- custos

def verificar_custos(c: pd.DataFrame, veiculos: pd.DataFrame, reg: Registro) -> pd.DataFrame:
    c = c.copy()
    c["status_qualidade"], c["motivos"] = "OK", ""
    for col in ("valor_brl", "litros", "preco_litro"):
        c[f"{col}_original"] = c[col]
    cad = veiculos.drop_duplicates("veiculo_id").set_index("veiculo_id")

    # Q01 duplicidade: mesmo identificador de transação na mesma fonte (arquivo reenviado, linha repetida)
    dup = c.duplicated(["fonte", "registro_id"], keep="first")
    origem = c[~dup].set_index(["fonte", "registro_id"])
    primeira = [f"{origem.loc[(f, r), '_arquivo']}:{origem.loc[(f, r), '_linha']}"
                for f, r in zip(c.loc[dup, "fonte"], c.loc[dup, "registro_id"])]
    reg.anotar(c, dup, "custos", "Q01", "registro_duplicado", "registro_id", "EXCLUIDO",
               "Transação já lida em outro registro; somá-la duplicaria o custo",
               valor=pd.Series(primeira, index=c.index[dup]).radd("já presente em "))

    # Q01 duplicidade por conteúdo: mesmo veículo, data e hora, valor e litros em mais de um arquivo do cartão
    # (o reenvio de um extrato chega com identificadores novos, então o identificador não basta)
    conteudo = ["veiculo_id", "data_texto", "valor_texto", "litros"]
    eh_cartao = c.fonte.eq("combustivel") & ~dup
    dup_c = eh_cartao & c[eh_cartao].duplicated(conteudo, keep="first").reindex(c.index, fill_value=False)
    base_c = c[eh_cartao & ~dup_c].drop_duplicates(conteudo).set_index(conteudo)
    primeira = [f"{base_c.loc[tuple(k), '_arquivo']}:{base_c.loc[tuple(k), '_linha']}"
                for k in c.loc[dup_c, conteudo].itertuples(index=False)]
    reg.anotar(c, dup_c, "custos", "Q01", "registro_duplicado", "registro_id", "EXCLUIDO",
               "Mesma transação (veículo, data e hora, valor e litros) já lida em outro arquivo: arquivo reenviado",
               valor=pd.Series(primeira, index=c.index[dup_c]).radd("já presente em "))
    dup = dup | dup_c

    # Q02 conciliação NF-e x cartão: a mesma compra aparece nas duas fontes
    nfe = c[(c.fonte == "nfe_combustivel") & ~dup]
    cartao = c[(c.fonte == "combustivel") & ~dup].assign(dia=lambda d: d.data_evento.dt.date)
    chave: dict[tuple, list[float]] = {}
    for vv, dia, valor in zip(cartao.veiculo_id, cartao.dia, cartao.valor_brl):
        chave.setdefault((vv, dia), []).append(valor)
    conciliada = pd.Series(False, index=c.index)
    for i, r in nfe.iterrows():
        k = (r.veiculo_id, r.data_evento.date() if pd.notna(r.data_evento) else None)
        conciliada[i] = any(abs(x - r.valor_brl) <= 0.01 * abs(r.valor_brl) for x in chave.get(k, []))
    reg.anotar(c, conciliada, "custos", "Q02", "registro_duplicado", "registro_id", "EXCLUIDO",
               "NF-e da mesma compra já registrada no extrato do cartão (mesmo veículo, dia e valor): conciliar, não somar")

    # Q03 campos obrigatórios
    vazio_valor = c.valor_brl.isna()
    reg.anotar(c, vazio_valor, "custos", "Q03", "campo_obrigatorio_vazio", "valor_brl", "QUARENTENA",
               "Sem valor não há custo a considerar; o registro aguarda o valor correto", valor=c.valor_texto)
    vazio_veic = c.veiculo_id.isna() & c.centro_custo.isna()
    reg.anotar(c, vazio_veic, "custos", "Q03", "campo_obrigatorio_vazio", "veiculo_id", "QUARENTENA",
               "Sem veículo o custo não pode ser atribuído nem comparado")

    # Q04 veículo inexistente
    inexistente = c.veiculo_id.notna() & ~c.veiculo_id.isin(cad.index)
    reg.anotar(c, inexistente, "custos", "Q04", "veiculo_inexistente", "veiculo_id", "QUARENTENA",
               "Veículo ausente do cadastro (agregado, cartão emprestado ou erro de digitação); confirmar com o gestor")

    # Q05 datas
    sem_data = c.data_evento.isna()
    reg.anotar(c, sem_data, "custos", "Q05", "data_invalida", "data_evento", "QUARENTENA",
               "Texto que não corresponde a uma data do calendário", valor=c.data_texto)
    sem_comp = c.competencia_inicio.isna() | c.competencia_fim.isna()
    reg.anotar(c, sem_comp & ~sem_data, "custos", "Q05", "data_invalida", "competencia", "QUARENTENA",
               "Competência inexistente (mês fora de 01 a 12); sem ela o custo não pode ser rateado",
               valor=c.competencia_inicio.fillna("(inválida)"))
    futura = c.data_evento > pd.Timestamp(DATA_REFERENCIA)
    reg.anotar(c, futura, "custos", "Q05", "data_invalida", "data_evento", "QUARENTENA",
               f"Data posterior ao recebimento dos arquivos ({DATA_REFERENCIA}); provável erro de digitação do ano",
               valor=c.data_texto)

    # Q06 valores negativos (estorno identificado pelo tipo de lançamento é legítimo)
    negativo = (c.valor_brl < 0) & (c.tipo_lancamento != "ESTORNO")
    reg.anotar(c, negativo, "custos", "Q06", "valor_negativo", "valor_brl", "QUARENTENA",
               "Valor negativo em lançamento de compra; o sinal não pode ser corrigido sem confirmar com a origem")
    itens = c.itens_negativos > 0
    reg.anotar(c, itens, "custos", "Q06", "valor_negativo", "itens", "QUARENTENA",
               "Ordem de serviço com item de valor negativo: o total da ordem fica subestimado",
               valor=c.itens_negativos.astype(str) + " item(ns)")

    comb = c.categoria.eq("COMBUSTIVEL") & c.tipo_lancamento.ne("ESTORNO") & ~dup & ~conciliada
    lo, hi = _faixa_preco(c.produto)

    # Q07 preço por litro fora da faixa: tenta corrigir a escala (casa decimal ou centavos), se verificável
    fora = comb & c.preco_litro.notna() & ((c.preco_litro < lo) | (c.preco_litro > hi))
    corr_preco = pd.Series(False, index=c.index)
    corr_ambos = pd.Series(False, index=c.index)
    for f in (10, 100):
        p = c.preco_litro / f
        dentro = fora & ~corr_preco & ~corr_ambos & p.between(lo, hi)
        so_preco = dentro & _perto(c.valor_brl, c.litros * p)
        ambos = dentro & ~so_preco & _perto(c.valor_brl / f, c.litros * p)
        c.loc[so_preco, "preco_litro"] = p[so_preco]
        c.loc[ambos, "preco_litro"] = p[ambos]
        c.loc[ambos, "valor_brl"] = c.valor_brl[ambos] / f
        corr_preco |= so_preco
        corr_ambos |= ambos
    reg.anotar(c, corr_preco, "custos", "Q07", "unidade_incompativel", "preco_litro", "CORRIGIDO",
               "Preço com casa decimal deslocada; corrigido porque litros x preço corrigido reproduz o valor total",
               valor=c.preco_litro_original)
    reg.anotar(c, corr_ambos, "custos", "Q07", "unidade_incompativel", "valor_brl", "CORRIGIDO",
               "Preço e valor exportados em centavos; divididos por 100 (o preço resultante fica na faixa do produto)",
               valor=c.valor_brl_original)
    reg.anotar(c, fora & ~corr_preco & ~corr_ambos, "custos", "Q07", "unidade_incompativel", "preco_litro",
               "QUARENTENA", "Preço fora da faixa plausível do produto sem correção verificável")

    # Q08 volume acima da capacidade do tanque: corrige se litros/10 bate com valor/preço
    tanque = c.veiculo_id.map(cad.capacidade_tanque_l)
    acima = comb & (c.litros > tanque * TOLERANCIA_TANQUE)
    corr_l = acima & _perto(c.litros / 10, c.valor_brl / c.preco_litro, 0.03)
    c.loc[corr_l, "litros"] = c.litros[corr_l] / 10
    reg.anotar(c, corr_l, "custos", "Q08", "unidade_incompativel", "litros", "CORRIGIDO",
               "Volume acima do tanque; separador decimal perdido (litros/10 = valor/preço)", valor=c.litros_original)
    reg.anotar(c, acima & ~corr_l, "custos", "Q08", "unidade_incompativel", "litros", "QUARENTENA",
               "Volume acima da capacidade do tanque sem correção verificável")

    # Q09 litros ausentes com valor e preço presentes: imputação determinística
    imputar = comb & c.litros.isna() & c.valor_brl.gt(0) & c.preco_litro.gt(0)
    c.loc[imputar, "litros"] = (c.valor_brl / c.preco_litro)[imputar].round(2)
    reg.anotar(c, imputar, "custos", "Q09", "campo_obrigatorio_vazio", "litros", "IMPUTADO",
               "Litros ausentes; calculados como valor / preço (regra IMP-01 da Sprint 1)")

    # Q10 valor x litros x preço não confere (após as correções)
    confere = comb & c.litros.notna() & c.preco_litro.notna() & c.valor_brl.gt(0)
    diverge = confere & ~_perto(c.valor_brl, c.litros * c.preco_litro) & ~c.status_qualidade.isin(["QUARENTENA"])
    reg.anotar(c, diverge, "custos", "Q10", "dado_incoerente", "valor_brl", "ALERTA",
               "Valor total diferente de litros x preço (acima de 2%); mantido o valor cobrado")

    # Q11 combustível incompatível com o veículo
    esperado = c.veiculo_id.map(cad.combustivel)
    incompat = comb & esperado.notna() & c.produto.ne("ajuste") & (c.produto != esperado)
    reg.anotar(c, incompat, "custos", "Q11", "dado_incoerente", "produto", "QUARENTENA",
               "Combustível diferente do cadastrado para o veículo (erro de cadastro ou uso indevido do cartão)",
               valor=c.produto + " (cadastro: " + esperado.fillna("") + ")")

    # Q12 odômetro menor que o do abastecimento anterior: custo mantido, odômetro ignorado
    validos = comb & c.odometro_km.notna() & c.data_evento.notna() & ~c.status_qualidade.isin(["QUARENTENA"])
    od = c[validos].sort_values(["veiculo_id", "data_evento"])
    regressivo = od.odometro_km < od.groupby("veiculo_id").odometro_km.shift(1)
    mask = pd.Series(False, index=c.index)
    mask[regressivo[regressivo].index] = True
    reg.anotar(c, mask, "custos", "Q12", "dado_incoerente", "odometro_km", "ALERTA",
               "Odômetro menor que o de um abastecimento anterior; custo mantido, odômetro não usado")

    # Q13 possível cobrança duplicada de pedágio (mesma praça, mesmo valor, até 10 minutos)
    ped = c[c.categoria.eq("PEDAGIO") & c.local.notna() & ~dup].sort_values(["veiculo_id", "local", "data_evento"])
    mesma = (ped.veiculo_id.eq(ped.veiculo_id.shift()) & ped.local.eq(ped.local.shift())
             & ped.valor_brl.eq(ped.valor_brl.shift())
             & (ped.data_evento - ped.data_evento.shift()).le(pd.Timedelta(minutes=10)))
    mask = pd.Series(False, index=c.index)
    mask[mesma[mesma].index] = True
    reg.anotar(c, mask, "custos", "Q13", "registro_duplicado", "valor_brl", "ALERTA",
               "Duas passagens na mesma praça em até 10 minutos: provável cobrança duplicada; custo mantido como "
               "cobrado e sinalizado para contestação")
    return c


# ---------------------------------------------------------------- quilometragem e telemetria

def verificar_km(km: pd.DataFrame, veiculos: pd.DataFrame, reg: Registro) -> pd.DataFrame:
    km = km.copy()
    km["status_qualidade"], km["motivos"] = "OK", ""
    km["km_original"] = km.km
    cad = veiculos.drop_duplicates("veiculo_id").set_index("veiculo_id")
    sem = km.km.isna()
    reg.anotar(km, sem, "km", "Q14", "campo_obrigatorio_vazio", "km", "ALERTA",
               "Quilometragem não informada no mês; indicadores por km desse mês não são calculados")
    neg = km.km < 0
    reg.anotar(km, neg, "km", "Q15", "valor_negativo", "km", "QUARENTENA", "Distância negativa")
    limite = km.veiculo_id.map(cad.classe_peso).map(KM_DIA_MAXIMO)
    absurdo = (km.km / km.dias_operacao) > limite
    reg.anotar(km, absurdo, "km", "Q15", "unidade_incompativel", "km", "QUARENTENA",
               "Quilometragem por dia de operação acima do limite físico da categoria; provável erro de unidade")
    inexistente = ~km.veiculo_id.isin(cad.index)
    reg.anotar(km, inexistente, "km", "Q04", "veiculo_inexistente", "veiculo_id", "QUARENTENA",
               "Veículo ausente do cadastro")
    km.loc[km.status_qualidade.eq("QUARENTENA"), "km"] = np.nan
    return km


def verificar_telemetria(t: pd.DataFrame, veiculos: pd.DataFrame, reg: Registro) -> pd.DataFrame:
    t = t.copy()
    t["status_qualidade"], t["motivos"] = "OK", ""
    t["registro_id"] = t.veiculo_id + "|" + t.competencia + "|" + t.leitura.astype(int).astype(str)
    incoerente = t.alertas.str.contains("SENSOR_INCOERENTE", na=False)
    reg.anotar(t, incoerente, "telemetria", "Q16", "dado_incoerente", "rpm", "ALERTA",
               "Rotação zerada com o veículo em movimento (falha do sinal); a rotação dessa leitura não entra nas médias")
    t.loc[incoerente, "rpm"] = np.nan
    inexistente = ~t.veiculo_id.isin(veiculos.veiculo_id)
    reg.anotar(t, inexistente, "telemetria", "Q04", "veiculo_inexistente", "veiculo_id", "QUARENTENA",
               "Dispositivo associado a veículo fora do cadastro")
    return t


def verificar_rejeitadas(lotes: list[Lote], reg: Registro) -> None:
    for lt in lotes:
        for r in lt.rejeitadas:
            reg.ocorrencias.append({
                "tabela": lt.fonte, "regra": "Q00", "tipo": "linha_ilegivel", "descricao_tipo": TIPOS["linha_ilegivel"],
                "arquivo": lt.arquivo, "linha": r["_linha"], "registro": r["conteudo"].split()[0], "campo": "(linha)",
                "valor_encontrado": r["conteudo"][:80], "tratamento": "REJEITADO",
                "justificativa": f"Linha fora do leiaute do extrato ({r['motivo']}); mantida no relatório para "
                                 "solicitar o reenvio"})


def verificar(lotes: list[Lote], tabelas: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    reg = Registro()
    verificar_rejeitadas(lotes, reg)
    veiculos = verificar_cadastro(tabelas["veiculos"], reg)
    validos = veiculos[veiculos.status_qualidade != "EXCLUIDO"]
    tratadas = {
        "veiculos": veiculos,
        "custos": verificar_custos(tabelas["custos"], validos, reg),
        "km": verificar_km(tabelas["km"], validos, reg),
        "telemetria": verificar_telemetria(tabelas["telemetria"], validos, reg),
    }
    return tratadas, reg.tabela()


def resumo_por_arquivo(lotes: list[Lote], ocorrencias: pd.DataFrame) -> pd.DataFrame:
    base = pd.DataFrame([{"arquivo": lt.arquivo, "formato": lt.formato, "registros_lidos": lt.registros}
                         for lt in lotes])
    cont = ocorrencias.groupby("arquivo").size().rename("ocorrencias")
    trat = ocorrencias.pivot_table(index="arquivo", columns="tratamento", values="id", aggfunc="count", fill_value=0)
    return base.set_index("arquivo").join(cont).join(trat).fillna(0).astype(
        {c: int for c in ["ocorrencias", *trat.columns]}).reset_index()
