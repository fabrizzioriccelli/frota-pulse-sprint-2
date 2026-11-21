# Resultados da Sprint 2 (gerado automaticamente)

Todos os números abaixo foram calculados por `src/executar_pipeline.py` sobre **dados simulados** de três frotas fictícias. Não representam clientes reais da Sem Parar Empresas.

## 1. Qualidade

452 ocorrências: excluido 203, alerta 193, quarentena 23, imputado 20, corrigido 12, rejeitado 1. Detalhe em `relatorio_qualidade.md`.

## 2. Custo total por categoria (R$, competência na janela de análise)

| Empresa | Combustível | Manutenção | Pedágio | Multas | Impostos | Outros | Total |
|---|---|---|---|---|---|---|---|
| EMP-A | 55.654 | 4.901 | 3.340 | 0 | 0 | 42.231 | 106.126 |
| EMP-B | 1.350.894 | 481.994 | 194.408 | 6.654 | 78.441 | 220.407 | 2.332.798 |
| EMP-C | 11.484.017 | 3.345.445 | 795.126 | 4.188 | 268.977 | 658.847 | 16.556.600 |

## 3. Benchmark por grupo

| Grupo | n (custo) | R$/km média | R$/km mediana | R$/km Q1–Q3 | km/L mediana | km/L Q1–Q3 | Referência válida |
|---|---|---|---|---|---|---|---|
| Leve mista (utilitário) | 8 | 1,926 | 1,410 | 1,348 a 2,646 | 9,34 | 9,20 a 9,43 | sim |
| Leve urbana (automóvel) | 2 | 0,672 | 0,672 | 0,664 a 0,679 | 11,50 | 11,25 a 11,82 | não (n < 5) |
| Leve urbana (utilitário) | 1 | 0,947 | 0,947 | 0,947 a 0,947 | 8,79 | 8,79 a 8,79 | não (n < 5) |
| Média mista (VUC) | 10 | 1,891 | 1,855 | 1,746 a 2,016 | 6,36 | 5,85 a 6,62 | sim |
| Média mista (caminhão toco) | 12 | 2,160 | 2,145 | 2,111 a 2,255 | 4,58 | 4,40 a 4,74 | sim |
| Pesada rodoviária (cavalo mecânico) | 28 | 3,675 | 3,694 | 3,543 a 3,834 | 2,39 | 2,26 a 2,57 | sim |
| Pesada rodoviária (truck) | 12 | 2,586 | 2,535 | 2,461 a 2,743 | 3,56 | 3,16 a 3,73 | sim |

Dispersão dos gaps entre veículos semelhantes: mediana do gap absoluto de custo por km = 4,3%, de consumo = 4,8%; percentil 90 do gap de custo = 12,7%, de consumo = 9,8%. Esses valores sustentam os limites de 5% (atenção) e 15% (ineficiente).

## 4. Diagnóstico por regras

Eficiente: 44, Atenção: 20, Sem referência: 8, Ineficiente: 6.

