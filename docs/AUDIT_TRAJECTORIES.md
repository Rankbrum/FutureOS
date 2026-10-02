# Auditoria de trajetórias, RNG e replay M3

Atualizado em 2026-10-01. Este documento descreve o contrato implementado em
`futureos/randomness.py`, `engine.py`, `audit.py`, `audit_runs.py`, `codec.py` e
`snapshots.py`. A evidência de execução e as medições ficam em [M3_REPORT.md](M3_REPORT.md).
M3 observa mecanismos do algoritmo; não calibra a sociedade sintética nem demonstra
causalidade ou probabilidade do mundo real.

## Versões e compatibilidade

| Contrato | Execução legada M1/M2 | Execução M3 explícita |
| --- | --- | --- |
| Engine | `futureos-kernel-v1` | `futureos-kernel-v2` |
| Snapshot | schema `1` | schema `2` |
| Gerador básico | `splitmix64-v1` | `splitmix64-v1`, reutilizado |
| Política de aleatoriedade | Uma stream sequencial por simulação | `sha256-path-splitmix64-v1` |
| Trace | Ausente | `futureos-trace-v1` |
| Modelo comportamental | `synthetic-adoption-v1` | `synthetic-adoption-v1` |

`create_simulation(...)` conserva o default legado. `audit_mode="summary"` ou
`audit_mode="trace"` seleciona M3; ambos usam as mesmas regras e os mesmos draws.
A fórmula de adoção continua a mesma, mas outra política de amostragem pode gerar
uma realização diferente. Resultados M1/M2 não são reescritos como M3.

Snapshot schema1 omite completamente a chave `audit`, preservando o formato,
checksum e identidade anteriores. O decoder insere `audit=None` somente quando o
payload tem exatamente os campos legados; não completa outros campos ausentes.
O envelope schema1 rejeita qualquer chave `audit`, inclusive `null`. Schema2
exige auditoria não nula e engine-v2. Combinações cruzadas ou versões desconhecidas
falham explicitamente. Não há migração silenciosa de snapshot ou stream consumida.

Cada snapshot M3 guarda estado completo e auditoria necessária à continuação. O
RNG raiz mantém a seed original e contador zero: população e draws de ticks não
avançam essa stream. A criação M3 rejeita `rng_state` já consumido. A restauração
verifica o checksum do envelope, o schema, as cadeias retidas da auditoria e,
quando existe último frame, seus hashes de estado/agentes contra o estado atual.
Valores inteiros aceitos em campos numéricos são preservados no JSON M3: `70` e
`70.0` têm bytes distintos e não podem mudar durante restauração de hashes. O
decoder legado mantém sua normalização histórica para `float`.

## Streams por contexto

`RandomStreams(root_seed)` é uma fábrica sem cache de geradores. `stream(namespace,
*path)` deriva uma seed e devolve um `SeededRandom` novo. A derivação codifica
domínio versionado, seed uint64 e componentes tipados do caminho em JSON canônico
UTF-8; inteiro `1` e string `"1"` são diferentes. Os oito primeiros bytes do
SHA-256, interpretados como inteiro big-endian, formam a seed da stream SplitMix64.

| Namespace | Caminho usado pelo motor | Consumo |
| --- | --- | --- |
| `population` | Sem componentes adicionais | Geração sequencial da população e relações dentro dessa stream |
| `events` | Tick executado, event ID, agent ID | Seleção de reach de um evento para um agente elegível |
| `decisions` | Tick executado, agent ID | Um draw de ruído por agente ativo, inclusive amplitude zero |
| `interactions` | Tick executado, source agent ID, target agent ID | Seleção de uma relação dirigida elegível |
| `social` | Reservado | Nenhum draw no modelo atual |
| `memory` | Reservado | Nenhum draw no modelo atual |

