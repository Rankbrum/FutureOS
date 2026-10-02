# Evidência M3 — RNG, trajetórias, replay e divergência

Executado em 2026-10-01, Python 3.13.15, somente biblioteca padrão. M3 implementa
o caminho `seed → streams isolados → ticks → trace/deltas → trajetória → hashes
→ replay → divergência`. Sem instalação de dependências, web, LLM ou serviço externo.
O modelo continua sintético e não calibrado; os mecanismos são provenance do algoritmo.

## Baseline e testes

Antes de editar: `python -m unittest discover -s tests -v`: **100 testes OK, 35,684 s**.
SplitMix64-v1 já estava implementado e foi preservado. O estado local registrava M2
concluída; não havia código M3 preexistente. Git local `main`, sem commits/remoto.

Suíte final: **164 testes OK, 23,172 s**, incluindo os 100 legados. A primeira suíte
integrada também passou (48,867 s); a repetição final inclui a consulta de influências
de entrada/saída alinhada entre API e artefato. Tempos dependem da carga da máquina.
Os 64 novos testes estão distribuídos em:

| Suíte | Testes | Garantias principais |
| --- | ---: | --- |
| test_rng_streams | 8 | Derivação canônica, separação, reprodução em processos/PYTHONHASHSEED distintos |
| test_audit | 18 | Trace determinístico, deltas reconstruíveis, isolamento reach/elegibilidade, contribuições e trajetória |
| test_m3_snapshots | 9 | Golden legado, schema2, numerics exatos, cadeias, isolamento e continuação em outro processo |
| test_audit_runs | 25 | IDs/versões, JSON, hashes, replay, primeiro desvio, origem e divergência |
| test_audit_cli | 4 | Persistência, consultas, códigos de erro de replay e summary sem trace |

Cobertura inclui snapshots M1 byte-compatible (checksum golden
`a0955cbba79a548e7c6747a94e3f9ccaad6e7111979d902d2c6a9462cd995959`), valores inteiros
aceitos em campos float no M3, alterações de cadeia/endpoint e consultas com IDs contendo
separadores. A suíte M2 mantém agregação, OAT, pareamento e CLI legados; o aceite de
100 seeds M2 não foi reexecutado nesta missão. Resultados históricos não foram reescritos.

Falhas encontradas e corrigidas durante integração: coerção int/float que alterava hashes
v2; emissão não ordenada de deltas ao limpar overrides; seleção textual ambígua de relações;
saída JSON da CLI em encoding Windows incompatível com UTF-8. Testes de regressão passaram.

## Arquitetura entregue

SplitMix64 continua o gerador base. `RandomStreams` deriva seeds pelo SHA-256 de domínio,
root seed e caminho tipado, codificados em JSON canônico UTF-8. Contextos de eventos,
decisões e interações incluem tick e participantes; população tem uma stream própria.
Social/memory estão reservados sem novos draws. Uma mesma chave reinicia sua stream;
o engine usa contextos únicos e snapshots não mantêm counters por milhares de chaves.

Engine-v2/RNG `sha256-path-splitmix64-v1`/trace `futureos-trace-v1` são selecionados por
`audit_mode`. Default/CLI demo e experiment continuam engine-v1. Pares schema1/engine1 e
schema2/engine2 são suportados explicitamente, sem migração silenciosa. [D016–D018](DECISIONS.md)
registram alternativas/consequências e [AUDIT_TRAJECTORIES](AUDIT_TRAJECTORIES.md) define
granularidade, hashes, formatos, limitações e política mínima de versões.

Summary guarda frames, métricas, unidade, denominador e fingerprints; `records=[]`.
Trace guarda os mesmos frames/hashes e os registros detalhados. Não há cópia de mundo
inteiro em cada delta. Estado social/memórias ainda existem no snapshot integral e são
copiados pelo engine puro. Retenção e cópias não foram otimizadas nesta missão.

## Execução verificada e exemplos

Cenário `synthetic-adoption-demo-v1`, seed **2026**, 21 agentes, snapshot após ticks 0–9,
branches A/B/C e horizonte total 30. Os três runs têm 386 interações e quatro eventos
cumulativos; adoção final A 33,33%, B 23,81%, C 52,38%. São realizações M3 com a nova
política aleatória, sem equivalência presumida com valores de seeds legadas.

Exemplo real de delta do branch A:

```json
{"tick":10,"kind":"state_changed","entity":"world","mechanism":"event:A:1-price","payload":{"field":"price","before":110.0,"after":70.0}}
```

Trajetória de `agent-021`, branch A: **265 registros** selecionados. No tick 1 interagiu
com `agent-001` e recebeu sua contribuição de influência. No tick 2 adotou: intenção **0,4914061390 → 0,5735338395**, score
**0,6739121401**, threshold **0,52**, mecanismo `adoption_threshold`. O registro de
decisão conserva os termos da fórmula, incluindo ruído **0,0147448591**, preço **−0,066**
e contribuições `.55*intentAnterior`/`.45*score`. Recebeu `news-3` no tick 3,
preço/incentivo A no tick 10 e `trust-18` no tick 18. A consulta também conserva
interações de entrada/saída e participantes das contribuições; isso explica o algoritmo.
`agent-001`, por sua vez, tem 236 registros e não adotou até o horizonte 30.

Run A de referência:

