# Decisões do FutureOS

Data de abertura: 2026-09-29. Este arquivo é o registro único de decisões técnicas do projeto; referências em `.harness` e arquivos de cada IA apontam para ele.

## D024 — Publicar o worktree preservando a visibilidade privada

**Data:** 2026-10-01. **Status:** autorizada pelo Founder e executada; commit/envio verificados no estado atual.

**Contexto:** Git local `main` sem commits, remoto existente `Rankbrum/FutureOS`
vazio e privado, com permissão de administração disponível.

**Decisão:** criar histórico e enviar o worktree ao remoto existente, preservando
a visibilidade privada e sem force push. Publicar docs/fontes/testes/fixtures e
resumos Harness; ignorar workspace pessoal do Obsidian e marcador de tentativa.

**Alternativas:** criar outro repositório duplicaria o destino configurado;
tornar público ampliaria o acesso sem necessidade; publicar apenas o núcleo
omitiria trabalho preexistente. Reescrever protótipos excederia a tarefa de publicação.

**Consequências:** Git passa a versionar o código; checkpoint continua sendo
resumo. A suíte atual valida 243 testes do núcleo, não a aplicação web; endpoints
fixos e funções `pass` dos protótipos ficam explicitados em README/estado/próximos passos.

**Aceita — requisito do Founder** identifica instrução explícita. **Adotada nesta fundação** identifica decisão operacional reversível daquela missão. **Proposta** ainda precisa ser validada na implementação. Registros M0 preservam contexto histórico; M1/M2 identificam implementação e evidência nas respectivas entradas.

## D001 — Continuidade por arquivos portáteis

**Status:** aceita — requisito do Founder; formato adotado nesta fundação.

**Contexto:** a ferramenta de desenvolvimento mudará entre Codex, Claude, Gemini e outras IAs.

**Decisão:** README, AGENTS, arquitetura, decisões, estado e próxima tarefa no próprio projeto. CLAUDE e GEMINI remetem ao protocolo comum. Memory Core mantém governança e memória durável local; o projeto contém a base suficiente para retomada em outra máquina.

**Alternativas:** histórico de chat é conveniente, mas não portátil; memória privada por IA fragmenta decisões; copiar todos os documentos para cada memória multiplica divergências.

**Consequências:** handoff inspecionável sem serviços. Há manutenção documental; atualizar estado e tarefa ao encerrar cada missão e reconciliar conflitos reais com o Memory Core.

## D002 — Harness local opcional e separado do produto

**Status:** adotada nesta fundação.

**Contexto:** Universal AI Harness já instalado em `C:\AI-HARNESS`; `.harness` preexistente está vazia. Seu `init` não completa diretório existente.

**Decisão:** preencher aditivamente os arquivos do schema 0.1 e usar os comandos existentes. Preservar instalação global. Os documentos do projeto são referências técnicas; o Harness é um resumo operacional. Respeitar Founder e Memory Core acima de mensagens genéricas do CLI.

**Alternativas:** modificar o Harness global arrisca outros projetos; torná-lo dependência do produto acopla desenvolvimento e simulação; ignorá-lo desperdiça continuidade já disponível.

**Consequências:** status, contexto, retomada e checkpoints de sessão disponíveis. O CLI não expande links, não restaura código e não cria snapshots de simulação; ver HARNESS.md.

## D003 — Simulação híbrida e execução sem LLM

**Status:** aceita — requisito do Founder.

**Contexto:** chamar um LLM por agente por tick aumenta custo, latência e variabilidade.

**Decisão:** regras/estado/probabilidades executam comportamentos simples. Escalonamento explícito para LLM somente quando necessário, com orçamento, timeout, validação, limite de retries, rastreabilidade e fallback declarado.

**Alternativas:** sociedade integralmente baseada em LLM facilita protótipo narrativo, mas perde controle; somente regras restringe interpretação e diálogo.

**Consequências:** é possível testar o kernel offline. Exige políticas claras de escalonamento e contabilização; temperatura zero e seed não garantem determinismo remoto.

