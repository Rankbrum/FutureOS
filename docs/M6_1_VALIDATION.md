# M6.1 — validação executada do worktree persistido

**Status: M6.1 COMPLETE.** Executado nesta sessão de 2026-10-01. Não deriva
conclusão de testes/perfis históricos. Produto não alterado; algoritmo e versões
de hashes preservados. Isto conclui a validação, não uma reescrita estrutural M6.

## Versão efetivamente usada

- Worktree `C:/projetos/FutureOS`, branch `main`, HEAD unborn: **nenhum commit**.
  Todos os arquivos do projeto estavam untracked. Git não permite atribuir um diff
  histórico a M5/M6; identidade por conteúdo registrada antes da suíte.
- FutureOS pacote `0.1.0`, Python `3.13.15`, engine `futureos-kernel-v2`, RNG
  `sha256-path-splitmix64-v1`, trace `futureos-trace-v1`, snapshot schema2,
  artifactVersion1 e replay `scenario-rebuild-v1`. Legados v1/schema1 preservados.
- SHA-256 do manifesto de runtime/cenários/pyproject:
  `416573e25ef2a72535aa56ac12f576ce234b998f8e56a5323aec343cbbe59079`.
  [Manifesto completo](evidence/M61_CODE_IDENTITY.json) inclui também hashes de
  testes e benchmarks anteriores. Todos esses arquivos continuaram idênticos
  até o encerramento. Novo helper de medição: `benchmarks/m61_validation.py`.
- Windows 11 build26200, i5-1235U, 10 cores/12 threads, RAM física
  16.907.784.192 bytes. Python real: `C:\Users\renan\AppData\Local\Programs\Python\Python313\python.exe`.
  Nenhuma dependência instalada, chamada externa, UI, LLM, commit ou remoto.

## Suíte atual e contratos

Comando efetivamente executado: `python -m unittest discover -s tests -v` via
`rtk proxy`. Exit0: **164 totais, 164 passados, 0 falhas, 0 erros, 0 skips,
24,373 s**. [Log atual completo](evidence/M61_SUITE.txt). O número coincidir com
164 históricos não foi usado como prova: o log lista a execução atual de cada teste.

Todos os testes abaixo foram executados dentro dessa suíte, não apenas inspecionados:

| Contrato | Evidência atual |
| --- | --- |
| Replay / três hashes | test_audit_runs.test_replay_matches_all_hashes_in_both_modes; test_audit_cli replay em novo processo |
| finalStateHash | test_audit igualdade summary/trace, status comprometido e endpoint adulterado |
| trajectoryHash / eventTraceHash | test_audit cadeias adulteradas; test_m3_snapshots adulteração com checksum recalculado |
| Branch isolation | test_snapshots mutações profundas/ordem; test_m3_snapshots estado auditado independente |
| RNG isolation | test_rng_streams consumo separado/PYTHONHASHSEED; test_audit reach/evento/elegibilidade |
| Snapshot compatibility | test_m3_snapshots golden legado, schema2, tipos numéricos e continuação em outro processo |
| Summary/trace determinism | test_audit estado/frames/hashes; test_audit_runs artefatos/identidade/ordenação |

Além disso, replay CLI de arquivo **atual**, A/seed2026/trace30/run1, executou
em novo processo: matched=true, finalStateHash/trajectoryHash/eventTraceHash
expected==actual e firstDivergence=null. JSON preservado na evidência portátil.
Nos benchmarks, três hashes iguais entre modos e repetições10/30/60; volumes
iguais entre repetições do mesmo cenário/modo. Summary e trace produzem volumes
diferentes. Trace120 teve somente um piloto, não mediana/repetição.

## Protocolo e benchmark bruto — três processos independentes

