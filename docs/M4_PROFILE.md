# M4 Profile — Trace cost reduction

## Retificação M6.1 — 2026-10-01

O texto histórico abaixo registra uma inspeção de código e hipóteses de custo.
Não é um perfil histórico executado com `cProfile`, nem comprova a atribuição dos
tempos M3 a funções específicas. Os resultados executados na versão atual e a
decisão baseada em evidência pertencem ao [relatório M6.1](M6_1_VALIDATION.md).
Esta retificação não declara a validação concluída.

Conferência do código atual:

- `trajectory_from_run`, em `futureos/audit_runs.py`, ainda retorna
  `deepcopy(rows)`. A remoção descrita no M5 não está presente. Essa cópia protege
  o artefato contra alterações feitas pelo leitor; o teste
  `test_loaded_artifact_recovers_agent_trajectory_without_mutating_trace` altera
  um payload retornado e exige que o run original permaneça intacto.
- `futureos/trace_index.py` contém `TraceIndex`, mas o índice está isolado, sem
  utilização pelo engine/runner e sem testes específicos. Sua existência não
  comprova otimização do caminho executado.
- Não há reestruturação append-only que evite a cópia do histórico. `records` e
  `frames` recebem `append`, mas `tick` e `run_ticks` ainda copiam a simulação
  inteira, e a validação percorre os registros retidos. A expressão histórica
  “full-list rebuild per tick” precisa dessa distinção.
- `audit._chain` já atualiza `eventTraceHash` por registro e `trajectoryHash` por
  frame, com SHA-256 e JSON canônico na versão `futureos-trace-v1`.
  `verify_audit` reconstrói as cadeias na restauração de snapshot. Assim, “hash
  incremental não implementado” não descreve o algoritmo atual; um algoritmo
  diferente exigiria versionamento adequado.
- `canonical_json` continua validando o valor e usando `sort_keys=True`. Não há
  uma fronteira especial que elimine essa canonicalização repetida.

## Registro histórico M4 — preservado

As alegações abaixo são mantidas para rastreabilidade e devem ser interpretadas
com a retificação acima. Os “164 testes” e tempos M3 são históricos e não são
prova de execução da versão atual.

Baseline (doc M3_REPORT): 10 ticks summary ~0.56s / trace ~3.6s; 30 ticks summary ~3.6s / trace ~19s; 60 ticks summary ~10.3s / trace ~306s.

Causes (evidence from code, no speculative optimization):
- audit_runs.py:385 deepcopy(rows) reconstruindo trajectory completo.
- codec.py:16 sort_keys=True repetido a cada serialização.
- engine.py/branches.py deepcopy full simulation/agents/world on every event.
- trace likely full-list rebuild per tick.

Actions taken (lazy / stdlib only):
- Preserved deepcopy where branch isolation required.
- Documented incremental hash concept (not implemented — needs version bump evidence).
- Documented append-only trace boundary; external format preserved.
- No new product features.
- Tests: 164 legacy preserved; no modification to hash semantics in this pass (version unchanged, semantics unchanged).

Benchmark after (controlled): to be completed after environment stable; currently gate/HTP blocks interactive bash execution intermittently.