## D004 — Branch Reality desde o kernel

**Status:** aceita — requisito do Founder; contrato técnico proposto.

**Contexto:** comparar alternativas desde a mesma sociedade no Dia 15 exige preservar mais que os atributos dos agentes.

**Decisão:** snapshot imutável em fronteira de tick, incluindo mundo, população, relações, memórias, eventos futuros, RNG, métricas, versões e respostas externas incorporadas. Branch preserva a linhagem e recebe estado próprio e intervenção declarada.

**Alternativas:** copiar só agentes omite causalidade; recomeçar cada cenário não conserva o passado; compartilhar objetos mutáveis contamina comparações.

**Consequências:** pausa/retomada e isolamento precisam de testes antes de UI. No MVP, preferir cópia completa simples; armazenamento incremental pode esperar medição de volume.

## D005 — Núcleo modular em um processo

**Status:** adotada em M1 (2026-09-30), com layout físico registrado em D010.

**Contexto:** não existe código nem carga medida que justifique infraestrutura distribuída.

**Decisão:** começar com módulos lógicos dentro de um processo, executáveis por CLI/testes; preservar as pastas já criadas. Web chama casos de uso do Core futuramente.

**Alternativas:** microserviços aumentam coordenação e operação; um script monolítico sem contratos dificultaria snapshot, provider e auditoria; frameworks de agentes exigem avaliação técnica.

**Consequências:** menores custos iniciais; interfaces devem permitir evolução sem antecipar filas, Kubernetes ou bancos de grafos.

## D006 — Stack ainda não contratada

**Status:** proposta original substituída por D010 em 2026-09-30; preservada como histórico.

**Contexto:** máquina dispõe de Python 3.13 e Node 24, mas não há manifestos de projeto. Python/SQLite do IA-Memory-System pertence a outro projeto.

**Decisão:** candidata para o kernel: Python 3.13 com biblioteca padrão, pela execução local, serialização, testes e RNG controlável sem instalação. Avaliar contra TypeScript pelo custo de eventual compartilhamento com web. Decidir antes do primeiro código; fixar versão e comandos no projeto. Framework web, banco, SDK LLM e orquestrador ficam adiados.

**Alternativas:** TypeScript permite compartilhamento de linguagem com UI, mas requer escolher tooling; Python não elimina a necessidade futura de contratos com a web.

**Consequências:** esta missão não instala nem fixa dependências. Nenhuma capacidade exclusiva dos runtimes empacotados no Codex deve ser requerida pelo produto.

## D007 — Scientist audita; resultados são condicionais

**Status:** aceita — requisito do Founder; execução proposta.

**Contexto:** população sintética e comportamento de LLM podem criar conclusões artificiais.

**Decisão:** separar modelo comportamental, observação e auditoria. Começar por invariantes e relatórios computáveis; Scientist analisa premissas, viés, sensibilidade, inconsistências e variância sem modificar execuções auditadas.

**Alternativas:** um LLM certificando a própria narrativa cria auditoria circular; apresentar frequência sintética como probabilidade real produz confiança indevida.

**Consequências:** relatórios incluem origem, limites e resultados por seed; validade externa requer calibração com dados reais. Não emitir um selo único de confiabilidade sem método justificado.

## D008 — Capacidades da máquina não são permissões de agentes

**Status:** adotada nesta fundação.

**Contexto:** skills e MCPs do ambiente de desenvolvimento incluem acesso a arquivos, navegação e sistemas externos.

**Decisão:** inventariá-los como ferramentas de desenvolvimento. Agentes simulados recebem apenas capacidades explícitas e versionadas do cenário, via adaptadores e política de efeitos. No kernel inicial, nenhuma ferramenta externa.

**Alternativas:** herdar automaticamente todos os MCPs dá conveniência, mas contamina simulação e expõe dados/efeitos reais.