As chaves do motor não incluem branch ID, simulation ID, payload, reach, relógio
de parede ou caminho de arquivo. IDs de evento são identidades semânticas e fazem
parte do contexto; renomeá-los altera os draws correspondentes. Os eventos de
intervenção criados pelo runner possuem seus próprios event IDs.

Pedir a mesma chave novamente reinicia a stream e repete seus draws. O chamador
deve dar contexto único a usos independentes; a fábrica não sabe distinguir uma
nova ocorrência de uma repetição intencional. O motor inclui tick/agente/evento/par
para essa finalidade. Cada stream continua obedecendo os endpoints 0/1 sem draw
e o rejection sampling do SplitMix64 já existente.

Variar reach muda a seleção daquele evento, mas não desloca ruído das decisões,
seleção de interações ou reach de outros event IDs. A diferença social produzida
pelo evento ainda pode mudar decisões, relações e métricas legitimamente. A
stream `population` é sequencial: alterar seu algoritmo ou consumo pode mudar os
agentes subsequentes; M3 não promete independência por atributo da população.

Como os contextos de ticks são reconstruíveis, snapshots não carregam uma lista
crescente de estados/contadores por draw. População já realizada, seed raiz,
tick, identidades, eventos e versões bastam para continuar os contextos usados.
Novos mecanismos ou várias ocorrências dentro da mesma chave exigem uma política
explícita de caminhos e versionamento.

## Summary, trace e tempo lógico

Auditoria não é memória de um agente simulado. O motor registra proveniência em
`Simulation.audit`; as memórias sociais existentes continuam no mundo simulado.
Trocar `summary` por `trace` não muda sociedade, decisões ou aleatoriedade.

`summary` retém um frame por tick: fingerprint do estado realizado, fingerprints
dos agentes, unidade, denominador ativo e seis métricas. Mantém hashes incrementais da trajetória e de todos
os registros emitidos, mais `trace_count`; os registros detalhados são descartados
depois de contribuir ao hash. Portanto summary ainda constrói e processa registros
transitórios. Não recupera posteriormente sua ordem detalhada ou contribuições;
verificar novamente a cadeia completa de registros exige reconstrução por replay.

`trace` conserva esses mesmos frames e hashes, além da sequência detalhada:

- `tick_started` e `tick_completed`;
- `event_applied`, com evento, payload, reach e destinatários realizados;
- `adoption_decision`, com score, threshold, intenção anterior/nova, componentes
  da fórmula e observações de pares;
- `interaction_created` e `influence_applied`;
- `state_changed` e `relationship_changed`, com campo, `before`, `after` e
  contribuições quando disponíveis. Relações registram `source_agent_id` e
  `target_agent_id` estruturados, sem inferir participantes por prefixo textual.

Uma ausência de delta significa que o valor permaneceu igual; decisões e eventos
ainda podem ter registros próprios. As contribuições nomeiam termos do algoritmo,
inclusive clipping e aprendizagem que podem impedir soma direta de diferenças
observadas. Não constituem explicação causal de comportamento humano.

`current_tick` aponta para o próximo tick. Frame/registro com `tick=0` pertence à
execução do tick 0; o frame é coletado após seu commit, quando o estado está no tick 1.
O registro `tick_completed` informa esse instante em `payload.state_tick`.
O frame externo expõe `stateTick = tick + 1`, `tickUnit` e `activeCount`; não há conversão implícita
para dias. A unidade permanece `synthetic_step`. O runner inclui a trajetória da
origem compartilhada: horizonte 30 contém frames dos ticks 0–29, não apenas a
continuação após a bifurcação.

As quatro médias/taxas usam agentes ativos como denominador, com vazio igual a
zero. Interações e eventos são contagens cumulativas desde tick 0, incluindo o
passado compartilhado. O último frame concorda com as métricas finais do run.

## Significado dos hashes

JSON canônico usa chaves ordenadas, separadores compactos, Unicode UTF-8 e números
finitos. Ordem de agentes é normalizada por ID; relações de cada agente são
normalizadas por target ID. Ordem de memórias e event log permanece significativa.