Fixture `synthetic-adoption-demo-v1`, 21 agentes, seed2026, origem10 e branches
A/B/C. Um subprocesso Python novo por configuração/repetição; 18 processos
distintos nos casos obrigatórios e um no piloto, sequenciais. Ordem: R1 10S/10T/30S/30T/60S/60T,
depois R2 e R3; ao final um piloto120T. Sem suíte, outro benchmark ou profiler simultâneo.
Processo Python alheio foi observado; carga de outras aplicações/SO não controlada.
Sem warm-up excluído e sem remover outliers. Tempos incluem preflight, simulação,
relatórios e sizing canônico, **excluem persistência em disco**; correspondem ao
escopo de `benchmarks.audit` usado historicamente no M3.

Ticks físicos: `10 + 3*(horizonte-10)` = 10/70/160/340. Frames e interações
exportados incluem origem repetida em cada branch; interações físicas removem
as duas duplicações. Bytes = cinco JSON UTF-8/LF (manifest, divergences, três runs),
conferidos contra arquivos reais em cada repetição. RSS = pico do processo via
GetProcessMemoryInfo antes da persistência, incluindo imports; commit e pico
incluindo disco estão no JSON. Não é tracemalloc/alocação líquida do engine.

| Ticks | Mode | Run 1 s | Run 2 s | Run 3 s | Mínimo s | Mediana s | Máximo s | s/tick físico |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | summary | 0.511227 | 0.492160 | 0.494219 | 0.492160 | 0.494219 | 0.511227 | 0.049422 |
| 10 | trace | 3.146671 | 3.139936 | 3.078328 | 3.078328 | 3.139936 | 3.146671 | 0.313994 |
| 30 | summary | 2.574082 | 2.508964 | 2.595235 | 2.508964 | 2.574082 | 2.595235 | 0.036773 |
| 30 | trace | 14.637043 | 14.375663 | 14.272555 | 14.272555 | 14.375663 | 14.637043 | 0.205367 |
| 60 | summary | 7.198665 | 7.240894 | 7.472696 | 7.198665 | 7.240894 | 7.472696 | 0.045256 |
| 60 | trace | 116.541106 | 48.755855 | 48.884915 | 48.755855 | 48.884915 | 116.541106 | 0.305531 |

| Ticks | Mode | Bytes/run | Records retidos | traceCount exportado | Frames | Interações físicas / exportadas | Pico RSS R1/R2/R3 MiB |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | summary | 72962 | 0 | 4317 | 30 | 127 / 381 | 25.906 / 25.797 / 25.566 |
| 10 | trace | 1762983 | 4317 | 4317 | 30 | 127 / 381 | 36.750 / 36.281 / 36.215 |
| 30 | summary | 195902 | 0 | 12992 | 90 | 904 / 1158 | 27.070 / 27.324 / 27.301 |
| 30 | trace | 5529725 | 12992 | 12992 | 90 | 904 / 1158 | 53.609 / 53.516 / 54.227 |
| 60 | summary | 378174 | 0 | 24999 | 180 | 1975 / 2229 | 28.398 / 29.031 / 28.391 |
| 60 | trace | 10562058 | 24999 | 24999 | 180 | 1975 / 2229 | 76.453 / 77.199 / 76.477 |

120 trace custou **958,522689 s** na tentativa de viabilidade; persistência
1,838889 s fora do timer, 20.229.952 bytes, 47.978 records retidos, 360 frames,
4.213 interações físicas/4.467 exportadas, pico RSS120,356 MiB antes do disco.
**Não razoável para três repetições nesta validação** pelo custo observado de
~16 minutos por tentativa. Registrado como piloto, sem mínimo/mediana/máximo de
três runs ou comparação M3; não há M3 histórico120. A primeira repetição trace60
116,541106 s permanece na tabela; as demais foram 48,755855/48,884915 s.
Nenhuma causa para o extremo é demonstrada por esta medição.

### Persistência separada

save_audit_experiment inclui validação, nova canonicalização e escrita;
não representa somente I/O nem garante fsync. Fica fora do tempo comparado ao M3.