**Consequências:** memória do Founder, credenciais e filesystem pessoal não entram no mundo simulado; cache/replay deve respeitar contexto, versão e isolamento de branch.

## D009 — Não inicializar Git implicitamente durante a auditoria

**Status:** adotada nesta fundação.

**Contexto:** FutureOS não é repositório Git e não herda um repositório pai.

**Decisão:** registrar a ausência, preparar `.gitignore` e recomendar versionamento local como primeiro passo da próxima missão. Nenhum commit, remoto ou publicação nesta etapa.

**Alternativas:** criar Git agora seria reversível, mas não é necessário para comprovar a auditoria ou documentação solicitadas.

**Consequências:** arquivos persistem, mas não há histórico ou rollback via Git. Checkpoints do Harness não cobrem essa lacuna.

## Como registrar a próxima decisão

Adicionar ID crescente, data, status, contexto, decisão, alternativas e consequências. Referenciar a evidência de validação. Quando uma escolha mudar, marcar a anterior como substituída e apontar para a nova; preservar o motivo original.

## D010 — Kernel Python local sem dependências

**Data:** 2026-09-30. **Status:** adotada para M1; substitui a proposta D006.

**Contexto:** o Founder autorizou o primeiro kernel, sem web nem LLM obrigatório. Python 3.13.15 está disponível pelo launcher da máquina.

**Decisão:** Python 3.13 com biblioteca padrão; pacote `futureos` na raiz, CLI por `python -m futureos` e testes por `unittest`. Os diretórios conceituais preexistentes são preservados; criar somente módulos com comportamento. Git local inicializado em `main`, sem remoto ou publicação. Nenhum commit automático nesta missão.

**Alternativas:** TypeScript exigiria escolher tooling; pacotes separados por cada camada antecipariam interfaces ainda sem comportamento. Instalar um framework não ajuda a provar os invariantes iniciais.

**Consequências:** execução direta sem instalar pacotes, Harness ou ferramentas de IA. Os contratos Python usam snake_case; uma interface externa futura deve versionar seu formato. A demo atual autorizada usa 10 ticks antes do snapshot e 20 depois, substituindo o horizonte proposto de Dia 15 para esta fixture.

## D011 — RNG e snapshots completos versionados

**Data:** 2026-09-30. **Status:** implementada em M1; materializa D004.

**Contexto:** seed sozinha não reproduz continuação após amostras da população ou ticks. Objetos mutáveis compartilhados contaminariam Branch Reality.

**Decisão:** SplitMix64 explícito, seed uint64, estado e contador; probabilidades 0/1 sem amostra, uma amostra de ruído por agente ativo mesmo com noise=0. Snapshot frozen com JSON canônico, schema/engine versionados, SHA-256 e identidade por conteúdo. Restauração reconstrói todo o agregado; persistência usa substituição em um arquivo. Branch nasce com mundo/configuração/métricas/RNG iguais, identidade/linhagem próprias; intervenções são agendadas depois.

**Alternativas:** RNG global ou seed isolada perdem posição da stream; random.Random serializado acoplaria formato ao runtime; cópia parcial perde causalidade; copy-on-write anteciparia otimização.

**Consequências:** continuação, isolamento e ordem dos branches têm testes. Cópia completa custa memória; SHA-256 detecta corrupção e não autentica snapshots. Formato incompatível exige migração explícita. Uma stream por simulação acopla consumo entre mecanismos; streams pareadas ficam para protocolo posterior.

## D012 — Semântica sintética e comparação numérica

**Data:** 2026-09-30. **Status:** implementada em M1.

**Contexto:** é necessário comportamento suficiente para testar infraestrutura, sem afirmar modelo científico ou adotar escolhas comerciais ausentes.

**Decisão:** eventos antes das decisões, observação síncrona dos pares, IDs ordenados, vínculos dirigidos e fórmula explícita em SIMULATION_ENGINE. Adoção é reavaliada em cada tick. Eventos econômicos parciais criam overrides por agente; universais mudam ambiente e limpam o override correspondente. Histórico de definições/event_log é preservado. Médias/fração usam agentes ativos; contagens são acumuladas. Comparação exige origem, seed, configuração, horizonte, elegibilidade e linhagem coerentes.

