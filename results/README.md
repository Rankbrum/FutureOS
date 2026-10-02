# Resultados locais

`python -m futureos --output results/demo` grava manifesto/comparação, snapshot de origem e um snapshot final por branch. Saídas são ignoradas pelo Git. O cenário versionado está em `scenarios/kernel-demo.json`.

Snapshots JSON do produto preservam mundo, memórias, relações, fila de eventos, métricas e RNG. Checkpoints em `.harness/checkpoints` preservam somente o resumo do desenvolvimento.

`python -m futureos experiment --seeds 1:100 --ticks 30 --output results/experiment-demo` grava manifest.json, aggregate.json, comparison.json, sensitivity.json, benchmark.json e runs indexadas. Escolha diretório ausente/vazio; não mistura lotes existentes. Não grava snapshots completos. Reexecute pelo cenário/seeds do manifesto quando necessário; summaries não permitem retomar do estado final. Detalhes em [EXPERIMENTS.md](../docs/EXPERIMENTS.md) e evidências em [M2_REPORT.md](../docs/M2_REPORT.md). Sem LLM ou dependências externas; modelo sintético, não calibrado e sem representatividade real.

`python -m futureos audit --seeds 2026 --ticks 30 --mode trace --output results/m3-new` grava manifest, divergences e runs M3 indexadas com cenário/versões/hashes/frames. Summary conserva `records=[]`; trace guarda detalhes. `replay`, `trajectory` e `divergence` consultam esses artefatos. [Protocolo](../docs/AUDIT_TRAJECTORIES.md) e [evidência M3](../docs/M3_REPORT.md) são portáteis; os JSON locais são ignorados.

Aceite 2026-10-01: `m3-profile-20261001/benchmark.json` e seis lotes 10/30/60 summary/trace; `m3-acceptance.json` registra tamanhos reais, igualdade de hashes, replay em processo separado e exemplos. Esses arquivos não fazem parte do handoff mínimo nem substituem os testes/docs versionados.
