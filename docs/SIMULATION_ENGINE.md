# Motor de simulação

Atualizado em 2026-10-01. M1 implementa o kernel legado e M3 acrescenta auditoria/RNG contextual explicitamente selecionados em `futureos/`, Python 3.13 stdlib. As capacidades futuras da [arquitetura](ARCHITECTURE.md) continuam propostas.

## Tempo e commit

`current_tick` é o próximo tick a executar. Estado no tick 10 significa que os ticks 0–9 foram concluídos. A unidade é `synthetic_step`, sem equivalência presumida com dia real.

Uma transição valida a entrada, faz cópia completa, aplica eventos ordenados por ID, seleciona agentes ativos ordenados por ID, observa estados depois dos eventos, calcula decisões, processa relações ordenadas por alvo, registra memórias, coleta métricas, incrementa o relógio e valida o resultado. Só então retorna o novo estado. Uma falha preserva o objeto do chamador.

Todas as decisões observam pares antes das novas decisões. Interações observam sentimento pós-evento; aprendizado da relação usa concordância entre decisões novas. Agentes inativos podem receber eventos, mas não decidem, interagem ou integram médias.

## Modelo provisório

Hipótese exclusivamente sintética, não calibrada:

```text
peer = soma(peso * adoptedDoPar) / max(1, soma(pesos))
peso = relação.trust * relação.influence * relação.strength * par.influence
score = clamp(
  .20 + .30*openness + .10*riskTolerance + .25*trust + .10*sentiment
  + peerWeight*conformity*peer
  - .30*priceSensitivity*max(0,preço-incentivo)/priceScale
  - .15*competitorPressure + noise
)
intent = clamp(.55*intentAnterior + .45*score)
adopted = intent >= adoptionThreshold
```

Clamp do score/intent é [0,1]. Adoção é reavaliada a cada tick, sem absorção permanente. Ruído uniforme em [-noise,+noise], uma amostra por agente ativo inclusive com amplitude zero.

Relação A → B significa que A observa B. Cada interação selecionada acrescenta `.02*peso*sentimentoDeB` à confiança de A e `.04*peso*sentimentoDeB` ao sentimento de A; sentimento também decai pelo fator configurado. Confiança da relação sobe/desce por `trust_learning_rate` conforme concordância de adoção. Valores permanecem em seus limites. Memórias registram eventos, interações e mudanças de adoção, sem acessar memória de desenvolvimento.

## Eventos

| Tipo | Payload |
|---|---|
| PRICE_CHANGE | price ≥ 0 |
| INCENTIVE | amount ≥ 0 |
| COMPETITOR_ENTRY | pressure em [0,1] |
| NEWS | sentiment_delta e/ou trust_delta em [-1,1] |
| TRUST_SHOCK | trust_delta em [-1,1] |

Alvos: todos, grupo em `agent.metadata.group` ou lista de IDs. Reach em [0,1] seleciona destinatários com o RNG da simulação. Grupos/IDs inexistentes, campos desconhecidos, payloads incompletos e números não finitos falham na validação.

Evento econômico universal (todos + reach=1) muda o ambiente e limpa o override correspondente nos agentes. Evento econômico parcial muda apenas o override dos destinatários. Condições persistem até serem substituídas por outro evento; incentivo não calcula receita ou dinheiro recebido. Eventos são da fase anterior às decisões.

`world.events` preserva definições passadas e futuras ordenadas por (tick,id); apenas eventos com tick igual ao relógio atual executam. `event_log` registra uma ocorrência, mesmo sem destinatários, com IDs atingidos. Agendar no passado ou repetir um ID é inválido. Nenhum evento passado se repete após retomada.

## Aleatoriedade

Algoritmo explícito `splitmix64-v1`, seed inteira sem sinal de 64 bits. Estado contém algoritmo, seed, estado interno e número de amostras; a validação confere consistência entre seed, contador e estado. `random`, `probability`, `choice` e `shuffle` passam por `SeededRandom`. Probabilidades 0 e 1 não consomem amostras. Não há random global no núcleo.

