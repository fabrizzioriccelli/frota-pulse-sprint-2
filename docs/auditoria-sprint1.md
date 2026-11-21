# Auditoria da Sprint 1 e aderência à Sprint 2

Antes de começar a Sprint 2, o [repositório da Sprint 1](https://github.com/fabrizzioriccelli/1TIAO-ENTERPRISE-CHALLENGE-) foi inspecionado arquivo por arquivo: estrutura, scripts, bases, documentação, diagramas e histórico. Esta matriz registra o que foi encontrado e o que foi feito na Sprint 2. A regra foi **preservar o que estava correto e evoluir o necessário**. A Sprint 1 continua no repositório dela, sem alterações; este repositório traz só a Sprint 2, e os caminhos de arquivo da seção 1 se referem ao repositório da Sprint 1. A massa simulada da Sprint 1 foi copiada para `data/sintetico/`, porque é a origem dos arquivos brutos desta Sprint.

## 1. O que a Sprint 1 entregou

| Item | Situação encontrada | Evidência |
|---|---|---|
| Especificação do produto, User Stories, arquitetura e LGPD | Concluído como planejamento | `docs/*.md` (problema, user-stories, solucao, arquitetura, seguranca-lgpd, roadmap) |
| Massa sintética de 3 frotas fictícias (78 veículos, 21.656 despesas, 34 cenários com gabarito) | Funcional e reprodutível | `src/gerar_dados_sinteticos.py`, `data/sintetico/` |
| Dicionário de dados (181 campos) | Completo | `data/dicionario-dados.csv` |
| Regras de qualidade R-* e cálculos de exemplo | Implementados como demonstração sobre a massa interna (formato único, já estruturado) | `src/calculos.py`, `src/exemplos_calculados.py` |
| Leitura de arquivos em formatos diferentes | **Só planejada** | `docs/ingestao-qualidade.md` |
| Telemetria e ESP32 | **Ausente** | - |
| Benchmark por grupos com gaps | **Parcial**: comparação com pares em exemplos isolados | `docs/benchmarks.md`, anexo de exemplos |
| Diagnóstico em níveis e Machine Learning | **Só planejados** (IA-03 em `docs/estrategia-ia.md`) | - |
| Testes automatizados | Validador de entregáveis (documentação e dados), sem testes de código | `src/validar_entregaveis.py` |

## 2. Matriz de aderência

| Componente | Situação na Sprint 1 | Necessidade da Sprint 2 | Ação tomada |
|---|---|---|---|
| Arquitetura | Monólito modular proposto, com camadas de dados, análise e interface | Fluxo funcional local, com módulos separados | **Preservada e evoluída**: o pacote `src/frota_pulse/` implementa as camadas de ingestão, qualidade, análise e diagnóstico ([arquitetura](arquitetura.md)) |
| Ingestão de dados | Formatos descritos, nenhum leitor | Ler CSV, TXT e JSON | **Implementada**: `ingestao.py` lê 12 arquivos em 3 formatos, com arquivo e linha de origem em cada registro |
| Normalização | Regras de padronização descritas | Colunas, categorias, datas, unidades e ausentes padronizados | **Implementada**: `normalizacao.py` (seis categorias, competência AAAA-MM, metros para km, centavos para reais) |
| Qualidade | 13 regras R-* sobre a massa interna | Verificações sobre os arquivos de entrada, com relatório rastreável | **Evoluída**: 17 regras Q00 a Q16 sobre as fontes brutas; os códigos R-* da Sprint 1 aparecem como referência na metodologia |
| Integração | Modelo conceitual com veículo e competência como chaves | Cadastro, custos e telemetria pela mesma chave | **Implementada**: `integracao.py` gera a base veículo-mês, com rateio por competência |
| Telemetria ESP32 | Ausente | Simulação no Wokwi, anomalias e CSV | **Criada**: `src/esp32/` (firmware, projeto Wokwi, compilação nativa) e `data/telemetria/` |
| Benchmark | Hierarquia de referências e regras de comparabilidade (BEN-01 a BEN-08) | Grupos comparáveis, média, mediana, quartis e gaps com direção | **Implementado** seguindo as regras da Sprint 1: grupo por porte, operação e categoria; locados fora do custo total (BEN-03) |
| Machine Learning | Componente IA-03 proposto | Classificação supervisionada com treino, teste e avaliação | **Implementado**: árvore de decisão sobre a telemetria ([machine-learning](machine-learning.md)) |
| Diagnóstico | Taxonomia de evidência e indicadores IND-01 a IND-12 | Níveis Eficiente, Atenção e Ineficiente por regras | **Implementado**: `diagnostico.py`, com limites justificados pela distribuição dos gaps |
| Economia em R$ e recomendações | Metodologia completa especificada | **Fora da Sprint 2** (objetivo da Sprint 3) | **Preservada** como especificação, sem implementação nesta Sprint |
| Documentação | 20 documentos da Sprint 1 | README no novo template, metodologia e evidências | **Evoluída**: repositório próprio para a Sprint 2, com README no template 2026; a Sprint 1 fica no [repositório dela](https://github.com/fabrizzioriccelli/1TIAO-ENTERPRISE-CHALLENGE-) |
| Testes | Validador de entregáveis | Testes de código e do fluxo completo | **Criados**: testes de código, do fluxo completo e da documentação em `tests/` ([testes](testes.md)) |

## 3. Decisões que mudaram algo da Sprint 1

| Decisão | Motivo |
|---|---|
| Seguro passa a ser subcategoria de **Outros** | A Sprint 2 pede seis categorias (combustível, manutenção, pedágio, multas, impostos e outros). A subcategoria é preservada, então nada se perde |
| Grupos de comparação sempre da mesma categoria de veículo | Na EMP-A, automóvel e utilitário rendem 11,5 e 8,8 km/L; juntá-los faria o utilitário parecer ineficiente só por ser utilitário |
| PDF e imagem ficam para a Sprint 3 | A Sprint 2 pede CSV, TXT e JSON; a extração de PDF e imagem já estava planejada para a Sprint 3 no roadmap |
| A massa da Sprint 1 vira a "verdade" da simulação | Os arquivos brutos da Sprint 2 são exportados a partir dela (`src/simulacao/gerar_fontes_brutas.py`), o que permite conferir o pipeline contra os dois gabaritos |

## 4. Conferência com a Sprint 1

O custo total da janela de análise calculado pelo pipeline da Sprint 2, a partir dos arquivos brutos, foi comparado com o indicador IND-01 da Sprint 1, calculado sobre a massa interna.

| Empresa | Sprint 1 (IND-01) | Sprint 2 (pipeline) | Diferença | Explicação |
|---|---|---|---|---|
| EMP-B | R$ 2.334.087,68 | R$ 2.332.798,38 | -0,06% | Ficam em quarentena: uma ordem de serviço de veículo inexistente (B-V99), dois pedágios sem valor, dois lançamentos do ERP com competência inválida e uma multa com data posterior à análise (R$ 1.209,59 mais os dois pedágios) |
| EMP-C | R$ 16.583.488,63 | R$ 16.556.600,10 | -0,16% | Registros que a Sprint 2 passou a isolar a partir das fontes brutas (datas inválidas, veículo em branco, ordem de serviço com item negativo) e diferenças de arredondamento do rateio |

As diferenças são pequenas e explicadas pelos registros que a Sprint 2 passou a isolar.