| Hash | Conteúdo |
| --- | --- |
| Fingerprint de agente | Agent completo: ID, traits, state, relações, memória e metadata |
| `stateHash` de frame | Seed, configuração, `current_tick` após commit, condições globais, agentes, event log e métricas |
| `finalStateHash` | Conteúdo do estado realizado, mais status operacional, todas as definições de eventos ordenadas por tick/ID, RNG raiz, world metadata e versões de engine/RNG |
| `trajectoryHash` | Cadeia ordenada de frames desde o cabeçalho de origem e versões |
| `eventTraceHash` | Cadeia ordenada de todos os registros emitidos, retidos ou transitórios |

Os hashes do estado realizado excluem eventos futuros/definições, RNG raiz,
world metadata, status operacional e cabeçalho de versões. Eles medem diferenças realizadas; agendas
diferentes sozinhas não antecipam o primeiro tick divergente. `finalStateHash`
inclui essas definições porque elas afetam continuação.

Ambos os hashes de estado excluem simulation ID, world ID, simulation
metadata/linhagem e auditoria inteira. Fingerprints de agentes incluem seus IDs e
metadata. Branch label, audit mode, duração, timestamps operacionais e caminho de
saída não entram nos três hashes finais. Conteúdo explicitamente declarado em
metadata/payload continua participando conforme a tabela; não é removido por ter
um nome temporal. `finalStateHash` não é o checksum do snapshot: o
snapshot integral também contém identidade, linhagem e auditoria.

Marcar uma simulação como completed pode mudar `finalStateHash` sem alterar os
frames e a trajetória já comprometidos, pois somente o hash final inclui status.

O cabeçalho das cadeias contém `initialStateHash`, `engineVersion`, `rngVersion`
e `traceVersion`. A trajetória começa com SHA-256 do JSON `{"trajectory": header}`;
o trace começa com `{"trace": header}`. Cada atualização calcula SHA-256 dos bytes
do digest anterior concatenados ao JSON canônico do próximo frame/registro interno.
Os nomes internos desses dataclasses são snake_case; o artifact externo não
redefine os bytes da cadeia ao expor campos camelCase.

Summary e trace têm os mesmos três hashes quando contexto e comportamento são
iguais; seus snapshots completos podem ter checksums diferentes porque armazenam
auditoria diferente. Hashes detectam conteúdo alterado, não autenticam o autor.

## Artefatos de execução e API

M3 grava seu próprio contrato `artifactVersion=1`, campos de proveniência camelCase
e `replayProtocol="scenario-rebuild-v1"`. Não passa pelos summaries snake_case ou
agregação legada M2. Configuração, nomes das seis métricas e payloads do motor
preservam os contratos internos existentes.

Um run contém cenário completo, checksum, seed, engine/RNG/trace versions,
configuração, branch/intervenções, horizonte, referência completa da origem,
`finalStateHash`, `trajectoryHash`, `eventTraceHash`, métricas, frames e registros
opcionais. Summary mantém `records=[]`. O manifesto contém as seeds canônicas e
IDs de runs; `divergences.json` reúne os pares de irmãos. Os arquivos indexados
ficam em `runs/run-000001.json`, etc. A saída deve ser diretório novo ou vazio.

Os IDs são derivados do protocolo/conteúdo e de seed/branch; excluem modo de
auditoria, tempos e caminhos. A referência `originSnapshot` deve preservar ID,
checksum, schema/engine, tick e state hash exatos. Um run não contém snapshot final
completo: permite reconstruir o cenário por replay, não retomar diretamente o
estado final. Para pausa/retomada, usar a API de snapshots do kernel.

```python
from futureos.audit_runs import (
    compare_run_divergence, load_run_artifact, replay_run,
    run_audit_experiment, save_audit_experiment, trajectory_from_run,
)

result = run_audit_experiment(seeds=[2026], ticks=30, mode="trace")
save_audit_experiment(result, "results/m3-example")
report = replay_run(load_run_artifact("results/m3-example/runs/run-000001.json"))
pair = compare_run_divergence(result.runs[0], result.runs[1])
agent_records = trajectory_from_run(result.runs[0], "agent-001")
```