No caminho legado M1/M2, população consome a mesma stream cuja continuação é entregue à simulação. Cada branch restaura uma cópia dessa stream. Ordem de execução dos branches não altera resultados individuais. Mudanças na quantidade de destinatários/reach podem mudar consumo posterior. M2 usa `shared-origin-single-stream-v1`; ver [EXPERIMENTS.md](EXPERIMENTS.md).

M3 selecionado por `audit_mode` usa `sha256-path-splitmix64-v1`: população em stream separada; eventos por tick/evento/agente, decisões por tick/agente e interações por tick/par dirigido. Root seed e contexto reconstruem as streams, cujo consumo é independente. SplitMix64 permanece intacto. Derivação, endpoints, namespaces reservados e limites estão em [AUDIT_TRAJECTORIES.md](AUDIT_TRAJECTORIES.md).

## Snapshot e retomada

`create_snapshot` valida o estado em fronteira de tick e gera `Snapshot` frozen: identidade por conteúdo, schema 1, engine `futureos-kernel-v1`, JSON canônico do estado completo e SHA-256 do envelope versionado. Apenas uma string de JSON é armazenada no snapshot, sem objetos internos mutáveis.

Inclui mundo, configuração, status, seed/RNG, memórias, relações, overrides, eventos passados/futuros, log, métricas e metadados/linhagem. IDs não dependem de relógio real; não existe gerador global de IDs a preservar.

`Snapshot.to_json/from_json`, `restore_snapshot`, `save_snapshot/load_snapshot` implementam serialização e persistência UTF-8. Versões incompatíveis, checksum/ID incorretos, campos ausentes/desconhecidos, JSON duplicado e estado inválido são rejeitados. Salvamento usa arquivo temporário no mesmo diretório e substituição atômica; não é uma transação entre múltiplos artefatos. Checksum detecta corrupção, não autentica autor nem substitui controle de acesso.

Execução M3 cria schema2/engine `futureos-kernel-v2`, incluindo audit state, versões da derivação/trace, frames e registros retidos. Schema1/engine1 omite audit e mantém bytes/checksum legado. Pares cruzados são rejeitados. Decoder v2 conserva tipos JSON numéricos; restauração confere cadeias/endpoint. Resume mantém modo e hashes; não recalcula todo o passado. Frames referem-se a ticks executados; mudanças/eventos/decisões guardam provenance, e summary descarta o trace completo. Replay de artefato compacto reconstrói o cenário e verifica trajectoryHash, finalStateHash e eventTraceHash.

## Branch Reality

`create_branch(snapshot, BranchConfiguration(id, metadata))` restaura cópia completa: mundo, configuração, métricas e RNG começam iguais. Somente identidade da simulação e linhagem mudam. IDs de branches são fornecidos pelo chamador e devem ser distintos na comparação; não há registro global. Intervenções são agendadas após a criação, no tick da fronteira ou no futuro.

Executar/mudar um branch não modifica snapshot, pai ou irmãos. `compare_branches` exige IDs distintos, mesma origem, horizonte, configuração do modelo e IDs de população; devolve dados sem interpretação por LLM.

## Métricas

`adoption_rate`, `average_trust`, `average_sentiment` e `average_intent` são medidas do estado atual sobre agentes ativos, com zero para população ativa vazia. Adoção é uma fração [0,1], sentimento [-1,1]. `interaction_count` e `event_count` são contagens acumuladas desde o começo, preservadas no snapshot. Uma interação é um vínculo dirigido selecionado; um evento é uma ocorrência, não um destinatário.

## Limites

Sem LLM/provider, ferramentas externas, auditor Scientist autônomo, calibração, receita, eventos dinâmicos gerados por agentes ou armazenamento distribuído. Validação e testes realizam verificações determinísticas sem alterar a sociedade auditada. Cópias completas, memórias e histórico crescem com o horizonte; apropriados à fixture pequena. M2 mede repetições, sensibilidade, tempo, bytes de snapshots e memórias sem persistir estados completos de todo o lote; isso não prova escala fora do caso medido.
