# Relatório de qualidade dos dados

Gerado por `src/executar_pipeline.py`. Dados simulados. A lista completa, uma linha por ocorrência, está em `outputs/reports/relatorio_qualidade.csv`.

**Registros analisados:** 75.413 em 12 arquivos. **Ocorrências:** 452.

## Por arquivo de origem

| arquivo | formato | registros_lidos | ocorrencias | ALERTA | CORRIGIDO | EXCLUIDO | IMPUTADO | QUARENTENA | REJEITADO |
|---|---|---|---|---|---|---|---|---|---|
| data/raw/cadastro/cadastro_frota.csv | csv | 79 | 1 | 0 | 0 | 1 | 0 | 0 | 0 |
| data/raw/combustivel/abastecimentos_cartao.csv | csv | 7.737 | 52 | 6 | 12 | 0 | 20 | 14 | 0 |
| data/raw/combustivel/abastecimentos_cartao_reenvio_EMP-B_2026-03.csv | csv | 161 | 161 | 0 | 0 | 161 | 0 | 0 | 0 |
| data/raw/combustivel/notas_fiscais_combustivel.json | json | 40 | 40 | 0 | 0 | 40 | 0 | 0 | 0 |
| data/raw/pedagio/extrato_tag_EMP-A.txt | txt | 243 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| data/raw/pedagio/extrato_tag_EMP-B.txt | txt | 8.345 | 17 | 15 | 0 | 0 | 0 | 2 | 0 |
| data/raw/pedagio/extrato_tag_EMP-C.txt | txt | 3.311 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| data/raw/manutencao/ordens_servico.json | json | 1.540 | 2 | 0 | 0 | 0 | 0 | 2 | 0 |
| data/raw/multas/notificacoes_multas.json | json | 72 | 1 | 0 | 0 | 0 | 0 | 1 | 0 |
| data/raw/financeiro/lancamentos_erp.csv | csv | 977 | 3 | 0 | 0 | 1 | 0 | 2 | 0 |
| data/raw/operacao/quilometragem_telematica.json | json | 888 | 23 | 21 | 0 | 0 | 0 | 2 | 0 |
| data/telemetria/telemetria_esp32.csv | csv | 52.020 | 151 | 151 | 0 | 0 | 0 | 0 | 0 |

## Por tipo de inconsistência e tratamento

| descricao_tipo | regra | tratamento | ocorrencias |
|---|---|---|---|
| Campo obrigatório vazio | Q03 | QUARENTENA | 4 |
| Campo obrigatório vazio | Q09 | IMPUTADO | 20 |
| Campo obrigatório vazio | Q14 | ALERTA | 21 |
| Dado incoerente | Q11 | QUARENTENA | 2 |
| Dado incoerente | Q12 | ALERTA | 6 |
| Dado incoerente | Q16 | ALERTA | 151 |
| Data inválida | Q05 | QUARENTENA | 8 |
| Linha ilegível | Q00 | REJEITADO | 1 |
| Registro duplicado | Q01 | EXCLUIDO | 163 |
| Registro duplicado | Q02 | EXCLUIDO | 40 |
| Registro duplicado | Q13 | ALERTA | 15 |
| Valor incompatível com a unidade | Q07 | CORRIGIDO | 7 |
| Valor incompatível com a unidade | Q08 | CORRIGIDO | 5 |
| Valor incompatível com a unidade | Q15 | QUARENTENA | 1 |
| Valor negativo indevido | Q06 | QUARENTENA | 2 |
| Valor negativo indevido | Q15 | QUARENTENA | 1 |
| Veículo inexistente no cadastro | Q04 | QUARENTENA | 5 |

## Tratamento aplicado e justificativa