| Veículo | Grupo | Nível | Pior gap % | Justificativa |
|---|---|---|---|---|
| B-V28 | Leve mista (utilitário) | Ineficiente | 121,9 | custo por km +121,9% em relação à mediana do grupo; consumo 0,9% melhor que a mediana; categoria com maior gap: outros; baixa utilização: km abaixo de 25% da mediana do grupo, o custo fixo pesa em poucos km |
| B-V29 | Leve mista (utilitário) | Ineficiente | 112,2 | custo por km +112,2% em relação à mediana do grupo; consumo 1,1% pior que a mediana; categoria com maior gap: outros; baixa utilização: km abaixo de 25% da mediana do grupo, o custo fixo pesa em poucos km |
| B-V30 | Leve mista (utilitário) | Ineficiente | 79,4 | custo por km +79,4% em relação à mediana do grupo; consumo 0,7% pior que a mediana; categoria com maior gap: outros; baixa utilização: km abaixo de 25% da mediana do grupo, o custo fixo pesa em poucos km |
| B-V02 | Média mista (VUC) | Ineficiente | 18,7 | custo por km +18,7% em relação à mediana do grupo; consumo 10,0% pior que a mediana; categoria com maior gap: manutenção |
| C-V30 | Pesada rodoviária (truck) | Ineficiente | 15,7 | custo por km +15,7% em relação à mediana do grupo; consumo 12,7% pior que a mediana; categoria com maior gap: combustível |
| B-V01 | Média mista (VUC) | Ineficiente | 15,5 | custo por km +15,5% em relação à mediana do grupo; consumo 3,8% melhor que a mediana; categoria com maior gap: manutenção |
| C-V38 | Pesada rodoviária (truck) | Atenção | 13,6 | custo por km +13,6% em relação à mediana do grupo; consumo 12,2% pior que a mediana; categoria com maior gap: combustível |
| C-V33 | Pesada rodoviária (truck) | Atenção | 13,6 | custo por km +8,4% em relação à mediana do grupo; consumo 13,6% pior que a mediana; categoria com maior gap: combustível |
| B-V19 | Média mista (caminhão toco) | Atenção | 12,7 | custo por km -0,8% em relação à mediana do grupo; consumo 12,7% pior que a mediana; categoria com maior gap: combustível |
| C-V10 | Pesada rodoviária (cavalo mecânico) | Atenção | 12,6 | custo por km +12,6% em relação à mediana do grupo; consumo 8,1% pior que a mediana; categoria com maior gap: manutenção |
| C-V32 | Pesada rodoviária (truck) | Atenção | 10,7 | custo por km +8,1% em relação à mediana do grupo; consumo 10,7% pior que a mediana; categoria com maior gap: combustível |
| B-V06 | Média mista (VUC) | Atenção | 10,3 | custo por km -0,2% em relação à mediana do grupo; consumo 10,3% pior que a mediana; categoria com maior gap: combustível |
| B-V05 | Média mista (VUC) | Atenção | 10,1 | custo por km +10,1% em relação à mediana do grupo; consumo 9,5% pior que a mediana; categoria com maior gap: combustível |
| C-V07 | Pesada rodoviária (cavalo mecânico) | Atenção | 9,8 | custo por km +4,5% em relação à mediana do grupo; consumo 9,8% pior que a mediana; categoria com maior gap: combustível |
| B-V11 | Média mista (caminhão toco) | Atenção | 8,8 | custo por km +8,8% em relação à mediana do grupo; consumo 1,5% melhor que a mediana; categoria com maior gap: manutenção |
| B-V15 | Média mista (caminhão toco) | Atenção | 8,1 | custo por km -0,7% em relação à mediana do grupo; consumo 8,1% pior que a mediana; categoria com maior gap: combustível |
| C-V22 | Pesada rodoviária (cavalo mecânico) | Atenção | 8,0 | custo por km +1,4% em relação à mediana do grupo; consumo 8,0% pior que a mediana; categoria com maior gap: combustível |
| B-V21 | Média mista (caminhão toco) | Atenção | 7,3 | custo por km +7,3% em relação à mediana do grupo; consumo 8,4% melhor que a mediana; categoria com maior gap: manutenção |
| B-V12 | Média mista (caminhão toco) | Atenção | 7,1 | custo por km +7,1% em relação à mediana do grupo; consumo 2,7% melhor que a mediana; categoria com maior gap: manutenção |
| C-V03 | Pesada rodoviária (cavalo mecânico) | Atenção | 7,1 | custo por km +5,4% em relação à mediana do grupo; consumo 7,1% pior que a mediana; categoria com maior gap: combustível |
| C-V19 | Pesada rodoviária (cavalo mecânico) | Atenção | 7,0 | custo por km +4,4% em relação à mediana do grupo; consumo 7,0% pior que a mediana; categoria com maior gap: combustível |
| C-V05 | Pesada rodoviária (cavalo mecânico) | Atenção | 5,9 | custo por km +1,8% em relação à mediana do grupo; consumo 5,9% pior que a mediana; categoria com maior gap: combustível |
| C-V02 | Pesada rodoviária (cavalo mecânico) | Atenção | 5,4 | custo por km +4,3% em relação à mediana do grupo; consumo 5,4% pior que a mediana; categoria com maior gap: combustível |
| C-V21 | Pesada rodoviária (cavalo mecânico) | Atenção | 5,4 | custo por km +4,1% em relação à mediana do grupo; consumo 5,4% pior que a mediana; categoria com maior gap: combustível |
| B-V17 | Média mista (caminhão toco) | Atenção | 5,2 | custo por km +2,0% em relação à mediana do grupo; consumo 5,2% pior que a mediana; categoria com maior gap: combustível |
| C-V09 | Pesada rodoviária (cavalo mecânico) | Atenção | 5,1 | custo por km +3,4% em relação à mediana do grupo; consumo 5,1% pior que a mediana; categoria com maior gap: combustível |

## 5. Modelo supervisionado

Alvo: consumo do mês mais de 5% pior que a mediana do grupo (alvo adotado). 835 veículo-mês; treino 585 (49 veículos), teste 250 (21 veículos). Proporção da classe positiva no teste: 26,4%. Linha de base (sempre prever a classe majoritária): 73,6%.

| Modelo | Acurácia teste | Acurácia balanceada | Precisão (acima) | Recall (acima) |
|---|---|---|---|---|
| arvore decisao | 82,8% | 79,6% | 65,8% | 72,7% |
| regressao logistica | 84,8% | 84,3% | 67,1% | 83,3% |
| floresta aleatoria | 83,2% | 83,2% | 64,0% | 83,3% |

Matriz de confusão da árvore (teste): verdadeiros negativos 159, falsos positivos 25, falsos negativos 18, verdadeiros positivos 48.

