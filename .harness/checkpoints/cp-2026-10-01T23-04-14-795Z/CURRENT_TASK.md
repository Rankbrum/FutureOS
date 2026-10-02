# Missão atual — M6.1 COMPLETE

Validação executada em 2026-10-01: **M6.1 COMPLETE**. Python 3.13.15,
FutureOS 0.1.0, engine-v2 / trace-v1 / RNG contextual / snapshot2 / artifact1.
Worktree C:/projetos/FutureOS, main sem commits. Produto preservado; manifesto
SHA-256 `416573e25ef2a72535aa56ac12f576ce234b998f8e56a5323aec343cbbe59079`. Fontes originais conferidas inalteradas no encerramento.

Suíte atual: **164 testes, 164 passados, 0 falhas, 0 erros, 0 skips, 24,373 s,
exit0**. Replay, três hashes, isolamento de branches/RNG, snapshots e determinismo
summary/trace executados. Replay CLI adicional A/trace30: matched=true nos três hashes.

18 medições sequenciais em processos novos: medianas summary10/30/60
**0,494219 / 2,574082 / 7,240894 s**; trace **3,139936 / 14,375663 / 48,884915 s**.
Bytes reais iguais entre repetições do mesmo modo; hashes iguais entre repetições
e modos. Trace60 bruto: 116,541106 / 48,755855 / 48,884915 s, extremo preservado.
Comparação M3 é histórica/descritiva, sem prova causal de melhoria.

Piloto120 trace: **958,522689 s**, 20.229.952 bytes, 47.978 records e pico RSS
120,356 MiB. Três repetições opcionais consideradas não razoáveis pelo custo
observado de ~16 minutos; sem mediana120 nem comprovação de repetição.

cProfile trace60 e consulta de trajetória executados; rankings cumulative/self/calls,
JSON/sort_keys e persistência no relatório. deepcopy acumulou
171.817730 s; canonical_json 21.625435 s,
6.02% do pstats (inclui validação/JSON; cumulativos não são aditivos).

Código contradiz a alegação M5: trajectory_from_run mantém deepcopy(rows),
necessário ao retorno isolado; TraceIndex sem integração/testes; sem nova fronteira
de canonicalização ou estrutura append-only imutável. _chain já é incremental v1.
M6_TRACE_CORE ausente e não criado. M4/M5 e o registro M6 anterior foram retificados.

D019 registra execução atual; D020 decide **manter hash-v1, sem algoritmo novo**:
canonicalização é secundária frente a cópia/validação e _chain já é incremental.
Próxima M7: golden moderno/diferencial v1 e uma otimização pequena de cópia ou
validação histórica, byte-equivalente e medida antes/depois.
Sem instalação, commit, remoto, UI ou LLM. Checkpoint é resumo, não backup de código.

Root Codex é o único escritor de estado/checkpoint. Ler docs/M6_1_VALIDATION.md,
docs/evidence/M61_20261001.json, docs/NEXT_STEPS.md e D019/D020. Raw/pstats em
results/m61-validation-20261001. Histórico M3 em cp-2026-10-01T17-49-36-974Z.
Encerramento atualiza memória oficial e cria checkpoint do resumo, sem backup de código.
