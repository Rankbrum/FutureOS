# Arquitetura do FutureOS

Atualizado em 2026-10-01. Status: **kernel M1, experimentos M2, auditoria M3, população M12 e planner opcional M13 implementados; demais camadas ampliadas continuam propostas**.

FutureOS é um laboratório de decisões. Sociedades de agentes exploram futuros possíveis condicionados a premissas explícitas. Os resultados não são previsões garantidas do mundo real.

Este documento descreve fronteiras e contratos de longo prazo. M1 materializa Agent, World, Event, Simulation, Snapshot, Branch, relações, memórias e métricas no pacote `futureos`. Simulation é o agregado de execução com configuração do modelo. M2 materializa ExperimentResult e o summary de SimulationRun como JSON tipado por validação, com runner, estatística e OAT em `experiments`/`sensitivity`; os demais conceitos continuam propostos. A presença de um diretório não significa funcionalidade. Consulte [CURRENT_STATE.md](CURRENT_STATE.md), [DECISIONS.md](DECISIONS.md), [SIMULATION_ENGINE.md](SIMULATION_ENGINE.md), [EXPERIMENTS.md](EXPERIMENTS.md) e [NEXT_STEPS.md](NEXT_STEPS.md).

## Princípios

1. O projeto deve ser compreensível e executável sem depender de Codex, Claude Code, Gemini ou outra ferramenta de desenvolvimento.
2. Comportamentos simples usam estado, regras e probabilidades. LLM é uma capacidade opcional, acionada por necessidade e sujeita a orçamento.
3. Branch Reality é um contrato do núcleo: bifurcar um estado íntegro, preservar sua origem e continuar universos sem contaminação entre eles.
4. Premissas, versões, aleatoriedade, intervenções e métricas fazem parte do experimento, não de contexto informal da conversa.
5. Começar em um processo, com módulos pequenos. Fronteiras lógicas não exigem microserviços, filas externas ou bancos especializados.
6. O controle científico acompanha o desenvolvimento do motor. Um relatório deve expor limitações e permitir contestar suas conclusões.

## Visão em camadas

```text
FutureOS
  Web Application                         apps/web
    FutureOS Core                         packages/core
      Experiment Engine                   packages/experiments
        Simulation Engine                 packages/simulation
          Population Engine               packages/population
            Agent Runtime                 packages/agents
              Memory + Relationships      packages/memory
              Behavioral Skills           skills/*
              LLM / MCP / Tools           contratos internos; adaptadores futuros

      Metrics + Scientific Audit          packages/analytics
```

Essa visão expressa responsabilidades, não uma cadeia obrigatória de chamadas. Métricas e auditoria recebem resultados do motor; população fornece o estado inicial; memória fornece o estado acessível aos agentes. Nenhum módulo do núcleo deve importar a interface web.

O primeiro caminho executável proposto é uma CLI local passando pelo Core. A aplicação web será um cliente posterior dos mesmos casos de uso.

## Harness de desenvolvimento e runtime do produto

O Harness Universal do desenvolvedor pode organizar contexto, tarefas, checkpoints de sessão, decisões e retomada de sessões. Esses checkpoints guardam resumos, não backups do código. Essa integração é operacional e deve manter o projeto compreensível por arquivos comuns.

O FutureOS Core coordena experimentos, execuções e persistência dos artefatos do produto. Ele não deve exigir os CLIs, hooks, memória privada ou serviços do Harness para simular. Um checkpoint de desenvolvimento não substitui um snapshot de uma sociedade simulada.

Uma eventual biblioteca do Harness só poderá ser reutilizada no produto depois de avaliar seu contrato, dependências e portabilidade. Não se presume que a integração operacional já forneça o motor de simulação.

## Módulos e diretórios existentes

| Local | Responsabilidade proposta | Limite |
| --- | --- | --- |
| `apps/web` | Criar e inspecionar experimentos, acompanhar execuções e comparar branches | Interface adiada; sem regras de simulação próprias |
| `packages/core` | Contratos compartilhados, IDs, versões, validação e coordenação dos casos de uso | Sem dependência de interface web ou ferramenta de desenvolvimento |
| `packages/experiments` | Hipóteses, cenários, protocolo, intervenções e critérios de comparação | Não executa o ciclo de cada agente |
| `packages/simulation` | Tempo lógico, ticks, eventos, snapshots, retomada e branches | Não presume um provedor de LLM |
| `packages/population` | Especificar e materializar população, atributos e relações iniciais | Registrar origem e limites da representatividade |
| `packages/agents` | Runtime de decisões, políticas, permissões e escalonamento seletivo para LLM | Não concede ferramentas externas implicitamente |
| `packages/memory` | Memórias dos agentes, relações, visibilidade e serialização desse estado | Memória do produto separada da memória de desenvolvimento |
| `packages/analytics` | Métricas, comparação de execuções e verificações científicas | Não transforma frequência sintética em certeza sobre o mundo real |
| `agents/citizen` | Especificação do papel Citizen | Comportamento sujeito às mesmas regras do runtime |
| `agents/influencer` | Especificação do papel Influencer | Alcance e influência são hipóteses declaradas |
| `agents/observer` | Especificação do papel Observer | Observação não altera silenciosamente o mundo |
| `agents/scientist` | Especificação do papel Scientist | Auditoria não modifica a execução auditada |
| `skills/behavior`, `skills/decision` | Políticas reutilizáveis de comportamento e decisão | Capacidades do produto; não confundidas com skills da IA desenvolvedora |
| `skills/influence`, `skills/persuasion`, `skills/trust` | Mecanismos sociais explícitos e versionados | Não presumir validade empírica por receberem um nome |
| `skills/validation` | Regras de validação e verificações reutilizáveis | Diagnósticos rastreáveis, com critérios definidos |
| `scenarios` | Definições de cenários e premissas | Separar dados sintéticos de dados observados |
| `simulations` | Configurações e protocolos de simulação | Não misturar definição com resultado de uma execução |
| `results` | Artefatos de execução: manifestos, métricas, relatórios e referências a snapshots | Política de retenção e versionamento a definir antes de gerar grandes volumes |
| `tests` | Invariantes do motor, replay, retomada, isolamento e contratos | Priorizar garantias comportamentais |
| `docs` | Arquitetura, decisões, estado, roteiro e continuidade | Atualizar quando a implementação ou decisão mudar |

