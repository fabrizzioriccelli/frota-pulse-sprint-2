# Testes e validação

Nenhum módulo foi considerado pronto só porque o código foi escrito. Esta página registra o que foi executado e os resultados obtidos.

## 1. Testes automatizados

Comando: `python -m pytest -v` (42 testes em `tests/`). Resultado da última execução: **42 aprovados, 0 falhas**.

| Área | Teste | O que garante |
|---|---|---|
| Leitura | `test_le_os_tres_formatos` | Os 12 arquivos são lidos, nos formatos CSV, TXT e JSON |
| | `test_cada_registro_guarda_arquivo_e_linha` | Todo registro sabe de que arquivo e linha veio |
| | `test_linha_truncada_do_txt_e_rejeitada_e_registrada` | A linha fora do leiaute não é descartada em silêncio |
| | `test_json_aninhado_vira_uma_linha_por_item_e_soma_por_ordem` | Itens de ordem de serviço são somados por ordem |
| Normalização | `test_numeros_em_formatos_diferentes` | "R$ 1.234,56", "1234.56" e vazio são interpretados corretamente |
| | `test_datas_sao_estritas` | "31/02/2026" não vira uma data válida |
| | `test_competencia`, `test_categorias_por_texto_livre` | Mês e categoria a partir de texto livre |
| | `test_todas_as_categorias_sao_as_seis_do_projeto` | Só existem as seis categorias pedidas |
| | `test_distancia_em_metros_vira_km` | Conversão de unidade |
| Qualidade | `test_nenhum_registro_e_apagado` | Os tratados têm o mesmo número de linhas que os normalizados |
| | `test_todas_as_inconsistencias_da_sprint2_sao_encontradas` | As 21 inconsistências injetadas são detectadas, com o tipo certo |
| | `test_problemas_da_sprint1_sao_encontrados` | Os cenários G01, G02, G10, G11, G14 a G20 são detectados pela regra esperada |
| | `test_estornos_legitimos_nao_sao_marcados` | Os estornos do cenário G33 (controle negativo) não geram ocorrência |
| | `test_quarentena_fica_fora_da_base` | Registro em quarentena ou excluído não entra nos indicadores |
| | `test_correcao_guarda_o_valor_original` | Toda correção preserva o valor de origem |
| | `test_relatorio_tem_os_campos_pedidos` | Tipo, arquivo, registro, tratamento e justificativa preenchidos |
| Cálculos | `test_divisao_por_zero_vira_nan` | Divisão por zero ou ausente não gera infinito |
| | `test_custo_por_km_e_consumo_conferidos_a_mao` | Custo por km e km/L recalculados a partir da base veículo-mês |
| | `test_participacoes_somam_100` | As participações das seis categorias somam 100% |
| | `test_ipva_anual_e_rateado_em_12_meses` | O rateio divide a parcela igualmente entre os meses |
| Benchmark | `test_direcao_do_gap_custo_menor_e_melhor` | Veículo 20% mais caro tem gap +20% |
| | `test_direcao_do_gap_consumo_maior_e_melhor` | Veículo que rende 20% menos tem gap +20% (pior), e não −20% |
| | `test_grupo_pequeno_nao_tem_referencia` | Grupos da EMP-A ficam sem referência |
| Regras | `test_limites_das_regras` | 5,00% é Eficiente, 5,01% é Atenção, 15,00% é Atenção, 15,01% é Ineficiente, ausente é Sem referência |
| | `test_custo_total_alto_nao_basta_para_ser_ineficiente` | O veículo de maior custo total não é classificado como ineficiente |
| | `test_baixa_utilizacao_e_explicada` | B-V28, B-V29 e B-V30 recebem a observação de baixa utilização |
| Modelo | `test_treino_e_teste_nao_compartilham_veiculos` | Sem vazamento entre treino e teste |
| | `test_atributos_nao_revelam_o_rotulo` | Nenhum atributo de custo, litros, km/L, preço, gap ou nível |
| | `test_modelo_supera_a_linha_de_base` | Acurácia acima de sempre prever a classe majoritária |
| | `test_resultado_reprodutivel`, `test_exemplos_tem_acertos_e_erros` | Mesmo resultado em nova execução; exemplos corretos e incorretos |
| Telemetria | `test_alertas_do_firmware_batem_com_os_limites_do_python` | Em cada uma das 52.020 leituras, os alertas do firmware conferem com os limites do Python |
| | `test_ha_leituras_normais_e_anormais` | Existem leituras NORMAL, ATENÇÃO e CRÍTICO |
| | `test_firmware_compila_e_gera_a_mesma_telemetria` | O firmware recompilado gera exatamente o CSV versionado |
| Fluxo completo | `test_pipeline_completo_gera_as_saidas` | O pipeline roda do início ao fim e grava bases, relatórios, gráficos e métricas |
| | `test_leituras_do_wokwi_iguais_as_da_compilacao_nativa` | As leituras do ESP32 no Wokwi são iguais, campo a campo, às da compilação nativa |
| Documentação | `test_readme_segue_o_template_2026`, `test_descricao_tem_ate_600_palavras` | Seções do template, FIAP NEXT, integrantes com RM, descrição em até 600 palavras |
| | `test_links_e_ancoras_internos_existem` | Todo link interno do README e de `docs/` aponta para um arquivo ou seção que existe |
| | `test_numeros_do_readme_conferem_com_as_saidas` | Ocorrências, níveis, acurácia e concordância citados no README são os gravados pelo pipeline |
| | `test_sem_dados_pessoais_ou_segredos` | Nenhum CPF, CNPJ, e-mail, chave ou token nos dados, no código e na documentação |