| Ticks | Mode | Persistência R1 s | R2 s | R3 s | Mediana s |
| --- | --- | --- | --- | --- | --- |
| 10 | summary | 0.014103 | 0.013638 | 0.012315 | 0.013638 |
| 10 | trace | 0.172178 | 0.159297 | 0.193282 | 0.172178 |
| 30 | summary | 0.021767 | 0.023759 | 0.022361 | 0.022361 |
| 30 | trace | 0.495870 | 0.515338 | 0.606715 | 0.515338 |
| 60 | summary | 0.040398 | 0.037392 | 0.047190 | 0.040398 |
| 60 | trace | 1.052777 | 0.998408 | 0.971654 | 0.998408 |

## Comparação M3 × M6

**M3 = observações históricas únicas de docs/M3_REPORT.md. M6 = medianas
executadas agora no worktree identificado.** Mesmo cenário/seed/horizontes/escopo
declarados, mas hardware/carga histórica e digest histórico não estão registrados.
Não assumir condições iguais nem atribuir diferenças a otimizações. A remoção M5
alegada nem sequer está no arquivo atual, e trajectory_from_run não integra esse benchmark.

| Ticks | Mode | M3 histórico s | M6 mediana atual s | Diferença s (%) |
| --- | --- | --- | --- | --- |
| 10 | summary | 0.563358 | 0.494219 | -0.069139 (-12.27%) |
| 10 | trace | 3.616264 | 3.139936 | -0.476328 (-13.17%) |
| 30 | summary | 3.637748 | 2.574082 | -1.063666 (-29.24%) |
| 30 | trace | 19.147803 | 14.375663 | -4.772140 (-24.92%) |
| 60 | summary | 10.320634 | 7.240894 | -3.079740 (-29.84%) |
| 60 | trace | 306.405316 | 48.884915 | -257.520401 (-84.05%) |

## Profile atual engine-v2 trace60

cProfile executado **depois** dos benchmarks, em processo próprio, mesmo
cenário/seed/branches/horizonte60, incluindo execução, sizing e persistência.
Tempo instrumentado antes de disco 352.064223 s;
persistência 7.136935 s;
total contabilizado por pstats 359.173816 s.
Não misturar esses tempos com o benchmark sem profiler.
Rankings completos em results/m61-validation-20261001/profile-60-trace;
top40 e funções-alvo preservados em [JSON portátil](evidence/M61_20261001.json).
Cumulative inclui descendentes: linhas aninhadas se sobrepõem, não somar suas porcentagens.

### Ranking por cumulative time

| # | Função | Calls totais | Self s | Cumulative s |
| --- | --- | --- | --- | --- |
| 1 | audit_runs.py:139 run_audit_experiment | 1 | 0.037851 | 348.630057 |
| 2 | audit_runs.py:103 _run | 3 | 0.028697 | 338.401677 |
| 3 | engine.py:430 run_ticks | 4 | 0.690386 | 324.006579 |
| 4 | engine.py:391 tick | 160 | 0.933100 | 322.001490 |
| 5 | copy.py:119 deepcopy | 31995599 | 72.509059 | 171.817730 |
| 6 | copy.py:218 _deepcopy_dict | 3474660 | 23.675970 | 171.429711 |
| 7 | copy.py:192 _deepcopy_list | 428752 | 3.622260 | 169.816570 |
| 8 | copy.py:248 _reconstruct | 871913 | 8.975068 | 169.076509 |
| 9 | copy.py:201 _deepcopy_tuple | 871731 | 4.972933 | 168.968726 |
| 10 | validation.py:56 validate_json | 1771467 | 3.468164 | 154.118491 |
| 11 | validation.py:60 visit | 27389613 | 100.576770 | 150.650327 |
| 12 | validation.py:244 validate_simulation | 367 | 0.054263 | 134.459616 |
| 13 | audit.py:152 validate_audit | 370 | 6.773312 | 127.066784 |
| 14 | validation.py:23 _unicode | 29132299 | 16.925958 | 28.791611 |
| 15 | ~:0 <method 'get' of 'dict' objects> | 65062581 | 22.709628 | 22.709628 |
### Ranking por total time (self)