**Alternativas:** mutação sequencial durante decisões favoreceria ordem de iteração; evento global ignorando target/reach atingiria agentes indevidos; adoção irreversível saturaria rapidamente a fixture; inferência LLM não é necessária à comparação.

**Consequências:** fixture com threshold 0,52, 21 agentes e preços/incentivo declarados produz diferenças verificáveis. Não calcula receita ou mensalidade, não é calibração e não permite previsão real. Cópias/validação rejeitam estado inválido e aliases comportamentais compartilhados entre agentes. Memórias e logs crescem com o horizonte.

## D013 — Experimentos pareados e estatística populacional

**Data:** 2026-09-30. **Status:** implementada em M2; requisito multi-seed aceito do Founder, formato técnico adotado.

**Contexto:** uma seed e uma média escondem dispersão e não permitem avaliar diferenças entre branches em um conjunto sintético.

**Decisão:** `experiments.py` executa seeds uint64 distintas em ordem canônica e cria uma origem íntegra por seed, compartilhada por branches independentes. Horizonte é total, com bifurcação declarada. Reutiliza o cenário schema1 da M1; scenario ID versionado + checksum de conteúdo e protocolo/seed/branch geram IDs estáveis. Summary de SimulationRun identifica versões, configuração, intervenção, população ativa, hashes, status e seis métricas. Manifesto completo, runs, agregação e comparação têm contratos JSON schema/report1, snake_case. Estatísticas usam count/mean/median/min/max e variância/desvio populacionais (N; singleton zero), preservando `{seed,run_id,value}`. Comparação pareada conserva sinais, maiores/menores/empates e distribuição de deltas. Diferencia delta de mediana e mediana dos deltas. Maior não implica melhor.

**Alternativas:** grupos independentes por branch confundem intervenção com população/amostragem; média isolada omite variabilidade; desvio amostral sugere inferência de uma população externa que não foi definida; depender de NumPy não é necessário para esse volume.

**Consequências:** reproduzibilidade exclui timings variáveis, armazenados separadamente. Validadores rejeitam mistura de horizonte/configuração/versões/intervenção, campos incompletos, origem/elegibilidade incompatíveis e pareamento incompleto. A política `shared-origin-single-stream-v1` mantém RNG M1; não promete choques iguais por mecanismo quando consumo diverge. Evidência em EXPERIMENTS e M2_REPORT. Frequência é do espaço simulado, nunca probabilidade real.

## D014 — Sensibilidade local OAT com baseline explícito

**Data:** 2026-09-30. **Status:** implementada em M2; escopo aceito do Founder, aplicação técnica adotada.

**Contexto:** atributos dos agentes e parâmetros de eventos/intervenções precisam ser perturbados sem contaminar outra execução ou relaxar o contrato de Branch Reality.

**Decisão:** protocolo JSON versionado define fatores individuais, valores e baseline. Cada fator produz experimentos próprios nas mesmas seeds/horizonte/branches, com preflight de todas as variantes antes do primeiro tick. População: override absoluto de um atributo para todos os agentes no tick zero, depois da geração, sem novo draw; grupos da fixture permanecem fixos, traits especiais do influenciador também são sobrescritos. Eventos: alterar reach ou campo existente do payload pelo event_id. Branches: price/incentive pelo branch_id. Baseline populacional uniforme não é confundido com distribuição original. Deltas entre variantes são pareados por branch/seed; não passam pela comparação de branches de origens distintas. Especificações equivalentes podem reutilizar resultado compacto com cópias isoladas. Manifestos e resultados de cada variante são preservados; timing separado.

**Alternativas:** aplicar deltas relativos mudaria a semântica perto dos limites e exigiria outra política; variar simultaneamente vários parâmetros dificultaria atribuição; análise global exige desenho adicional; afrouxar compare_branches permitiria comparações indevidas. Nenhuma análise generativa é necessária.

