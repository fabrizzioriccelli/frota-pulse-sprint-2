#!/usr/bin/env python3
"""Exporta a massa sintética da Sprint 1 para os formatos em que os dados chegariam do cliente (Sprint 2).

Cada fonte imita um sistema diferente, com nomes de colunas, separadores, formatos de data e unidades próprios:

  data/raw/cadastro/cadastro_frota.csv               CSV ","  cadastro da frota (sistema de gestão)
  data/raw/combustivel/abastecimentos_cartao.csv     CSV ";"  extrato do cartão-combustível, decimal com vírgula
  data/raw/combustivel/abastecimentos_cartao_reenvio_EMP-B_2026-03.csv   o mesmo extrato de mar/2026, reenviado
  data/raw/combustivel/notas_fiscais_combustivel.json   JSON  NF-e de combustível (mesmas compras do cartão)
  data/raw/pedagio/extrato_tag_<empresa>.txt         TXT     extrato da tag de pedágio, campos separados por " | "
  data/raw/manutencao/ordens_servico.json            JSON    ordens de serviço das oficinas, com itens aninhados
  data/raw/multas/notificacoes_multas.json           JSON    notificações e pagamentos de multas
  data/raw/financeiro/lancamentos_erp.csv            CSV ","  lançamentos do ERP: impostos, seguro e outros
  data/raw/operacao/quilometragem_telematica.json    JSON    quilometragem mensal, em METROS

Além dos problemas já injetados na Sprint 1 (duplicidades, sinal invertido, data futura, veículo desconhecido...),
este script injeta problemas típicos de integração entre formatos. Todos ficam registrados em
data/raw/gabarito_inconsistencias_sprint2.csv, usado nos testes para conferir se o pipeline os encontra.

Uso:
    python src/simulacao/gerar_fontes_brutas.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from frota_pulse.config import BRUTOS, SEMENTE, SINTETICO  # noqa: E402

rng = np.random.default_rng(SEMENTE)
gabarito: list[dict] = []


def anotar(tipo: str, arquivo: str, registro: str, descricao: str) -> None:
    gabarito.append({"tipo": tipo, "arquivo": arquivo, "registro": registro, "descricao": descricao})


def br(v: float, casas: int = 2) -> str:
    """Número no formato brasileiro, sem separador de milhar (como exportam os extratos)."""
    return f"{v:.{casas}f}".replace(".", ",")


def data_br(iso: str) -> str:
    """'2025-07-02T14:05' -> '02/07/2025 14:05'."""
    d, _, h = iso.partition("T")
    a, m, dd = d.split("-")
    return f"{dd}/{m}/{a}" + (f" {h}" if h else "")


def carregar() -> dict[str, pd.DataFrame]:
    nomes = ["veiculos", "frotas", "categorias_veiculo", "despesas", "abastecimentos", "manutencoes", "pedagios",
             "multas", "tributos", "seguros", "uso_veiculo_mensal", "origens_dados", "gabarito_registros"]
    return {n: pd.read_csv(SINTETICO / f"{n}.csv") for n in nomes}


def cadastro(t: dict) -> None:
    v = (t["veiculos"].merge(t["frotas"], on="frota_id").merge(t["categorias_veiculo"], on="categoria_id"))
    out = pd.DataFrame({
        "codigo_veiculo": v.veiculo_id, "empresa": v.empresa_id, "codigo_frota": v.frota_id, "frota": v.nome, "categoria": v.categoria_id,
        "porte": v.classe_peso, "modalidade_operacional": v.modalidade_operacional, "ano_fabricacao": v.ano_fabricacao,
        "propriedade": v.propriedade, "combustivel": v.combustivel_padrao, "capacidade_tanque_l": v.capacidade_tanque_l,
        "eixos": v.eixos, "possui_tag": v.possui_tag_pedagio.map({True: "sim", False: "nao"}), "situacao": v.status,
    })
    dup = out[out.codigo_veiculo == "B-V05"]
    out = pd.concat([out, dup]).sort_values("codigo_veiculo", kind="stable")
    anotar("registro_duplicado", "cadastro/cadastro_frota.csv", "B-V05", "Veículo cadastrado duas vezes (mesma linha)")
    caminho = BRUTOS / "cadastro" / "cadastro_frota.csv"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(caminho, index=False)


def combustivel(t: dict) -> None:
    d = t["despesas"].query("categoria_custo == 'COMBUSTIVEL'").merge(t["abastecimentos"], on="despesa_id", how="left")
    d["data_hora"] = d.data_hora.fillna(d.data_evento + "T12:00")  # estornos não têm hora no extrato
    d["combustivel"] = d.combustivel.fillna("")
    g01 = set(t["gabarito_registros"].query("cenario_id == 'G01'").registro_id)
    g11 = set(t["gabarito_registros"].query("cenario_id == 'G11'").registro_id)
    notas_fiscais(d[d.despesa_id.isin(g11)])
    d = d[~d.despesa_id.isin(g11)]
    linhas = []
    for r in d.sort_values(["data_hora", "despesa_id"]).itertuples():
        linhas.append({
            "ID_TRANSACAO": r.despesa_id, "TIPO_LANCAMENTO": "ESTORNO" if r.subcategoria == "estorno_ajuste_preco"
            else "COMPRA", "DATA_HORA": data_br(r.data_hora), "VEICULO": r.veiculo_id or "",
            "PRODUTO": {"gasolina": "GASOLINA COMUM", "diesel_s10": "DIESEL S10", "diesel_s500": "DIESEL S500",
                        "etanol": "ETANOL", "": "AJUSTE DE PRECO"}.get(r.combustivel, str(r.combustivel).upper()),
            "LITROS": "" if pd.isna(r.litros) else br(r.litros, 2),
            "PRECO_LITRO": "" if pd.isna(r.preco_litro) else br(r.preco_litro, 3),
            "VALOR_TOTAL": br(r.valor_brl, 2), "ODOMETRO_KM": "" if pd.isna(r.odometro_km) else f"{r.odometro_km:.0f}",
            "POSTO": r.posto_codigo if isinstance(r.posto_codigo, str) else "",
            "REDE_CONVENIADA": "S" if r.posto_rede_negociada is True else "N",
            "_g01": r.despesa_id in g01, "_empresa": r.empresa_id,
        })
    df = pd.DataFrame(linhas)
    df["VEICULO"] = df.VEICULO.fillna("")
    principal = df[~df._g01].copy()
    # Datas inválidas, veículo vazio e valores em centavos (problemas de exportação do sistema do cartão)
    idx = principal.index.to_numpy()
    escolhidos = rng.choice(idx, 9, replace=False)
    for i, ruim in zip(escolhidos[:3], ["31/02/2026 10:15", "00/01/2026 08:40", "2026-14-03 17:20"]):
        anotar("data_invalida", "combustivel/abastecimentos_cartao.csv", principal.at[i, "ID_TRANSACAO"],
               f"Data '{ruim}' não existe no calendário")
        principal.at[i, "DATA_HORA"] = ruim
    for i in escolhidos[3:5]:
        anotar("campo_obrigatorio_vazio", "combustivel/abastecimentos_cartao.csv", principal.at[i, "ID_TRANSACAO"],
               "Veículo em branco")
        principal.at[i, "VEICULO"] = ""
    emp_a = principal[(principal._empresa == "EMP-A") & (principal.LITROS != "")].index.to_numpy()
    for i in rng.choice(emp_a, 4, replace=False):
        anotar("unidade_incompativel", "combustivel/abastecimentos_cartao.csv", principal.at[i, "ID_TRANSACAO"],
               "Preço e valor exportados em centavos (100 vezes o valor em reais)")
        for c in ("PRECO_LITRO", "VALOR_TOTAL"):
            principal.at[i, c] = br(float(principal.at[i, c].replace(",", ".")) * 100, 2 if c == "VALOR_TOTAL" else 1)
    colunas = [c for c in df.columns if not c.startswith("_")]
    pasta = BRUTOS / "combustivel"
    pasta.mkdir(parents=True, exist_ok=True)
    principal[colunas].to_csv(pasta / "abastecimentos_cartao.csv", sep=";", index=False)
    reenvio = df[df._g01]
    reenvio[colunas].to_csv(pasta / "abastecimentos_cartao_reenvio_EMP-B_2026-03.csv", sep=";", index=False)
    anotar("arquivo_reenviado", "combustivel/abastecimentos_cartao_reenvio_EMP-B_2026-03.csv", "(arquivo inteiro)",
           f"{len(reenvio)} transações de mar/2026 da EMP-B já presentes no extrato principal")


def notas_fiscais(d: pd.DataFrame) -> None:
    """NF-e de combustível recebidas por e-mail: a mesma compra também aparece no extrato do cartão."""
    notas = [{"chave_nfe": r.descricao_original.split()[1], "id_lancamento": r.despesa_id, "veiculo": r.veiculo_id,
              "emissao": r.data_hora, "produto": "OLEO DIESEL B S10" if r.combustivel == "diesel_s10" else "GASOLINA C",
              "quantidade_l": r.litros, "valor_unitario": r.preco_litro, "valor_total": r.valor_brl}
             for r in d.sort_values("despesa_id").itertuples()]
    caminho = BRUTOS / "combustivel" / "notas_fiscais_combustivel.json"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps({"origem": "NF-e recebidas por e-mail", "notas": notas}, ensure_ascii=False,
                                  indent=1), encoding="utf-8")


def pedagio(t: dict) -> None:
    d = t["despesas"].merge(t["pedagios"], on="despesa_id", how="inner")
    d = d[d.subcategoria != "pedagio_manual_reembolso"]  # reembolsos manuais vêm pelo ERP
    for emp, g in d.groupby("empresa_id"):
        nome = f"pedagio/extrato_tag_{emp}.txt"
        linhas = [f"EXTRATO DE UTILIZAÇÃO - TAG DE PEDÁGIO - CLIENTE {emp}",
                  f"PERÍODO: {data_br(g.data_hora.min())[:10]} A {data_br(g.data_hora.max())[:10]}",
                  "TRANSACAO | DATA_HORA | VEICULO | CONCESSIONARIA | PRACA | EIXOS | PAGADOR | VALOR", "-" * 96]
        g = g.sort_values(["data_hora", "despesa_id"]).reset_index(drop=True)
        vazios = set(rng.choice(len(g), 2, replace=False)) if emp == "EMP-B" else set()
        quebrada = int(rng.integers(len(g))) if emp == "EMP-C" else -1
        for i, r in g.iterrows():
            pagador = "EMBARCADOR (VALE-PEDAGIO)" if r.natureza_custo == "custeado_terceiro" else "PROPRIO"
            valor = "" if i in vazios else f"R$ {br(r.valor_brl)}"
            if i in vazios:
                anotar("campo_obrigatorio_vazio", nome, r.despesa_id, "Valor da passagem em branco")
            campos = [r.despesa_id, data_br(r.data_hora), r.veiculo_id or "", r.concessionaria_codigo, r.praca_codigo,
                      str(int(r.eixos_cobrados)), pagador, valor]
            if i == quebrada:
                anotar("linha_ilegivel", nome, r.despesa_id, "Linha truncada: separadores perdidos na exportação")
                linhas.append(" ".join(campos[:5]))
            else:
                linhas.append(" | ".join(campos))
        linhas += ["-" * 96, f"TOTAL DE TRANSAÇÕES: {len(g)}"]
        caminho = BRUTOS / nome
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def manutencao(t: dict) -> None:
    d = t["despesas"].merge(t["manutencoes"], on="despesa_id")
    ordens = []
    for r in d.sort_values(["data_evento", "despesa_id"]).itertuples():
        pecas = round(r.valor_brl * 0.6, 2)
        itens = [{"descricao": "Peças e materiais", "valor": pecas},
                 {"descricao": "Mão de obra", "valor": round(r.valor_brl - pecas, 2)}]
        ordens.append({"numero_os": r.despesa_id, "veiculo": r.veiculo_id, "data_entrada": r.data_evento,
                       "tipo_servico": r.subcategoria.replace("_", " "), "natureza": r.tipo, "programada": bool(r.programada),
                       "sistema": r.sistema, "odometro_km": None if pd.isna(r.odometro_km) else int(r.odometro_km),
                       "oficina": r.oficina_codigo, "dias_parado": int(r.dias_parado), "itens": itens})
    i = int(rng.integers(len(ordens)))
    anotar("veiculo_inexistente", "manutencao/ordens_servico.json", ordens[i]["numero_os"],
           f"Veículo B-V99 não existe no cadastro (original {ordens[i]['veiculo']})")
    ordens[i]["veiculo"] = "B-V99"
    j = int(rng.integers(len(ordens)))
    anotar("valor_negativo", "manutencao/ordens_servico.json", ordens[j]["numero_os"],
           "Item de mão de obra com sinal invertido")
    ordens[j]["itens"][1]["valor"] = -abs(ordens[j]["itens"][1]["valor"])
    caminho = BRUTOS / "manutencao" / "ordens_servico.json"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps({"fonte": "portal das oficinas credenciadas", "ordens": ordens}, ensure_ascii=False,
                                  indent=1), encoding="utf-8")


def multas(t: dict) -> None:
    d = t["despesas"].merge(t["multas"], on="despesa_id")
    regs = [{"auto_infracao": r.auto_infracao_token, "id_lancamento": r.despesa_id, "veiculo": r.veiculo_id,
             "tipo": "NIC (não indicação do condutor)" if r.tipo_multa == "nic" else "Infração de trânsito",
             "gravidade": r.gravidade, "data_notificacao": r.data_notificacao, "valor_original": r.valor_original,
             "valor_pago": r.valor_brl, "data_pagamento": r.data_pagamento if isinstance(r.data_pagamento, str) else None,
             "situacao": r.situacao} for r in d.sort_values("despesa_id").itertuples()]
    caminho = BRUTOS / "multas" / "notificacoes_multas.json"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(regs, ensure_ascii=False, indent=1), encoding="utf-8")


def financeiro(t: dict) -> None:
    d = t["despesas"]
    d = d[d.categoria_custo.isin(["TRIBUTO", "SEGURO", "OUTROS"]) | (d.subcategoria == "pedagio_manual_reembolso")]
    trib = t["tributos"].set_index("despesa_id")
    seg = t["seguros"].set_index("despesa_id")
    frotas = t["frotas"].set_index("empresa_id").frota_id
    contas = {"ipva": "IPVA", "licenciamento": "Licenciamento anual", "apolice_frota": "Seguro frota",
              "parcela_apolice_frota": "Seguro frota - parcela", "locacao_veiculo": "Locação de veículo",
              "lavagem": "Lavagem", "estacionamento": "Estacionamento", "telemetria": "Serviço de rastreamento",
              "pedagio_manual_reembolso": "Reembolso de pedágio pago em dinheiro"}
    linhas = []
    for r in d.sort_values(["data_evento", "despesa_id"]).itertuples():
        hist = contas[r.subcategoria]
        if r.despesa_id in trib.index:
            x = trib.loc[r.despesa_id]
            hist += f" {x.exercicio} parcela {x.parcela}/{x.total_parcelas}"
        if r.despesa_id in seg.index:
            hist += f" apólice {seg.loc[r.despesa_id].apolice_token}"
        ci, cf = r.competencia_inicio, r.competencia_fim
        linhas.append({"documento": r.despesa_id, "data_lancamento": r.data_evento, "conta": contas[r.subcategoria],
                       "historico": hist, "centro_custo": r.veiculo_id if isinstance(r.veiculo_id, str)
                       else frotas[r.empresa_id], "valor": f"{r.valor_brl:.2f}",
                       "competencia_inicial": f"{ci[5:]}/{ci[:4]}", "competencia_final": f"{cf[5:]}/{cf[:4]}"})
    df = pd.DataFrame(linhas)
    for i in rng.choice(len(df), 2, replace=False):
        anotar("data_invalida", "financeiro/lancamentos_erp.csv", df.at[i, "documento"], "Competência inicial '13/2025'")
        df.at[i, "competencia_inicial"] = "13/2025"
    k = int(rng.integers(len(df)))
    anotar("registro_duplicado", "financeiro/lancamentos_erp.csv", df.at[k, "documento"], "Lançamento repetido")
    df = pd.concat([df, df.iloc[[k]]]).sort_values(["data_lancamento", "documento"], kind="stable")
    caminho = BRUTOS / "financeiro" / "lancamentos_erp.csv"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho, index=False, quoting=csv.QUOTE_MINIMAL)


def quilometragem(t: dict) -> None:
    u = t["uso_veiculo_mensal"].sort_values(["veiculo_id", "competencia"]).reset_index(drop=True)
    regs = [{"veiculo": r.veiculo_id, "mes": r.competencia,
             "distancia_m": None if r.status_valor != "OBSERVADO" else int(round(r.km_rodados * 1000)),
             "dias_operacao": int(r.dias_em_operacao), "fonte": r.fonte_km} for r in u.itertuples()]
    ok = [i for i, r in enumerate(regs) if r["distancia_m"]]
    a, b = rng.choice(ok, 2, replace=False)
    anotar("unidade_incompativel", "operacao/quilometragem_telematica.json", f"{regs[a]['veiculo']}|{regs[a]['mes']}",
           "Distância enviada em milímetros (1.000 vezes o valor em metros)")
    regs[a]["distancia_m"] *= 1000
    anotar("valor_negativo", "operacao/quilometragem_telematica.json", f"{regs[b]['veiculo']}|{regs[b]['mes']}",
           "Distância negativa")
    regs[b]["distancia_m"] = -regs[b]["distancia_m"]
    caminho = BRUTOS / "operacao" / "quilometragem_telematica.json"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps({"provedor": "telemática embarcada", "unidade_distancia": "m", "registros": regs},
                                  ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> None:
    t = carregar()
    for f in (cadastro, combustivel, pedagio, manutencao, multas, financeiro, quilometragem):
        f(t)
    pd.DataFrame(gabarito).to_csv(BRUTOS / "gabarito_inconsistencias_sprint2.csv", index=False)
    arquivos = sorted(p.relative_to(BRUTOS).as_posix() for p in BRUTOS.rglob("*") if p.is_file())
    print(f"ok: {len(arquivos)} arquivos em data/raw; {len(gabarito)} inconsistências novas registradas")
    for a in arquivos:
        print("  ", a)


if __name__ == "__main__":
    main()