| # | Função | Calls totais | Self s | Cumulative s |
| --- | --- | --- | --- | --- |
| 1 | validation.py:60 visit | 27389613 | 100.576770 | 150.650327 |
| 2 | copy.py:119 deepcopy | 31995599 | 72.509059 | 171.817730 |
| 3 | copy.py:218 _deepcopy_dict | 3474660 | 23.675970 | 171.429711 |
| 4 | ~:0 <method 'get' of 'dict' objects> | 65062581 | 22.709628 | 22.709628 |
| 5 | ~:0 <built-in method builtins.id> | 65903638 | 17.068322 | 17.068322 |
| 6 | validation.py:23 _unicode | 29132299 | 16.925958 | 28.791611 |
| 7 | ~:0 <method 'encode' of 'str' objects> | 29200350 | 11.935714 | 11.935714 |
| 8 | copy.py:248 _reconstruct | 871913 | 8.975068 | 169.076509 |
| 9 | audit.py:152 validate_audit | 370 | 6.773312 | 127.066784 |
| 10 | copy.py:232 _keep_alive | 5647056 | 5.834476 | 9.313552 |
| 11 | dataclasses.py:1411 _asdict_inner | 3682961 | 5.349490 | 7.862270 |
| 12 | ~:0 <method 'items' of 'dict' objects> | 11192190 | 5.104705 | 5.104705 |
| 13 | copy.py:173 _deepcopy_atomic | 26348543 | 5.053569 | 5.053569 |
| 14 | copy.py:201 _deepcopy_tuple | 871731 | 4.972933 | 168.968726 |
| 15 | ~:0 <built-in method builtins.isinstance> | 13027036 | 4.361326 | 4.361326 |
### Ranking por call count

| # | Função | Calls totais | Self s | Cumulative s |
| --- | --- | --- | --- | --- |
| 1 | ~:0 <built-in method builtins.id> | 65903638 | 17.068322 | 17.068322 |
| 2 | ~:0 <method 'get' of 'dict' objects> | 65062581 | 22.709628 | 22.709628 |
| 3 | copy.py:119 deepcopy | 31995599 | 72.509059 | 171.817730 |
| 4 | ~:0 <method 'encode' of 'str' objects> | 29200350 | 11.935714 | 11.935714 |
| 5 | validation.py:23 _unicode | 29132299 | 16.925958 | 28.791611 |
| 6 | validation.py:60 visit | 27389613 | 100.576770 | 150.650327 |
| 7 | copy.py:173 _deepcopy_atomic | 26348543 | 5.053569 | 5.053569 |
| 8 | ~:0 <built-in method builtins.isinstance> | 13027036 | 4.361326 | 4.361326 |
| 9 | ~:0 <method 'items' of 'dict' objects> | 11192190 | 5.104705 | 5.104705 |
| 10 | ~:0 <built-in method math.isfinite> | 10741473 | 3.145631 | 3.145631 |
| 11 | ~:0 <method 'append' of 'list' objects> | 8092256 | 2.892372 | 2.892372 |
| 12 | ~:0 <method 'add' of 'set' objects> | 7462702 | 3.466791 | 3.466791 |
| 13 | ~:0 <method 'remove' of 'set' objects> | 7387980 | 3.286715 | 3.286715 |
| 14 | copy.py:232 _keep_alive | 5647056 | 5.834476 | 9.313552 |
| 15 | ~:0 <built-in method builtins.setattr> | 4213003 | 1.509945 | 1.509945 |

### Funções investigadas e limites de atribuição