```text
runId: audit-run-403fee53bbc805b1a5b3cac9999fc08a4c3a1d7f8d3e323b322d097e6628527b
experimentId: audit-experiment-fbe6ebff23df1dddb077cd74c935c98a52cba19dc6c911452c85cc643002c5bb
finalStateHash: f2d765e43b095544b980e73dde6574ee0df0930aa489b8b4b7a76c1ce34a0351
trajectoryHash: cc3b73b0ee9ad275cf3700ca213a70a2091ba90f2be0b2fc9d01b515f911791f
eventTraceHash: 098b767479de08d1d102436b3ac3c3158e6d1048561ffe94a8facf96e4b6173b
```

Replay pela CLI em **processo Python separado**, lendo o JSON salvo, retornou
`matched=true`, os três pares expected/actual iguais e `firstDivergence=null`.
Fixtures alteradas nos testes identificam primeiro registro/frame/contexto ou hash
detectável; quando só um hash final difere, o relatório não inventa um tick.

A/B divergem primeiro no **tick executado 10** (estado comprometido 11), assim como
A/C e B/C. Os 21 fingerprints de agentes diferem nesse tick, incluindo memórias dos
eventos distintos. A/B têm adoção **0,3809523810 vs 0,2857142857** e intenção média
**0,4596462872 vs 0,4375263394**; A/C têm intenção **0,4596462872 vs 0,4744422390**.
Os relatórios associam registros de eventos, modelo de adoção, threshold, memórias e
aprendizado de relações quando diferem. Fingerprint inclui memória/event IDs; agente
divergente não significa necessariamente uma mudança de adoção. É provenance interna.

## Perfil summary versus trace

Comando: `python -m benchmarks.audit --ticks 10,30,60 --seed 2026 --output results/m3-profile-20261001`.
Execução sequencial summary/trace em cada horizonte, sem outra suíte dos agentes em
paralelo. Uma seed, 21 agentes e três branches. O tempo inclui preflight, simulação,
relatórios e serialização canônica, excluindo escrita em disco. Bytes são a soma dos
JSON UTF-8 com LF (manifest, divergences, três runs). Todos os tamanhos foram conferidos
contra os arquivos reais. Os três hashes por branch coincidiram em todos os horizontes.

| Horizonte | Summary tempo | Trace tempo | Overhead tempo | Summary bytes | Trace bytes | Razão bytes |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 0,563358 s | 3,616264 s | +541,91% | 72.962 | 1.762.983 | 24,163× |
| 30 | 3,637748 s | 19,147803 s | +426,36% | 195.902 | 5.529.725 | 28,227× |
| 60 | 10,320634 s | 306,405316 s | +2.868,86% | 378.174 | 10.562.058 | 27,929× |

Summary retém zero registros completos. Trace retém 4.317/12.992/24.999 registros somados
nos três runs; os frames somam 30/90/180. Há 10/70/160 ticks físicos por modo porque a
origem é executada uma vez. Os artefatos de branches incluem o passado compartilhado.
No horizonte 10 nenhuma intervenção foi aplicada: trajetórias realizadas são iguais,
embora finalStateHash possa diferir pela fila futura agendada.

São medidas locais únicas, dependentes da carga da máquina, sem inferência de escala ou
intervalo de confiança. O custo de 60 ticks em trace foi muito superior ao de 30, enquanto
bytes cresceram menos que 2×. Ainda não há perfil CPU/memória que atribua quantitativamente
esse custo a cópia, validação, hashing ou carga externa. Não foi feita otimização nem
promessa de throughput. A próxima investigação deve medir essas fases antes de mudar
retenção/cópias; preservar os compromissos determinísticos é critério obrigatório.

## Arquivos e handoff

Código modificado: `futureos/randomness.py`, `models.py`, `engine.py`, `codec.py`,
`snapshots.py`, `validation.py`, `branches.py`, `__main__.py`.
Criados: `futureos/audit.py`, `futureos/audit_runs.py`, `benchmarks/audit.py`, cinco
suítes de teste novas listadas acima, este relatório e `docs/AUDIT_TRAJECTORIES.md`.

Documentação atualizada: README, CURRENT_STATE, NEXT_STEPS, ARCHITECTURE,
SIMULATION_ENGINE, DECISIONS, ROADMAP, HANDOFF e results/README. Resumos/estado/checkpoint
Harness e memória específica FutureOS são atualizados no encerramento; ID e memória
final ficam em CURRENT_STATE e `.harness/STATE.json`. Checkpoint final verificado:
[cp-2026-10-01T17-49-36-974Z](../.harness/checkpoints/cp-2026-10-01T17-49-36-974Z/checkpoint.json).
Memória oficial `04_PROJECTS/FutureOS/PROJECT.md` e sessão
`09_SESSIONS/2026-10-01/codex-14-49-35-FutureOS.md` escritas com sucesso. Resumos Harness
modificados: STATE.json, CURRENT_TASK.md, PROJECT.md, DECISIONS.md, MEMORY.md e LESSONS.md.
Scripts locais de aceite/handoff em results são ignorados, junto dos artefatos gerados.

Evidência local ignorada pelo Git: `results/m3-profile-20261001/benchmark.json`, seus seis
lotes e `results/m3-acceptance.json` (bytes, replay e exemplos). Fonte portátil: código,
testes, decisões e este relatório. Git continua `main` sem commits/remoto/publicação;
checkpoint Harness é resumo de desenvolvimento, não backup de código.

Próxima tarefa proposta: [perfil CPU e retenção do trace](NEXT_STEPS.md), antes de avançar
para providers/UI. Não há bloqueio funcional conhecido do aceite M3. Summary não oferece
auditoria detalhada; snapshots completos e cópias ainda crescem, hashes não autenticam e
o lote de arquivos não é uma transação. Não foram adicionados modelos reais ou calibração.