**Defeito encontrado pelos testes:** a primeira versão do firmware avaliava os limites com o valor completo, mas imprimia o valor arredondado. Uma leitura de 14,96% de combustível aparecia como "15.0" e com o alerta COMB_BAIXO, o que era incoerente no CSV. A leitura passou a ser arredondada antes da avaliação.

## 2. Conferências manuais

**Correção de unidade (regra Q07).** Linha do extrato: `DSP-A-000201;COMPRA;22/12/2025 06:24;A-V04;GASOLINA COMUM;34,27;620,3;21258,00;;POSTO-A004;N`. Preço de R$ 620,30 por litro está fora da faixa da gasolina (R$ 4,00 a R$ 9,50). Dividindo por 100: R$ 6,203 por litro e valor de R$ 212,58. Conferência: 34,27 L × R$ 6,203 = R$ 212,58. O pipeline registrou exatamente essa correção, guardando os valores originais.

**Custo por km e consumo (B-V23, leve mista).** Custo dos meses com km: R$ 39.800,17; km: 29.814,7. Custo por km = 39.800,17 ÷ 29.814,7 = R$ 1,335/km. Consumo = 29.814,7 km ÷ 3.151,55 L = 9,46 km/L.

**Gap com direção (B-V23).** Mediana do grupo: R$ 1,4105/km e 9,335 km/L. Gap de custo = (1,3349 − 1,4105) ÷ 1,4105 × 100 = −5,4% (melhor que o grupo). Gap de consumo = (9,335 − 9,460) ÷ 9,335 × 100 = −1,3% (melhor). Pior gap = −1,3%, que é menor ou igual a 5%: **Eficiente**, como o pipeline classificou.

**Conferência com a Sprint 1.** O custo total por empresa calculado a partir dos arquivos brutos difere do indicador IND-01 da Sprint 1 em −0,06% (EMP-B) e −0,16% (EMP-C), diferença explicada pelos registros em quarentena ([auditoria](auditoria-sprint1.md#4-conferência-com-a-sprint-1)).

## 3. Situações excepcionais verificadas

| Situação | Comportamento |
|---|---|
| Mês sem quilometragem | Custo do mês não entra no custo por km; ocorrência Q14 |
| Veículo sem nenhum km no período (A-V02 a A-V04) | Indicadores por km ausentes; nível "Sem referência" |
| Grupo com menos de 5 veículos comparáveis | Sem gap e sem nível; justificativa registrada |
| Veículo locado | Fora do custo total e das categorias embutidas na mensalidade; comparado em consumo |
| Divisão por zero | Resultado ausente, nunca infinito |
| Linha ilegível no TXT | Rejeitada e listada no relatório |
| Leitura de telemetria com falha de rotação | Rotação descartada nas médias; demais grandezas mantidas |

**Defeito encontrado no Wokwi:** a compilação real para o ESP32 falhou na primeira tentativa, porque o Arduino gera protótipos das funções antes de os tipos `Leitura` e `Simulacao` estarem declarados. A compilação nativa não acusava o erro. Os tipos foram movidos para `perfil.h` ([telemetria](telemetria-esp32.md#5-execução-no-wokwi)).

## 4. Execução no Wokwi

O firmware foi compilado e simulado no wokwi.com, com os quatro alertas provocados pelos controles do circuito e os três perfis do modo ROTEIRO. Resultado, capturas, gravação e Monitor Serial: [telemetria, seção 5](telemetria-esp32.md#5-execução-no-wokwi).

**Limite que permanece:** o projeto não foi gravado numa placa ESP32 física, e todos os testes usam dados simulados.

## 5. Como reproduzir

```bash
python -m pytest -v                                        # 42 testes
python src/executar_pipeline.py                            # fluxo completo
node src/esp32/wokwi/executar_no_wokwi.js /tmp/wokwi       # execução no Wokwi (Node.js e Playwright)
```
