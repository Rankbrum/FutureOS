# Evidência M2 — experimentos, sensibilidade e benchmark

Data: 2026-09-30, America/Sao_Paulo. Python 3.13.15, engine `futureos-kernel-v1`, modelo `synthetic-adoption-v1`, RNG `splitmix64-v1`. Somente biblioteca padrão; nenhuma dependência instalada ou chamada externa do runtime.

**M2 concluída.** Lote principal de 100 seeds, repetição determinística e sensibilidade adicional de 100 seeds passaram. Encerramento operacional e memória durável são registrados em CURRENT_STATE e no estado/checkpoint Harness.

## Comandos e artefatos

```powershell
python -m futureos experiment --scenario scenarios/kernel-demo.json --seeds 1:100 --ticks 30 --output results/experiment-new
python -m benchmarks.experiment --seeds 100 --ticks 30 --output results/experiment-demo --verify-repeat
python -m futureos experiment --scenario scenarios/kernel-demo.json --seeds 1:100 --ticks 30 --sensitivity scenarios/sensitivity-acceptance.json --output results/sensitivity-100
python -m futureos experiment --scenario scenarios/kernel-demo.json --seeds 1:10 --ticks 30 --sensitivity scenarios/sensitivity-demo.json --output results/sensitivity-demo
python -m unittest discover -s tests -v
```

Comandos executados nesta máquina foram prefixados com `rtk proxy py -3.13`; os comandos acima são a forma portátil equivalente. O primeiro comando documenta a CLI; sua integração foi exercitada por testes em cenários pequenos. O benchmark executa exatamente o mesmo `run_experiment` nas 100 seeds e verifica a repetição. Saídas ocupadas são rejeitadas: usar um novo caminho para repetir.

`--ticks 30` inclui 10 ticks comuns e 20 por branch. São 300 runs finais sobre 100 origens, com 7.000 ticks efetivamente executados pelo compartilhamento do passado. Não são 9.000 ticks recomputados independentemente.

## Agregado principal — 100 seeds

Experimento: `experiment-8ac1bfe077ab17e9d33eb5f99984c35caa8b5957923c34970ec4501f259718ea`. Cada estatística contém 100 valores finais, e o JSON conserva a distribuição por seed/run_id. Mesma população-base completa por seed entre A/B/C, sem misturar origens de seeds distintas.

| Branch | Adoção média | Mediana | Mínimo | Máximo | Desvio padrão (pp) | Variância (fração²) |
|---|---:|---:|---:|---:|---:|---:|
| A — preço 70 | 43,7619% | 42,8571% | 19,0476% | 80,9524% | 12,6113 | 0,0159045351 |
| B — preço 99,90 | 28,3333% | 28,5714% | 9,5238% | 57,1429% | 10,8039 | 0,0116723356 |
| C — preço 70 + incentivo 20 | 61,0952% | 59,5238% | 33,3333% | 95,2381% | 13,6203 | 0,0185512472 |

Outras médias das mesmas 100 execuções:

| Branch | Trust | Sentiment | Intent | Interações | Eventos |
|---|---:|---:|---:|---:|---:|
| A | 0,601179691 | 0,031433382 | 0,511640722 | 381,5 | 4 |
| B | 0,601193869 | 0,031453953 | 0,451610540 | 381,5 | 4 |
| C | 0,601184945 | 0,031442822 | 0,557662411 | 381,5 | 4 |

Interações em cada branch: mediana 382, mínimo 350, máximo 415, desvio 14,60719, variância 213,37. Eventos são sempre 4 (desvio/variância zero). Todas as seis métricas têm count/mean/median/min/max/standard_deviation/variance/distribution em `results/experiment-demo/aggregate.json`; a tabela não substitui sua distribuição.

Comparações de adoção, pareadas por seed:

| Par | Primeiro maior | Segundo maior | Empates | Delta média (primeiro − segundo, pp) |
|---|---:|---:|---:|---:|
| A / B | 94 | 0 | 6 | +15,4286 |
| C / A | 97 | 0 | 3 | +17,3333 |
| C / B | 100 | 0 | 0 | +32,7619 |

O JSON usa pares canônicos A−B, A−C, B−C e preserva os sinais respectivos. O relatório completo conserva também deltas de mediana, deltas individuais e ganhos/empates nas demais métricas. Esses números são frequências neste espaço simulado, sem inferência prescritiva.

## Benchmark principal e reprodução

| Medida | Valor observado |
|---|---:|
| Agentes / seeds / branches / horizonte | 21 / 100 / 3 / 30 |
| Runs finais / ticks físicos | 300 / 7.000 |
| Duração baseline | 383,341770s |
| Runs/s | 0,782591 |
| Média total/run | 1,277806s |
| Duração repeat | 318,192695s |
| Arquivos / bytes persistidos | 305 / 892.504 |
| Snapshot origem: min / média / max bytes | 36.099 / 39.026,83 / 41.915 |
| Snapshot final: min / média / max bytes | 78.568 / 86.141,21 / 93.434 |
| Memórias origem: min / média / max | 134 / 156,19 / 177 |
| Memórias final: min / média / max | 441 / 499,32 / 557 |