Os contratos de providers ficam inicialmente no runtime de agentes; os contratos de persistência pertencem aos módulos que possuem o estado, coordenados pelo Core. A auditoria científica pertence a `packages/analytics`, com o papel Scientist descrito em `agents/scientist`. Criar pacotes separados para `providers`, `persistence` ou `science` só quando uma necessidade concreta justificar essa extração.

## Modelo de domínio

Os campos abaixo são requisitos conceituais; schemas concretos estão no núcleo e no protocolo M2, e não implementam automaticamente todos os requisitos ampliados.

| Entidade | Significado e contrato mínimo | Módulo responsável |
| --- | --- | --- |
| `Experiment` | Pergunta, hipótese, premissas, cenários, protocolo e critérios de comparação versionados | `experiments` |
| `Scenario` | Condições iniciais e mecanismos assumidos; origem dos dados e parâmetros | `experiments` |
| `Population` | Especificação da população e realização concreta de agentes e relações | `population` |
| `Agent` | Identidade, papel, atributos, estado, política e permissões | `agents` |
| `Memory` | Registro com conteúdo, origem, tempo lógico e escopo de acesso | `memory` |
| `Relationship` | Vínculo com direção ou simetria declarada, participantes, atributos e semântica | `memory` |
| `Event` | Ocorrência ordenada no tempo lógico, com origem, dados e causalidade | `simulation` |
| `World` | Estado completo do ambiente e referência ao estado social necessário para continuar a execução | `simulation` |
| `Simulation` | Definição executável do modelo: regras, políticas de tempo, eventos e configuração | `simulation` |
| `SimulationRun` | Execução concreta: cenário/população materializados, seed, versões, orçamento, branch e status | `simulation` |
| `Tick` | Transição atômica do tempo lógico com fases e ordenação declaradas | `simulation` |
| `Intervention` | Alteração exógena declarada, com alvo, parâmetros, instante e fase de aplicação | `experiments` |
| `Branch` | Linhagem derivada de snapshot imutável, com origem e intervenção próprias | `simulation` |
| `Metric` | Medida versionada com unidade, janela, denominador e regra de agregação | `analytics` |

Um experimento define as comparações; uma Simulation define como executar o modelo; uma SimulationRun registra uma realização concreta. Branch identifica a linhagem e não deve ser usado como sinônimo de uma repetição estatística. Repetições com seeds diferentes precisam ser identificadas explicitamente.

## Contratos mínimos entre módulos

- **Configuração:** validar cenários, unidades, políticas, orçamento, versões e parâmetros de intervenção antes de executar.
- **População:** materializar o estado inicial de forma rastreável, com IDs estáveis e seed explícita quando houver amostragem.
- **Decisão:** receber observações permitidas e devolver uma intenção validável; acesso a memória ou ferramentas passa por contratos explícitos.
- **Transição:** aplicar intenções e eventos em ordem determinística, preservando invariantes do mundo.
- **Snapshot:** capturar estado íntegro após commit de tick, com versões e integridade verificável.
- **Branch:** partir de snapshot imutável e continuar com isolamento de estado e de aleatoriedade.
- **Provider:** devolver resposta estruturada, uso, status e referência ao registro da chamada; falhas e orçamento não podem gerar comportamento implícito.
- **Métricas:** calcular medidas pela definição versionada, sem alterar o mundo observado.
- **Auditoria:** produzir achados com evidência, gravidade e limitações; manter separadas observação e intervenção.

Detalhes de transição, aleatoriedade e snapshots estão em [SIMULATION_ENGINE.md](SIMULATION_ENGINE.md). Papéis e permissões dos agentes estão em [AGENTS.md](AGENTS.md).

## Branch Reality

Exemplo fornecido pelo Founder: sociedade no Dia 15, compartilhando o mesmo estado até esse ponto.