**Experimento 1 (descartado):** alvo = regra mensal completa: pior gap de custo por km ou de consumo acima de 15%. Acurácia da árvore no teste 44,0% contra linha de base 72,8%: a telemetria não antecipa custos de manutenção, pedágio e custo fixo.

Regras aprendidas pela árvore:

```
|--- pct_marcha_lenta <= 10.8
|   |--- pct_excesso_velocidade <= 7.5
|   |   |--- pct_rpm_acima_verde <= 28.4
|   |   |   |--- class: 0
|   |   |--- pct_rpm_acima_verde >  28.4
|   |   |   |--- class: 0
|   |--- pct_excesso_velocidade >  7.5
|   |   |--- idade_anos <= 6.5
|   |   |   |--- class: 1
|   |   |--- idade_anos >  6.5
|   |   |   |--- class: 0
|--- pct_marcha_lenta >  10.8
|   |--- pct_rpm_acima_verde <= 30.3
|   |   |--- pct_marcha_lenta <= 15.9
|   |   |   |--- class: 0
|   |   |--- pct_marcha_lenta >  15.9
|   |   |   |--- class: 1
|   |--- pct_rpm_acima_verde >  30.3
|   |   |--- grupo_LEVE_MISTA_UTILITARIO <= 0.5
|   |   |   |--- class: 1
|   |   |--- grupo_LEVE_MISTA_UTILITARIO >  0.5
|   |   |   |--- class: 0
```

## 6. Regras x modelo (veículos de teste)

Concordância: 18 de 21 veículos (86%).

| Veículo | Regras | Modelo | Meses | Meses consumo ruim (real) | (previstos) | Interpretação |
|---|---|---|---|---|---|---|
| B-V05 | Atenção | Condução ineficiente | 12 | 10 | 10 | Concordam: desvio com componente de condução; investigar hábitos de direção e consumo |
| B-V08 | Eficiente | Condução dentro do padrão | 10 | 1 | 2 | Concordam: dentro da referência nas duas leituras |
| B-V09 | Eficiente | Condução dentro do padrão | 12 | 0 | 2 | Concordam: dentro da referência nas duas leituras |
| B-V12 | Atenção | Condução dentro do padrão | 12 | 0 | 0 | Divergem: as regras apontam desvio, mas a telemetria não mostra condução ruim; causa provável: custo de manutenção |
| B-V14 | Eficiente | Condução dentro do padrão | 12 | 2 | 4 | Concordam: dentro da referência nas duas leituras |
| B-V15 | Atenção | Condução ineficiente | 12 | 11 | 8 | Concordam: desvio com componente de condução; investigar hábitos de direção e consumo |
| B-V20 | Eficiente | Condução dentro do padrão | 12 | 0 | 1 | Concordam: dentro da referência nas duas leituras |
| B-V23 | Eficiente | Condução dentro do padrão | 12 | 1 | 0 | Concordam: dentro da referência nas duas leituras |
| B-V29 | Ineficiente | Condução dentro do padrão | 12 | 2 | 0 | Divergem: as regras apontam desvio, mas a telemetria não mostra condução ruim; causa provável: baixa utilização (custo fixo em poucos km) |
| C-V03 | Atenção | Condução ineficiente | 12 | 10 | 10 | Concordam: desvio com componente de condução; investigar hábitos de direção e consumo |
| C-V06 | Eficiente | Condução dentro do padrão | 12 | 0 | 2 | Concordam: dentro da referência nas duas leituras |
| C-V11 | Eficiente | Condução dentro do padrão | 12 | 0 | 0 | Concordam: dentro da referência nas duas leituras |
| C-V12 | Eficiente | Condução dentro do padrão | 12 | 0 | 0 | Concordam: dentro da referência nas duas leituras |
| C-V14 | Eficiente | Condução dentro do padrão | 12 | 0 | 5 | Concordam: dentro da referência nas duas leituras |
| C-V17 | Eficiente | Condução dentro do padrão | 12 | 0 | 2 | Concordam: dentro da referência nas duas leituras |
| C-V21 | Atenção | Condução dentro do padrão | 12 | 5 | 4 | Divergem: as regras apontam desvio, mas a telemetria não mostra condução ruim; causa provável: custo de combustível |
| C-V25 | Eficiente | Condução dentro do padrão | 12 | 1 | 2 | Concordam: dentro da referência nas duas leituras |
| C-V30 | Ineficiente | Condução ineficiente | 12 | 11 | 7 | Concordam: desvio com componente de condução; investigar hábitos de direção e consumo |
| C-V31 | Eficiente | Condução dentro do padrão | 12 | 0 | 1 | Concordam: dentro da referência nas duas leituras |
| C-V33 | Atenção | Condução ineficiente | 12 | 12 | 11 | Concordam: desvio com componente de condução; investigar hábitos de direção e consumo |
| C-V35 | Eficiente | Condução dentro do padrão | 12 | 0 | 2 | Concordam: dentro da referência nas duas leituras |
