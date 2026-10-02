# Evidência da demo M1

Executado em 2026-09-30, Python 3.13.15, engine futureos-kernel-v1, modelo synthetic-adoption-v1 e RNG splitmix64-v1. Cenário [kernel-demo.json](../scenarios/kernel-demo.json), seed 2026, 21 agentes ativos.

`python -m futureos --seed 2026 --output results/demo`

Fluxo: população → 10 ticks → snapshot → A/B/C → 20 ticks independentes → comparação no tick 30.

| Branch | Intervenção no tick 10 | Adoção | Trust | Sentiment | Intent | Interações | Eventos |
|---|---|---:|---:|---:|---:|---:|---:|
| A | preço 70, incentivo 0 | 33,33% (7/21) | 0,641167 | 0,033570 | 0,511591 | 365 | 4 |
| B | preço 99,90, incentivo 0 | 23,81% (5/21) | 0,641096 | 0,033478 | 0,455114 | 365 | 4 |
| C | preço 70, incentivo 20 | 57,14% (12/21) | 0,641168 | 0,033573 | 0,565992 | 365 | 4 |

Snapshot comum: `simulation:synthetic-adoption-demo-v1:tick-10:cf7b5de14baa01cb`. Todos herdam a mesma seed, posição do RNG, eventos futuros, relações, memórias e métricas. As duas intervenções econômicas por branch são universais; NEWS tick 3 e TRUST_SHOCK tick 18 são probabilísticos. Contagens incluem o passado comum.

Artefatos gerados e ignorados pelo Git: `results/demo/report.json`, `origin.snapshot.json` e `branch-1.snapshot.json` a `branch-3.snapshot.json`. O manifesto inclui configuração, cenário, seed, algoritmo, versões, linhagem, checksum, horizonte, métricas e limitações. Valores de preço são unidades sintéticas; não há receita nem garantia comercial. Zero chamadas externas.

Testes verificam igualdade de estado completo em reexecução e retomada, não apenas igualdade desta tabela. Cada snapshot salvo é carregável pela API `load_snapshot`/`restore_snapshot` e pode continuar ticks. Checkpoint do Harness pertence ao desenvolvimento e não contém esses artefatos.