`trajectory_from_run` recupera registros de um agente diretamente do artifact
trace. A seleção usa entidade exata e IDs estruturados de origem/destino, além de
destinatários de eventos; IDs com prefixos semelhantes não se confundem.
Para uma sociedade mantida pela API do kernel, `futureos.audit.agent_trajectory`
recebe a simulação e um agent ID. Exige modo trace e retorna mudanças do agente,
eventos recebidos e interações de entrada/saída selecionadas. Não modifica o mundo.

## Replay e divergência

Replay valida schema e versões suportadas antes de executar ticks. Reconstitui a
população, origem e branch pelo protocolo declarado. Primeiro confere contexto
coerente — cenário/checksum, configuração, intervenção, identidade e horizonte —,
depois a origem reproduzida e o conteúdo realizado. Versão desconhecida ou artefato
malformado falha; contexto suportado mas adulterado produz `matched=false`.

`firstDivergence` identifica a primeira diferença detectável pela evidência
disponível: contexto/origem, registro detalhado quando existe, frame e, por fim,
hash/summary. Um hash final alterado sozinho não permite inventar tick, agente ou
mecanismo. O relatório compara separadamente os três hashes; `detailAvailable`
explica se há trace para localizar alterações dentro do tick. Uma reconstrução
igual evidencia determinismo daquele protocolo, não validade externa do modelo.

`compare_run_divergence` exige mesma seed, cenário/conteúdo, configuração,
bifurcação, horizonte, versões e origem de snapshot exata. Não relaxa esse contrato
para comparar origens diferentes. Retorna `firstTick`, fingerprints de agentes
divergentes e métricas naquele tick; `firstMetricsTick` registra separadamente a
primeira diferença nas métricas. Somente dois artifacts trace fornecem diferenças
de registros e mecanismos detalhados.

Fingerprint de agente inclui memória: receber outro event ID pode diferenciá-lo
mesmo com valores comportamentais iguais. Agendas futuras diferentes podem mudar
`finalStateHash` sem diferença em frames já concluídos. `identical` no relatório
de divergência significa igualdade dos estados realizados ao longo dos frames,
não igualdade de todos os protocolos ou definições futuras.

## CLI e perfil

Na raiz, Python 3.13 e biblioteca padrão:

```powershell
python -m futureos audit --seeds 2026 --mode trace --ticks 30 --output results/m3-example
python -m futureos replay results/m3-example/runs/run-000001.json
python -m futureos trajectory results/m3-example/runs/run-000001.json --agent agent-001
python -m futureos divergence results/m3-example/runs/run-000001.json results/m3-example/runs/run-000002.json
python -m benchmarks.audit --ticks 10,30,60 --output results/m3-profile
```

Nesta máquina, a convenção local é prefixar comandos com `rtk proxy`; o produto
não depende de RTK. O benchmark executa summary e trace sequencialmente em cada
horizonte, confere identidade e os três hashes de cada branch, e registra tempo,
bytes canônicos UTF-8, frames e registros retidos, com razões de custo. O tempo
inclui preflight, simulação, relatórios e serialização; exclui escrita em disco.
O horizonte 10 coincide com a bifurcação da fixture: intervenções permanecem
agendadas. Tempos dependem da carga da máquina. Dados medidos, verificações e
limites efetivos pertencem a [M3_REPORT.md](M3_REPORT.md), sem valores presumidos
neste protocolo.

Frames/fingerprints crescem com agentes e horizonte; trace conserva ainda mais
registros, e os estados sociais mantêm suas memórias. Não há compactação ou banco
externo presumidos. O perfil orienta propostas posteriores de otimização. M3 não
introduz web, LLM, provider, serviço externo ou previsão garantida.