```text
Snapshot íntegro do Dia 15
  Universe A → preço R$ 99,90
  Universe B → preço R$ 70 + mensalidade
  Universe C → promoção
```

O valor da mensalidade de B e os parâmetros da promoção de C não foram definidos. Esse exemplo orienta o contrato de branching; não é uma configuração pronta para executar. O motor deve rejeitar intervenções incompletas até que seus parâmetros sejam fornecidos.

Cada universo continua independentemente. A comparação registra o mesmo horizonte, definições de métricas e condições de origem, além das diferenças introduzidas. Branches de um único estado não substituem repetições e análises de sensibilidade.

## Persistência e rastreabilidade

Manter definições versionadas, manifesto por execução, snapshots, registro de eventos relevantes, respostas externas incorporadas, métricas e relatórios. Um manifesto deve permitir recuperar configuração, seed, versões, linhagem, estado de execução e artefatos associados.

Snapshots e registros são contratos de dados antes de serem uma escolha de banco. Event sourcing completo, banco de grafos, embeddings, armazenamento distribuído e filas externas ficam adiados. O volume real e os padrões de acesso orientarão essas decisões.

O estado de agentes pertence ao experimento. Arquivos do Memory Core, histórico de conversas de desenvolvimento, credenciais e configurações privadas da máquina não são entradas automáticas da sociedade simulada.

## Stack e sequência de implementação

Python 3.13 com biblioteca padrão foi adotado e implementado em M1 (D010). Módulos físicos de `futureos` correspondem a contratos, validação, RNG, população, motor, codec/snapshots, branches e demo/CLI. A árvore `packages/*` permanece uma visão conceitual preservada, sem exigir um pacote por camada. Não há necessidade estabelecida de CrewAI, LangGraph ou equivalente.

A primeira entrega exercita execução, snapshot, retomada, branching e comparação com regras simples e zero chamadas externas. A demo autorizada usa 10 ticks + 20 após bifurcação, distinta do exemplo conceitual Dia 15 acima. Web, autenticação, billing, banco, providers e distribuição ficam para missões posteriores.

M2 executa uma origem por seed e continua branches em cópias completas. Analítica não modifica sociedades: agrega métricas finais, conserva valores por seed e compara pares elegíveis. Sensibilidade OAT define cenários/overrides novos antes da execução, preservando baseline e premissas. Estado de desenvolvimento, timings variáveis e memória dos agentes têm contratos separados. Relatórios em lote persistem resumos e hashes; snapshots completos continuam disponíveis no kernel M1.

## Auditoria M3 implementada

`RandomStreams` deriva seeds SHA-256 e reutiliza SplitMix64-v1. O engine-v2 separa população, eventos, decisões e interações; contexto de tick/agente/evento/par isola consumo sem manter estado crescente por stream. M1/M2 continuam no caminho legado; snapshots schema1 e schema2 são identificados explicitamente, sem migração silenciosa.

`Simulation.audit` é provenance de execução, separada da memória social. Summary retém frames com hashes de estado/agentes, métricas, unidade e denominador; trace acrescenta eventos, decisões, deltas e contribuições internas. Auditoria não consome RNG nem muda decisões ao alternar modo. Hashes incrementais e representação canônica permitem consultar trajetória e localizar diferenças de protocolo, tick, agente e registro. Snapshot M3 inclui auditoria; artefato compacto reexecuta o cenário por replay.

`audit_runs.py` materializa protocolo M3 versionado e manifesto por execução, sem reinterpretar summaries M2. Replay valida cenário/seed/configuração/versões; divergência exige origem exata e horizonte elegível. Mecanismos são provenance do algoritmo, sem causalidade real. Ver [AUDIT_TRAJECTORIES](AUDIT_TRAJECTORIES.md), D016–D018 e [M3_REPORT](M3_REPORT.md). Perfil 10/30/60 demonstra custo relevante do trace; cópias/retensão são uma próxima investigação proposta, sem otimização nesta entrega.

## População M12 e proposta M13 implementadas

`PopulationSpec`/`Archetype` são contratos únicos para manual, JSON e propostas LLM.
Traits são numéricos no archetype, com overrides de distribuições globais em
`trait_distributions`. Validator compartilhado rejeita traits/distribuições/campos
desconhecidos e tipos/weights/bounds inválidos. População usa largest remainder;
traits e relationships têm streams derivadas independentes. Helper externo monta
World com provenance e chama o construtor do engine existente com a root seed.

`LLMPopulationPlanner` importa o adapter M11 e os contratos/validador, sem importar
generator/engine. Retorna proposta validada com assumptions, warnings obrigatórios
e provenance allowlist. `population plan` salva JSON para revisão, sem gerar agentes
ou iniciar ticks. Depois da revisão, o chamador carrega JSON e gera explicitamente.
Planejamento real pode variar entre calls; spec validada + seed fixa é determinística.
Fake offline é genérico, sem inferência de dados reais. Providers reais, UI e calibração
continuam adiados. Contratos, limites e execução em [M13](M13_LLM_POPULATION_PLANNER.md),
D021–D023 e [M12.1](M12_1_SMOKE_RESULT.json).