| Função | Calls | Self s | Cumulative s |
| --- | --- | --- | --- |
| deepcopy | 31995599 | 72.509059 | 171.817730 |
| validate_json | 1771467 | 3.468164 | 154.118491 |
| validate_simulation | 367 | 0.054263 | 134.459616 |
| validate_audit | 370 | 6.773312 | 127.066784 |
| canonical_json | 32355 | 0.101353 | 21.625435 |
| commit_frame | 160 | 0.074494 | 14.377435 |
| validate_run_artifact | 9 | 0.606718 | 10.482072 |
| content_hash | 3601 | 0.021781 | 9.665581 |
| create_branch | 3 | 0.004050 | 8.240235 |
| restore_snapshot | 3 | 0.000464 | 7.868251 |
| save_audit_experiment | 1 | 0.009378 | 7.133954 |
| simulation_from_dict | 3 | 0.000131 | 4.918163 |
| _agent_data | 6993 | 0.021049 | 4.917020 |
| _chain | 26628 | 0.142886 | 4.448780 |
| _decode | 26454 | 0.254655 | 4.078098 |
| _state_data | 170 | 0.006444 | 2.575025 |
| verify_audit | 3 | 0.013636 | 1.391962 |
| _digest | 239753 | 0.238497 | 1.326493 |
| _digest | 11934 | 0.022923 | 0.486995 |
| <built-in method _hashlib.openssl_sha256> | 40535 | 0.207404 | 0.207404 |
| <method 'hexdigest' of '_hashlib.HASH' objects> | 30244 | 0.095836 | 0.095836 |
| write_text | 5 | 0.000106 | 0.033453 |
| write_text | 5 | 0.000124 | 0.033342 |
| <method 'digest' of '_hashlib.HASH' objects> | 10291 | 0.024346 | 0.024346 |
| _hash | 11 | 0.000055 | 0.003549 |

deepcopy: 171.817730 s cumulativos / 31995599 calls totais.
canonical_json: 21.625435 s cumulativos,
6.02% do tempo
contabilizado, incluindo validação+JSON. _chain: 4.448780 s
cumulativos; inclui canonicalização. asdict ocorre nos callers antes de _chain
e deve ser avaliado separadamente. SHA-256 nativo, JSON,
dataclasses, validação e cópia devem ser examinados separadamente pelos self times.
Canonicalização é secundária frente a cópia/validação neste perfil; trocar só o
encadeamento não resolve cópias/revalidação do histórico. Branch copies aparecem em create_branch,
restore_snapshot/_decode e verificações de cadeias. tick/run_ticks/schedule_event
copiam o histórico inteiro; validação percorre frames/records anteriores.

sort_keys=True permanece no encoder. cProfile não separa o tempo de sorting
no encoder C. Diagnóstico isolado de json.dumps sobre cinco documentos trace60,
sete pares com ordem alternada: medianas sort=True
0.402036 s e sort=False
0.359277 s. Exclui validação/hashes/engine/disco;
essa diferença não demonstra ganho end-to-end. sort=False muda bytes canônicos,
portanto não é uma substituição compatível do algoritmo atual.

trajectory_from_run não é chamada no benchmark/profile principal. Profile separado
da consulta agent-021 em artefato trace60: 0.687299 s,
462 registros. Inclui validação do artefato e deepcopy do
resultado destacado, não reconstrução de mundo completo. Ranking separado:

| Função consulta60 | Calls | Self s | Cumulative s |
| --- | --- | --- | --- |
| trajectory_from_run | 1 | 0.007746 | 0.687280 |
| validate_run_artifact | 1 | 0.032205 | 0.638501 |
| validate_json | 1 | 0.000011 | 0.552863 |
| visit | 159136 | 0.366773 | 0.552852 |
| _unicode | 188358 | 0.066776 | 0.114863 |
| <method 'encode' of 'str' objects> | 188358 | 0.048087 | 0.048087 |
| deepcopy | 15350 | 0.017376 | 0.036822 |
| _deepcopy_list | 241 | 0.000886 | 0.036810 |

## Confirmação das alegações M5/M6 no código

- audit_runs.py:385 contém **return deepcopy(rows)**. A remoção alegada no M5
  não está presente. test_audit_runs.py:153 modifica payload retornado e exige
  que o artefato original permaneça intacto; return rows direto quebraria o contrato.
  audit.agent_trajectory retorna rows, mas cria cada linha por asdict(item).
- trace_index.py existe com add/get, sem import/utilização no engine/runner/testes.
  Não há evidência de aceleração entregue pelo índice nem testes novos conceituais executáveis.
- codec.py:13–17 continua validate_json + json.dumps(sort_keys=True), sem
  uma nova fronteira otimizada de canonicalização.
- audit.py:95/128 faz append em listas mutáveis. TraceRecord/TickFrame não são
  imutáveis; engine.py:396/437 copia Simulation com histórico inteiro. Isso não
  comprova uma estrutura append-only que elimine cópias históricas.
