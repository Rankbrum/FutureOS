# FutureOS

FutureOS é um laboratório de decisões: sociedades sintéticas exploram futuros condicionados às premissas. Os resultados não são previsões garantidas.

Repositório: [Rankbrum/FutureOS](https://github.com/Rankbrum/FutureOS), público na última verificação. O núcleo usa somente a biblioteca padrão; `apps/api` e `apps/web` são protótipos posteriores, com endpoints ainda incompletos e Flask não declarado como dependência. Consulte o [estado atual](docs/CURRENT_STATE.md) antes de usar a demo web.

## Estado

Kernel M1, experimentos M2, auditoria M3, população determinística M12 e planner opcional M13 implementados em Python 3.13, somente biblioteca padrão. **243 testes passaram em 2026-10-01**. M13 propõe PopulationSpec via adapter M11/FakeLLMProvider, valida e salva JSON para revisão humana; a simulação continua sem LLM. Providers reais não estão conectados. Consulte [estado verificado](docs/CURRENT_STATE.md) e [relatório M13](docs/M13_LLM_POPULATION_PLANNER.md).

## Executar

Na raiz, com Python 3.13:

```powershell
python -m futureos
python -m futureos --seed 2026 --output results/demo
python -m futureos --seed 2026 --json
python -m futureos experiment --scenario scenarios/kernel-demo.json --seeds 1:100 --ticks 30 --output results/experiment-demo
python -m futureos experiment --seeds 1:10 --ticks 30 --sensitivity scenarios/sensitivity-demo.json --output results/sensitivity-demo
python -m benchmarks.experiment --seeds 100 --ticks 30 --output results/benchmark-new --verify-repeat
python -m unittest discover -s tests -v
python -m futureos audit --seeds 2026 --ticks 30 --mode trace --output results/m3-new
python -m futureos replay results/m3-new/runs/run-000001.json
python -m futureos trajectory results/m3-new/runs/run-000001.json --agent agent-021
python -m futureos divergence results/m3-new/runs/run-000001.json results/m3-new/runs/run-000002.json
python -m benchmarks.audit --ticks 10,30,60 --output results/m3-profile-new
python -m futureos population plan --description "Donos de pequenos restaurantes avaliando software de automação" --size 100 --provider fake --output population-spec.json
```

No Windows, o launcher também funciona: `py -3.13` no lugar de `python`. Nesta máquina a convenção é prefixar com `rtk proxy`; RTK é opcional para o produto. Não é necessário executar pip, npm ou instalar pacotes.

A demo usa [cenário versionado](scenarios/kernel-demo.json): 20 cidadãos e 1 influenciador, 10 ticks, snapshot, branches A (preço 70), B (99,90), C (70 e incentivo 20), mais 20 ticks. Valores são fixtures sintéticas sem definição comercial. `--output` salva manifesto, comparação e quatro snapshots JSON. Saídas de resultados são ignoradas pelo Git.

`experiment` repete esse fluxo por seed; `--ticks 30` é o horizonte total 10+20. O lote salva summaries de runs e relatórios, sem duplicar snapshots. O diretório de saída deve ser novo ou vazio. [Protocolo M2](docs/EXPERIMENTS.md) explica estatística populacional, distribuição, pareamento RNG e baseline OAT; [evidência](docs/M2_REPORT.md) registra benchmark e limites científicos.

## Arquitetura implementada

| Módulo | Comportamento |
|---|---|
| [models](futureos/models.py), [validation](futureos/validation.py) | Contratos tipados e invariantes |
| [randomness](futureos/randomness.py) | SplitMix64 versionado, seed e estado da stream |
| [population](futureos/population.py) | População e relações sintéticas |
| [engine](futureos/engine.py) | Eventos, decisões síncronas e transições puras |
| [codec](futureos/codec.py), [snapshots](futureos/snapshots.py) | JSON estrito, checksum, gravação e restauração |
| [branches](futureos/branches.py) | Linhagem, cópias independentes e comparação |
| [demo](futureos/demo.py), [CLI](futureos/__main__.py) | Experimento local e apresentação |
| [experiments](futureos/experiments.py), [sensitivity](futureos/sensitivity.py) | Lotes pareados, agregação, distribuição e OAT |
| [audit](futureos/audit.py), [audit_runs](futureos/audit_runs.py) | Trace/deltas, trajetórias, compromissos por tick, replay e divergência M3 |
| [population_spec](futureos/population_spec.py), [population_validation](futureos/population_validation.py) | Contrato PopulationSpec, JSON para revisão e validação compartilhada |
| [population_generator](futureos/population_generator.py), [relationship_generator](futureos/relationship_generator.py) | Spec + seed → agentes/relações → Simulation usando o engine existente |
| [population_planner](futureos/population_planner.py), [adapter](futureos/llm_provider.py) | Proposta opcional M13; fake offline, assumptions, warnings e provenance |

`create_simulation`, `schedule_event`, `tick` e `run_ticks` retornam cópias. `create_snapshot` produz JSON imutável; `restore_snapshot` reconstrói estado independente. `create_branch` recebe `BranchConfiguration(id, metadata)`; criar os branches primeiro e agendar intervenções depois preserva a origem exata. `compare_branches` compara métricas no mesmo horizonte e origem.

`create_simulation(..., audit_mode="summary" | "trace")` seleciona engine-v2/RNG contextual; o default continua v1. SHA-256 deriva as seeds de streams SplitMix64 por mecanismo/tick/agente/evento. Summary mantém métricas/fingerprints por tick sem trace completo; trace permite consultar eventos, influências e mudanças. [Protocolo M3](docs/AUDIT_TRAJECTORIES.md) define hashes e versões. O trace tem custo de cópias/validação relevante no perfil medido; usar conforme necessidade de auditoria.

## Continuidade

Começar por [AGENTS](AGENTS.md), [estado](docs/CURRENT_STATE.md), [decisões](docs/DECISIONS.md), [arquitetura](docs/ARCHITECTURE.md), [motor](docs/SIMULATION_ENGINE.md) e [próxima missão](docs/NEXT_STEPS.md). [Handoff](docs/HANDOFF.md), [Harness](docs/HARNESS.md) e [memória](docs/MEMORY.md) explicam governança.

Harness é opcional para desenvolvimento; seus checkpoints não são snapshots de simulação nem backup de código. O modelo de adoção é sintético e não calibrado; agentes não representam população real e frequência simulada não é probabilidade real. Resultados testam infraestrutura e exploram comportamento do modelo. Interface web, banco externo, providers reais e frameworks de agentes continuam adiados.

`population plan` não inicia Simulation. Revise o JSON, carregue com `PopulationSpec.from_json` e depois use `create_simulation_from_population_spec(spec, seed)` explicitamente; o [relatório M13](docs/M13_LLM_POPULATION_PLANNER.md) mostra as duas etapas. O fake usa uma fixture genérica, sem inferir características reais da descrição. Um planner real pode variar; mesmo JSON validado + mesma seed mantém geração determinística.