**Consequências:** análise local explora comportamento do modelo; não identifica causalidade real nem interação global dos fatores. Alterar reach, especialmente 0/1, pode mudar alinhamento da stream. Exemplos verificáveis cobrem price_sensitivity, NEWS reach e incentivo. Validações/testes cobrem também amount de INCENTIVE e os seis atributos candidatos.

## D015 — Armazenamento mínimo e benchmark antes de otimizar

**Data:** 2026-09-30. **Status:** implementada em M2; decisão operacional adotada.

**Contexto:** persistir snapshots completos de todos os runs duplicaria mundo/memória/logs sem necessidade para agregação, e escala ainda não foi medida.

**Decisão:** lote guarda manifest/aggregate/comparison/sensitivity/benchmark e arquivos indexados de runs, com métricas e referências/checksums. Snapshots completos existem transitoriamente por seed, com sizing e contagens de memória, e são liberados. M1 conserva API de retomada. `perf_counter` mede preflight, simulação, sizing e relatórios; output de disco fica fora. Run recebe tempo da continuação + quota igual da origem comum; overhead aparece só no total. Benchmark reproduzível verifica campos determinísticos em segunda execução; tempos não entram em igualdade. Saída exige diretório ausente/vazio para não misturar lotes. CLI limita materialização a 100.000 seeds; API não introduz esse limite. Nenhuma dependência, paralelo de runs ou otimização do kernel.

**Alternativas:** manter todos os estados finais facilita retomada mas aumenta volume; banco externo/armazenamento incremental/worker pool não se justificam antes das medidas; sobrescrever lote existente silenciosamente perde evidência; omitir preflight/sizing subestimaria o custo real desse comando.

**Consequências:** summaries não permitem retomar do estado final; reprodução usa protocolo completo. Arquivos não formam transação de lote, e erro de disco pode deixar saída parcial. Checksums não autenticam autor. Benchmark é evidência local, sujeita à carga concorrente da máquina. Medidas e limite de escala constam em M2_REPORT. Checkpoint Harness continua sendo resumo de desenvolvimento, separado do snapshot de produto e de backup/Git.

## D016 — Streams indexados sobre SplitMix64, sem migração silenciosa

**Data:** 2026-10-01. **Status:** implementada em M3; isolamento requerido pelo Founder, granularidade técnica adotada.

**Contexto:** a stream única M1/M2 acopla draws posteriores ao consumo de eventos. O gerador existente já é SplitMix64 e não requer substituição.

**Decisão:** preservar `splitmix64-v1`. `sha256-path-splitmix64-v1` deriva seeds uint64 por SHA-256 de JSON canônico com domínio, root seed e caminho de segmentos tipados; oito primeiros bytes big-endian. População usa uma stream sequencial própria. Eventos usam `(events,tick,event_id,agent_id)`, decisões `(decisions,tick,agent_id)` e interações `(interactions,tick,source_id,target_id)`. Social/memory ficam reservados, sem sorteios artificiais. Payload, reach, ID do branch e relógio não integram essas chaves. Cada chamada reinicia uma stream indexada; o engine usa cada contexto uma vez por mecanismo/tick. Não manter cache nem milhares de counters.

**Alternativas:** streams sequenciais por mecanismo isolam mecanismos mas permitem desalinho entre agentes/ticks; counters por agente/evento exigem crescer snapshots; trocar o gerador base perde compatibilidade sem resolver o problema da derivação. Draws indexados fornecem a granularidade necessária neste kernel pequeno.

**Consequências:** semântica nova é engine `futureos-kernel-v2`, escolhida por `audit_mode`; defaults, CLI demo/experiment e snapshots schema1 continuam v1. Schema2/engine2 preserva root seed, política e fronteira de tick, suficientes para retomar contextos indexados. População não continua sendo sorteada durante ticks. Algoritmo, derivação e semântica são versões distintas. Vetor canônico, processos com diferentes PYTHONHASHSEED, reach, elegibilidade, retomada e permutações têm testes. D011/D013 permanecem contratos legados.