- _chain audit.py:31–32 já encadeia digest anterior e item canônico;
  record/commit_frame atualizam incrementalmente eventTraceHash/trajectoryHash.
  verify_audit reprocessa cadeias na restauração/leitura.
- **docs/M6_TRACE_CORE.md não existia e não foi criado**: não houve implementação
  estrutural do core nesta validação. Este relatório registra a validação real.
  M4/M5 receberam retificações; registro M6 anterior em CURRENT_STATE está substituído.

## Decisão sobre hash incremental — manter v1, sem algoritmo novo

D019/D020 em DECISIONS.md. **Não implementar nem promover uma nova versão de hash**
nesta validação: canonical_json é6,02% do pstats total (inclui validação/JSON),
_chain1,24%; deepcopy47,84% cumulativo e validate_simulation37,44% apontam para
cópia e revalidação. Percentuais cumulativos se sobrepõem e a instrumentação
altera custos relativos; não são estimativas diretas de speedup sem profiler.
Os dois encadeamentos já são incrementais v1. Nenhum dado justifica neste aceite
custo/risco de migração para outro algoritmo, especialmente quando a versão
anterior deve continuar legível/reproduzível.

Próximo experimento: golden moderno/diferencial v1 e reduzir cópia/revalidação
histórica com imutabilidade/fronteiras explícitas, defendendo mutações públicas
e adulteração. Materialização única de agentes/hash da origem e serialização
byte-equivalente são alternativas menores. Nunca retirar a cópia de retorno
da trajetória sem preservar isolamento da API.

Se dados posteriores tornarem hashing/canonicalização o gargalo, reavaliar
fingerprints por componente e versão de hash explícita. Qualquer algoritmo
diferente exige versões adequadas de trace/artifact/snapshot, cabeçalho com domínio,
despacho explícito de leitura/replay v1, rejeição de misturas e continuação entre
processos. Não reinterpretar versões antigas. Essa regra não é implementação
nem proposta ativa de migração nesta missão. Versões/hashes atuais mantidos.

## Entrega, checkpoint e próxima missão

Criados helper de medição, este relatório e evidências portáteis; atualizados
CURRENT_STATE, NEXT_STEPS, DECISIONS, retificações M4/M5, resumos/estado Harness e
Memory Core. Artefatos brutos/pstats/scripts auxiliares em results são ignorados
pelo Git; os números e rankings relevantes permanecem nos docs.
Checkpoint final verificado: [cp-2026-10-01T23-04-14-795Z](../.harness/checkpoints/cp-2026-10-01T23-04-14-795Z/checkpoint.json), ID consistente com STATE.json.
Checkpoint é resumo, não backup/Git/snapshot da sociedade. Nenhum commit criado.

Próxima recomendação M7: golden moderno/diferencial v1 e uma otimização pequena
byte-equivalente de cópia/validação histórica, medida antes/depois em mesma
condição. Reavaliar hashing só se novo perfil justificar. Critérios em NEXT_STEPS.

## Reprodução

Sem instalar dependências. Para repetir exatamente esta versão, confira hashes
do manifesto; copie docs/evidence/M61_CODE_IDENTITY.json como code-identity.json
em um diretório de saída novo. Execute a suíte, depois cada comando em processo
próprio, repetindo --repeat 1/2/3; variar ticks10/30/60 e summary/trace.
120 trace é opcional e teve apenas piloto por custo elevado nesta sessão:

```powershell
rtk proxy python -m unittest discover -s tests -v
rtk proxy python -X utf8 -m benchmarks.m61_validation measure --ticks 30 --mode trace --repeat 1 --output results/novo-m61
rtk proxy python -X utf8 -m benchmarks.m61_validation profile --ticks 60 --mode trace --output results/novo-m61
```

O helper rejeita runtime/cenários diferentes do manifesto e diretório de medição
já existente. Para validar versão posterior, capture novo manifesto e execute nova
suíte; não copie o digest desta versão para código alterado.