Windows 11, Python 3.13.15. As contagens de memórias são entradas, não consumo de RAM. Guardar as 100 origens e 300 snapshots finais medidos exigiria aproximadamente **29.745.047 bytes de JSON**, frente aos 892.504 efetivamente gravados, cerca de **33,3 vezes** menos volume no lote compacto. Essa comparação inclui todos os relatórios compactos, sem prometer o mesmo fator em outro cenário.

`--verify-repeat` reexecutou com entrada de seeds invertida; o runner normalizou para ordem crescente. Manifest, cada run (incluindo hashes de estado final), aggregate e comparison foram canonicamente idênticos. Tempo ficou excluído da igualdade. Depois, os 300 summaries do disco foram reagregados e comparados usando os validadores finais; coincidência exata com os relatórios salvos. Nenhum snapshot completo de lote foi persistido.

Guardas do benchmark exercitadas: seeds 0/100001, horizonte igual ao branch point, pasta ocupada e mismatch de comparison não gravam resultado. Medição foi feita sob carga concorrente de testes/OAT; diferenças de duração entre baseline/repeat não significam mudança do modelo ou ganho de uma otimização.

## Testes e revisão

- Baseline M1: 61 testes OK, 8,727s.
- Suite final M2: **100 testes OK, 34,736s**; 61 legados e 39 novos (21 experimentos, 11 OAT e 7 CLI).
- Determinismo, reordenação de seeds/branches/rows, origem por seed, isolamento, população/versões/horizontes elegíveis, agregação das seis métricas, desvios/variância populacionais, distribuição, ganhos/perdas/empates pareados, JSON estrito, preflight integral e saída sem mistura.
- Regressões cobrem configuração negativa/incompleta, overrides desconhecidos e intervenções incompatíveis em summaries importadas, não apenas inputs do runner.
- OAT cobre todos os seis atributos candidatos, campo amount de INCENTIVE, reach de NEWS, incentivo por branch e fatores independentes sem acumular alterações.
- CLI mantém flags e snapshots da demo M1, range inclusivo/lista explícita, JSON/resumo humano, protocolo inválido sem output e limite operacional contra alocação enorme.

Revisão paralela encontrou e corrigiu alias de configuração entre manifesto/run, proveniência incompleta e validação fraca de configuração/intervenção ao reagregar. Uma expectativa inicial do teste de `sensitivity.json` foi ajustada ao estado explícito `not_requested`. Nenhum teste final falhou. Não houve otimização do kernel.

## Replay em processos distintos

Processo Python 1 gerou snapshot tick 10 e hashes completos dos ticks 11–30. Processo Python 2 carregou a origem do disco e avançou 20 ticks. Todos os estados completos por tick e o JSON canônico do snapshot final coincidiram; o arquivo de origem permaneceu intacto.

Fixture seed 2026, 21 agentes: origem **37.969 bytes / 148 memórias**, final **76.623 bytes / 429 memórias**. Checksum final: `60947ec1c479665f211559d4ba3a2c8945a6dce22482284bc0862f39595b31d5`. Evidência local ignorada: `results/m2-replay-verification.json`. É replay da trajetória original M1, não de uma intervenção OAT.

## Sensibilidade demonstrativa — 10 seeds

12 especificações únicas × 10 seeds × 3 branches × 30 ticks = **360 runs**, com três análises OAT. Duração total medida **436,767s**, throughput **0,824 runs/s**. Inclui execução e summaries da sensibilidade; exclui preflight inicial e escrita em disco, conforme benchmark. Artefatos: **35 arquivos, 1.802.576 bytes** em `results/sensitivity-demo`. Timings e snapshots de sizing ficam separados dos resultados determinísticos.

População: price_sensitivity absoluto para todos os agentes no tick zero. Baseline uniforme 0,50 é distinto da população original heterogênea. Deltas de adoção média, em **pontos percentuais**, relativos a esse baseline:

| Valor | A | B | C |
|---:|---:|---:|---:|
| 0,40 | +16,67 | +11,43 | +5,71 |
| 0,45 | +8,10 | +5,71 | +2,38 |
| 0,50 | 0 | 0 | 0 |
| 0,55 | −9,05 | −7,14 | −1,90 |
| 0,60 | −12,86 | −11,43 | −5,24 |

NEWS `news-3`, baseline reach 0,80, mesmos seeds e demais campos:

| Reach | Delta A (pp) | Delta B (pp) | Delta C (pp) |
|---:|---:|---:|---:|
| 0,20 | −1,90 | −2,86 | −3,81 |
| 0,40 | −0,48 | −0,95 | −2,86 |
| 0,60 | −0,48 | −0,48 | −1,43 |
| 0,80 | 0 | 0 | 0 |

INCENTIVE de C, baseline amount 20, via definição da branch:

| Amount | Delta A (pp) | Delta B (pp) | Delta C (pp) |
|---:|---:|---:|---:|
| 0 | 0 | 0 | −24,76 |
| 10 | 0 | 0 | −12,86 |
| 20 | 0 | 0 | 0 |
| 30 | 0 | 0 | +10,00 |