| regra | descricao_tipo | tratamento | justificativa |
|---|---|---|---|
| Q00 | Linha ilegível | REJEITADO | Linha fora do leiaute do extrato (1 campos; esperados 8); mantida no relatório para solicitar o reenvio |
| Q01 | Registro duplicado | EXCLUIDO | Mesmo veículo cadastrado mais de uma vez; mantida a primeira linha (as demais são idênticas) |
| Q01 | Registro duplicado | EXCLUIDO | Transação já lida em outro registro; somá-la duplicaria o custo |
| Q01 | Registro duplicado | EXCLUIDO | Mesma transação (veículo, data e hora, valor e litros) já lida em outro arquivo: arquivo reenviado |
| Q02 | Registro duplicado | EXCLUIDO | NF-e da mesma compra já registrada no extrato do cartão (mesmo veículo, dia e valor): conciliar, não somar |
| Q03 | Campo obrigatório vazio | QUARENTENA | Sem valor não há custo a considerar; o registro aguarda o valor correto |
| Q03 | Campo obrigatório vazio | QUARENTENA | Sem veículo o custo não pode ser atribuído nem comparado |
| Q04 | Veículo inexistente no cadastro | QUARENTENA | Veículo ausente do cadastro (agregado, cartão emprestado ou erro de digitação); confirmar com o gestor |
| Q05 | Data inválida | QUARENTENA | Texto que não corresponde a uma data do calendário |
| Q05 | Data inválida | QUARENTENA | Competência inexistente (mês fora de 01 a 12); sem ela o custo não pode ser rateado |
| Q05 | Data inválida | QUARENTENA | Data posterior ao recebimento dos arquivos (2026-07-10); provável erro de digitação do ano |
| Q06 | Valor negativo indevido | QUARENTENA | Ordem de serviço com item de valor negativo: o total da ordem fica subestimado |
| Q06 | Valor negativo indevido | QUARENTENA | Valor negativo em lançamento de compra; o sinal não pode ser corrigido sem confirmar com a origem |
| Q07 | Valor incompatível com a unidade | CORRIGIDO | Preço com casa decimal deslocada; corrigido porque litros x preço corrigido reproduz o valor total |
| Q07 | Valor incompatível com a unidade | CORRIGIDO | Preço e valor exportados em centavos; divididos por 100 (o preço resultante fica na faixa do produto) |
| Q08 | Valor incompatível com a unidade | CORRIGIDO | Volume acima do tanque; separador decimal perdido (litros/10 = valor/preço) |
| Q09 | Campo obrigatório vazio | IMPUTADO | Litros ausentes; calculados como valor / preço (regra IMP-01 da Sprint 1) |
| Q11 | Dado incoerente | QUARENTENA | Combustível diferente do cadastrado para o veículo (erro de cadastro ou uso indevido do cartão) |
| Q12 | Dado incoerente | ALERTA | Odômetro menor que o de um abastecimento anterior; custo mantido, odômetro não usado |
| Q13 | Registro duplicado | ALERTA | Duas passagens na mesma praça em até 10 minutos: provável cobrança duplicada; custo mantido como cobrado e sinalizado para contestação |
| Q14 | Campo obrigatório vazio | ALERTA | Quilometragem não informada no mês; indicadores por km desse mês não são calculados |
| Q15 | Valor negativo indevido | QUARENTENA | Distância negativa |
| Q15 | Valor incompatível com a unidade | QUARENTENA | Quilometragem por dia de operação acima do limite físico da categoria; provável erro de unidade |
| Q16 | Dado incoerente | ALERTA | Rotação zerada com o veículo em movimento (falha do sinal); a rotação dessa leitura não entra nas médias |

## Um exemplo de cada regra (registro afetado)

| id | regra | arquivo | linha | registro | campo | valor_encontrado | tratamento |
|---|---|---|---|---|---|---|---|
| QA-00001 | Q00 | data/raw/pedagio/extrato_tag_EMP-C.txt | 2729 | DSP-C-007372 | (linha) | DSP-C-007372 27/04/2026 11:56 C-V11 VARIAS CONSOLIDADO_VIAGEM | REJEITADO |
| QA-00002 | Q01 | data/raw/cadastro/cadastro_frota.csv | 15 | B-V05 | veiculo_id | B-V05 | EXCLUIDO |
| QA-00165 | Q02 | data/raw/combustivel/notas_fiscais_combustivel.json | 1 | NF-F90A3E | registro_id | NF-F90A3E | EXCLUIDO |
| QA-00205 | Q03 | data/raw/pedagio/extrato_tag_EMP-B.txt | 5378 | DSP-B-006936 | valor_brl |  | QUARENTENA |
| QA-00209 | Q04 | data/raw/combustivel/abastecimentos_cartao.csv | 48 | DSP-C-000754 | veiculo_id | C-V99 | QUARENTENA |
| QA-00214 | Q05 | data/raw/combustivel/abastecimentos_cartao.csv | 1560 | DSP-C-002082 | data_evento | 31/02/2026 10:15 | QUARENTENA |
| QA-00222 | Q06 | data/raw/combustivel/abastecimentos_cartao.csv | 7248 | DSP-C-009077 | valor_brl | -2685.45 | QUARENTENA |
| QA-00224 | Q07 | data/raw/combustivel/abastecimentos_cartao.csv | 2262 | DSP-C-002892 | preco_litro | 62.13 | CORRIGIDO |
| QA-00231 | Q08 | data/raw/combustivel/abastecimentos_cartao.csv | 1229 | DSP-C-000938 | litros | 3911.3 | CORRIGIDO |
| QA-00236 | Q09 | data/raw/combustivel/abastecimentos_cartao.csv | 223 | DSP-B-000823 | litros | 43.52 | IMPUTADO |
| QA-00256 | Q11 | data/raw/combustivel/abastecimentos_cartao.csv | 2906 | DSP-C-004036 | produto | gasolina (cadastro: diesel_s10) | QUARENTENA |
| QA-00258 | Q12 | data/raw/combustivel/abastecimentos_cartao.csv | 238 | DSP-C-000316 | odometro_km | 334715.0 | ALERTA |
| QA-00264 | Q13 | data/raw/pedagio/extrato_tag_EMP-B.txt | 1145 | DSP-B-011174 | valor_brl | 15.34 | ALERTA |
| QA-00279 | Q14 | data/raw/operacao/quilometragem_telematica.json | 7 | A-V02\|2025-10 | km |  | ALERTA |
| QA-00300 | Q15 | data/raw/operacao/quilometragem_telematica.json | 74 | B-V03\|2025-08 | km | -3616.0 | QUARENTENA |
| QA-00302 | Q16 | data/telemetria/telemetria_esp32.csv | 620 | A-V05\|2026-02\|19 | rpm | 0.0 | ALERTA |