## D017 — Provenance incremental e dois níveis de retenção

**Data:** 2026-10-01. **Status:** implementada em M3.

**Contexto:** resultados finais ocultam mudanças transitórias e mecanismos; guardar o mundo completo em cada mudança duplicaria o estado.

**Decisão:** trace-v1 guarda registros estruturados de ticks, eventos, decisões, interações, influências, deltas e relações. Deltas identificam entidade, campo, antes/depois, mecanismo e tick; contribuições e participantes de relações são campos estruturados. A coleta é um campo próprio de Simulation, separado da memória dos agentes e sem draws adicionais. Summary descarta registros completos, conservando fingerprints por agente, métricas, unidade e denominador por tick. Trace conserva esses compromissos mais os registros. Ambos calculam os mesmos hashes incrementais.

**Alternativas:** logs narrativos não permitem consulta computável; mundos completos por tick custam armazenamento; somente hashes finais impedem localizar o primeiro tick divergente; event sourcing integral exigiria registrar outras mutações e uma reconstrução de estado que não foi solicitada.

**Consequências:** `tick` identifica a transição executada e `stateTick=tick+1` o estado comprometido. Trajetória detalhada exige trace; summary recupera métricas/fingerprints, sem inventar detalhes ausentes. Cada modo ainda custa cópias/validação; M3 mede 10/30/60 antes de propor otimização. Deltas descrevem provenance do algoritmo, nunca causalidade do mundo real. Medidas/evidência em M3_REPORT e protocolo em AUDIT_TRAJECTORIES.

## D018 — Artefatos M3, hashes e replay versionados

**Data:** 2026-10-01. **Status:** implementada em M3.

**Contexto:** novo RNG/trace não pode reinterpretar artefatos anteriores; auditoria precisa reproduzir o protocolo e localizar divergências verificáveis.

**Decisão:** manter formatos M1/M2 e criar artefato M3 `artifactVersion=1`, camelCase, com runId/experimentId, seed, scenarioVersion/schema/checksum, engineVersion/rngVersion/traceVersion, cenário completo, configuração, intervenção, origem e horizonte. `finalStateHash` SHA-256 inclui estado de continuação/fila/status, excluindo identidade/linhagem e auditoria. `trajectoryHash` encadeia frames dos estados realizados; `eventTraceHash` encadeia todos os registros, mesmo quando summary os descarta. Relógio e modo não entram em IDs/hashes. Snapshot schema2 inclui auditoria; modo altera bytes/checksum do snapshot, sem alterar os hashes comportamentais.

Replay `scenario-rebuild-v1` rejeita versões desconhecidas antes dos ticks, reconstrói cenário/seed/configuração/branch e verifica os três hashes, incluindo obrigatoriamente trajectoryHash. Compara contexto, primeiro record/frame detectável por tick e depois hashes finais. Divergência exige origem exata, seed, configuração, versões e horizonte; informa primeiro tick/agentes/métricas e registros internos associados quando há trace.

**Alternativas:** atualizar todos os summaries M2 invalidaria seus IDs; migrar RNG de um snapshot em andamento alteraria sua continuação; hash nativo de Python não é persistente; reter somente hash final limita localização de divergência. Nenhum banco/dependência adicional é necessário.

**Consequências:** versões suportadas são pares exatos schema1/engine1 e schema2/engine2. Decoder v2 preserva tipos JSON numéricos aceitos pelo kernel para não alterar hashes; v1 conserva sua coerção histórica. Restauração verifica cadeia e endpoint retidos. Mudança de fórmula/ordem/derivação exige nova engine/RNG; mudança de registros exige nova trace; mudança incompatível de envelope/artefato exige novo schema/artifact. Não há migração automática. Artefatos compactos reexecutam o cenário e não retomam do estado final. Hashes não autenticam autores; diferenças internas não inferem causalidade real. `identical` da comparação refere-se a estados realizados, não à fila futura de intervenções.