As variantes permanecem independentes; modificar incentivo C não alterou métricas de A/B. Arquivo `sensitivity.json` conserva manifestos, métricas individuais, distribuições e deltas pareados de cada baseline/variante. Esse exemplo tem **10 seeds**; a demonstração de aceite abaixo usa 100 no protocolo `sensitivity-acceptance.json`.

## Sensibilidade de aceite — 100 seeds

CLI real executada com `--seeds 1:100 --ticks 30 --sensitivity scenarios/sensitivity-acceptance.json`. Baseline C incentivo 20 e variante 30: **2 experimentos únicos, 600 runs** (21 agentes, 3 branches, 30 ticks cada), total **756,924734s**, throughput **0,792681 runs/s**. O baseline repetido na lista de valores é reutilizado por cache exato com relatórios copiados, sem recalcular. Pasta `results/sensitivity-100`: **305 arquivos, 3.586.770 bytes**.

| Branch | Adoção média baseline | Variante incentivo C=30 | Delta média (pp) |
|---|---:|---:|---:|
| A | 43,7619% | 43,7619% | 0 |
| B | 28,3333% | 28,3333% | 0 |
| C | 61,0952% | 70,1429% | +9,0476 |

C na variante: mediana 71,4286%, mínimo 38,0952%, máximo 95,2381%, desvio populacional 11,5442 pp e variância 0,0133267574. Adoção maior que baseline em **84/100 seeds**, igual em 16/100, menor em 0/100. Delta entre medianas: +11,9048 pp; mediana dos deltas pareados: +9,5238 pp. Os dois campos são distintos.

Manifesto/agregado/comparação originais dessa execução CLI foram idênticos aos do benchmark de 100 seeds. Todos os baselines/variantes foram reagregados/pareados novamente com o validador final e coincidiram exatamente com os JSON salvos. A/B preservaram as seis métricas e hashes de estado final por seed ao modificar somente C. Não se interpreta 84/100 como probabilidade real.

## Limitações e próxima recomendação

O modelo é sintético; regras não foram calibradas; agentes não representam população real; frequência simulada não equivale a probabilidade real. Esses resultados testam infraestrutura e exploram comportamento do modelo. Não são conclusões prescritivas ou recomendações comerciais.

Benchmark foi medido com outras verificações locais concorrentes: não é um ensaio isolado nem SLA. Tempo inclui validação/cópias/sizing/relatórios; persistência em disco fica fora. Estados completos, memórias e logs ainda crescem com ticks. Summary de run não permite retomada; hashes não autenticam autor; gravação multi-arquivo pode deixar lote parcial. RNG único por simulação pode desalinha-la após consumo diferente. OAT não mede interação/global sensitivity ou validade empírica.

Próxima missão recomendada: [auditoria de trajetórias e RNG por mecanismo](NEXT_STEPS.md), com desenho/versionamento e perfil de crescimento antes de nova infraestrutura. M3 é proposta, não implementada. Sem web, LLM, banco externo, MCP externo ou calibração real nesta entrega.

## Inventário desta missão

**Criados:** `futureos/experiments.py`, `futureos/sensitivity.py`, `benchmarks/__init__.py`, `benchmarks/experiment.py`, `tests/test_experiments.py`, `tests/test_sensitivity.py`, `tests/test_experiment_cli.py`, `scenarios/sensitivity-demo.json`, `scenarios/sensitivity-acceptance.json`, `docs/EXPERIMENTS.md` e este relatório. Resultados e replay são gerados/ignorados; checkpoints e resumos Memory Core são registros de continuidade.

**Modificados:** `futureos/__main__.py`, README, docs/ARCHITECTURE, SIMULATION_ENGINE, DECISIONS, CURRENT_STATE, NEXT_STEPS, ROADMAP e HANDOFF; results/README; .harness/CURRENT_TASK, STATE, PROJECT, DECISIONS, MEMORY e LESSONS; PROJECT do Memory Core. AGENTS, adapters Claude/Gemini, kernel/snapshots M1, cenário kernel-demo, .gitignore e pyproject foram preservados. Git main continua sem commit/remoto/publicação.

**Decisões:** D013 (pareamento e estatística populacional), D014 (OAT/baseline absoluto), D015 (summary mínimo, medição e diretório novo). Histórico D001–D012 preservado. Checkpoint final é resumo de desenvolvimento, sem backup de código; ID/registro no STATE e CURRENT_STATE. Memory Core guarda resumo durável e ponte para estes documentos, sem copiar o projeto ou conversas.

**Checkpoint final verificado:** [cp-2026-09-30T23-38-57-391Z](../.harness/checkpoints/cp-2026-09-30T23-38-57-391Z/checkpoint.json). CURRENT_TASK copiado coincide exatamente com o arquivo atual. STATE completed, PROJECT oficial e resumo `codex-20-37-16-FutureOS.md` do Memory Core conferidos. Nenhuma pendência funcional de M2.