## D019 — Validação M6.1 por execução atual e identidade por conteúdo

**Data:** 2026-10-01. **Status:** adotada/executada; requisito explícito do Founder.

**Contexto:** ambiente anterior não executou suíte/bench/profile; M4/M5/M6
misturavam inspeção e referência histórica com alegações de implementação.
Git main sem commits não permite atribuir diff histórico a M5/M6.

**Decisão:** suíte atual164/164OK24,373s, 18 benchmarks independentes10/30/60,
cProfile trace60/consulta e comparação histórica descritiva em M6_1_VALIDATION.
Manifesto SHA-256 identifica versão; fontes originais conferidas inalteradas.
Bytes/hashes invariantes verificados. Piloto120958,523s torna três repetições
opcionais não razoáveis nesta missão: singleton sem mediana. COMPLETE refere-se
à validação, não a um core M6 reescrito.

**Alternativas:** reaproveitar os164 testes/timings históricos não provaria a
versão; ignorar o extremo60 esconderia dispersão; atribuir diferença a M5 sem
diff/controle não tem evidência causal. Criar commit não integra esta missão.

**Consequências:** M4/M5 retificados; deepcopy(rows) contratual permanece, índice
sem integração e append-only imutável ausente. M6_TRACE_CORE ausente/não criado.
Logs/números/rankings portáteis; artefatos grandes ignorados. Checkpoint é resumo.
Mesmo cenário/escopo não garante hardware/carga iguais ao M3 histórico.

## D020 — Manter hash-v1; priorizar cópias e validação histórica

**Data:** 2026-10-01. **Status:** decisão baseada no profile atual; nenhum algoritmo novo.

**Contexto:** canonical_json acumulou21.625435s,
6.02% de pstats trace60 (validação/JSON incluídos); deepcopy
171.817730s cumulativos. Não somar linhas aninhadas. _chain de
records/frames já é incremental v1. _agent_data/_state_data materializam memórias
crescentes e commit_frame repete agentes para hashes de mundo/indivíduo.

**Decisão:** não implementar nem promover nova versão de hash nesta validação.
canonical_json é6,02% cumulativo e _chain1,24% do pstats, frente a deepcopy47,84%
e validate_simulation37,44%. Cumulativos se sobrepõem e instrumentação altera
custos relativos. Custos secundários não justificam migração quando a prioridade
medida é cópia/revalidação de histórico. _chain v1 já é incremental.

**Alternativas prioritárias:** golden/diferencial moderno v1, materialização única
de agentes por commit, reaproveitar hash da origem, serialização byte-equivalente,
histórico imutável/validação por fronteira com proteção contra adulteração.
sha256.update não é automaticamente o mesmo algoritmo; retirar sort_keys altera
bytes; return rows direto quebra isolamento da consulta.

**Consequências:** versões/leitura/replay atuais mantidos. Próxima missão mede
uma alteração byte-equivalente de cópia/validação histórica com golden/diferencial
v1. Reavaliar hashing apenas se custo residual posterior justificar dois algoritmos,
cache/invalidação e novos schemas. Se houver algoritmo diferente, introduzir
versão explícita e trace/artifact/snapshot adequados, preservar despacho v1,
rejeitar misturas/desconhecidas e testar leitura/replay/continuação entre processos,
tipos/Unicode/ordem, summary/trace e adulteração. Nunca reinterpretar versões antigas.

## D021 — Reconciliar a base M11/M12 por execução real

**Data:** 2026-10-01. **Status:** adotada/executada no escopo autorizado M12.1/M13.

**Contexto:** docs curtos alegavam adapter/população integrados, mas M11 era stub,
CLI antiga tinha sido substituída, generator ignorava a spec/importava símbolo
ausente, helper Simulation não existia e dois testes eram texto inválido. Suíte
inicial160 terminou com4falhas/4erros; smoke ImportError. Memory Core/Harness ainda
M6.1. Ausência de Git histórico impede atribuir isso a sessões anteriores.

**Decisão:** reparar dependências necessárias a M13 sem tocar engine/RNG/hash;
implementar materialização M12 a partir de archetypes/overrides existentes, helper
externo World→engine e restaurar CLI/isolamento da consulta. Preservar cópia do início.
M12.1 REAL8agentes/seed2026/5ticks; suíte final243OK. Evidências M12_1_SMOKE_RESULT e M13.

**Alternativas:** declarar bloqueio de ambiente contradiz Python funcionando;
reutilizar resultados históricos não valida o worktree; contornar o import sem
honrar a spec produziria sucesso aparente. Reescrever engine ampliaria o escopo.

**Consequências:** as mudanças M12 foram entregues agora; stub não é golden.
Largest remainder normaliza somente quotas de pesos dentro epsilon0.01; spec intacta.
bounded_normal usa Box-Muller com clipping nos bounds (não normal truncada por
rejeição). Relationships uniform não gera vínculos novos. Histórico anterior
preservado; ScientistExplainer/reais não são declarados funcionais.

## D022 — Planner opcional no contrato PopulationSpec existente

**Data:** 2026-10-01. **Status:** aceita pelo Founder e implementada em M13.

**Contexto:** descrição humana deve propor a população, sem LLM criar agentes ou
alterar ticks. O exemplo conceitual traz distribuições por archetype, enquanto
o schema M12 possui Traits numéricos + trait_distributions globais.

**Decisão:** LLMPopulationPlanner usa adapter M11 e retorna PopulationSpec validado;
from_json/to_json compartilhados são a revisão. Prompt declara população sintética,
assumptions, limites, traits permitidos, distribuição e source/warnings. JSON
estrito e validator rejeitam conteúdo significativo inválido; nenhum trait é
mapeado automaticamente. Fake offline genérico, 35 testes planner/CLI passam.

**Alternativas:** schema LLM paralelo cria divergência; distribuições dentro de
Traits exigiriam alterar contrato para além desta missão; agentes finais gerados
pelo LLM perderiam separação/determinismo. Correção silenciosa obscurece a proposta.

**Consequências:** overrides globais valem para todos os archetypes; limitação
explicitada. Modo manual permanece independente. Providers reais poderão
implementar LLMProvider, mas não foram conectados/validados nesta entrega.

## D023 — Revisão, provenance e determinismo em duas etapas

**Data:** 2026-10-01. **Status:** aceita pelo Founder e implementada em M13.

**Contexto:** uma proposta LLM não é população calibrada, nem chamada remota é
garantidamente determinística. Configuração de provider pode conter credenciais.

**Decisão:** population plan termina em JSON revisável e imprime assumptions/
warnings; geração/simulação é chamada explícita posterior. source llm_generated,
ambos warnings obrigatórios, assumptions não vazias. Planner grava só provider,
model e planner_version da resposta; rejeita metadata LLM não vazia. Não grava
request/config/erro bruto. Rejeita formas reconhecíveis de credenciais também em
assumptions/IDs/provenance, sem redigir silenciosamente. Engine não recebe provider.

**Alternativas:** encadear plan→simulation antes da revisão antecipa aprovação;
copiar configuração inteira pode persistir segredo; assumir repetibilidade LLM
real confunde planejamento com geração condicionada a JSON fixo.

**Consequências:** JSON igual+seed igual produz sociedade e três hashes iguais;
calls reais do planner podem divergir. JSON é suficiente para revisão nesta missão,
sem UI/flag de aprovação. Guard de texto não detecta todo segredo arbitrário;
provider não deve devolver credenciais. Próxima proposta M14: CLI de execução
explícita da spec revisada. Sem mudança nos algoritmos/versões do core.
Decisão: reutilizar parser/validate/fingerprint existentes; não duplicar.
