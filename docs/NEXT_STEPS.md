# Próxima tarefa recomendada após publicação — verificar os protótipos posteriores

Atualizado em 2026-10-01. Publicação inicial do worktree verificada em
`Rankbrum/FutureOS`, atualmente público; validação atual do núcleo: 243 testes passaram.
As notas M16–M18 abaixo são históricas e não comprovam uma demo web funcional.
Esta recomendação não inicia implementação adicional.

Tarefa executável: confrontar M15/M16/apps com seus contratos, converter as
checagens relevantes em testes executáveis e substituir respostas fixas da API
por validação/execução dos casos de uso existentes. Critérios de aceite:

1. Entradas inválidas de população/cenário são rejeitadas por validadores reais.
2. Experimento usa spec revisada e seeds, executa ticks e deriva métricas reais,
   preservando isolamento, replay e hashes; não retorna resultados constantes.
3. Testes de cenário/runner/API são coletados e exercitam comportamento; a suíte
   do núcleo permanece verde. Documentar dependência web opcional antes de instalação.
4. Smoke web e evidências reais substituem alegações de conclusão sem execução,
   mantendo o histórico. Atualizar docs/Harness/Memory Core com os limites restantes.

## Histórico preservado — recomendação M14

# Próxima missão recomendada — M14: executar JSON revisado pela CLI

Atualizado em 2026-10-01. **M12.1 VALIDATED / M13 COMPLETE**, evidência no
[estado](CURRENT_STATE.md) e [relatório M13](M13_LLM_POPULATION_PLANNER.md).
Esta proposta não autoriza execução automática de M14.

## Tarefa executável

Adicionar comando explícito para carregar um PopulationSpec JSON já revisado e
executar o pipeline determinístico com seed/horizonte definidos pelo operador.
Exemplo conceitual: `population run --spec population-spec.json --seed 2026
--ticks 5 --output results/novo-run`. Nome/contrato final devem ser escolhidos na
missão. `population plan` continua terminando na proposta, sem encadear execução.

## Critérios de aceite

1. Carregar via PopulationSpec.from_json e validar antes de geração/ticks.
2. Exibir assumptions/warnings/source/provenance e tornar a revisão humana
   uma etapa explícita do procedimento; não tratar proposta LLM como fato.
3. Reutilizar generate_population_with_relationships e o helper de Simulation,
   sem importar planner/provider no caminho de execução manual.
4. Persistir seed, spec revisada, versões/horizonte, métricas e hashes, com formato
   documentado e sem segredo. Saída nova; falhas úteis sem resultados inventados.
5. Repetir mesmo JSON+seed em processos novos com sociedade/hashes iguais; testar
   manual e llm_generated, dados inválidos e preservação da spec original.
6. Suíte atual243 e CLI legadas passam; engine/RNG/hash/snapshots permanecem
   compatíveis. Atualizar docs, evidências, Harness/checkpoint e Memory Core.

Sem provider real obrigatório, LLM nos ticks, RAG, UI, dataset, calibração, banco
ou dependências novas. ScientistExplainer persiste stub fora desse escopo.
Versionamento Git continua uma necessidade separada; checkpoints não salvam código.
M7 de desempenho continua proposta histórica e não é a próxima missão de produto.

## Histórico preservado — recomendação anterior

# Proposta M7: otimização comprovada preservando v1

Atualizado em 2026-10-01. **M6.1 COMPLETE**, evidência em [M6_1_VALIDATION](M6_1_VALIDATION.md).
M7 não está implementada; a recomendação não autoriza execução automática.

## Tarefa executável e aceite

1. Conferir worktree/manifesto e executar baseline atual. Criar golden moderno v1
   e diferencial contra versão preservada: records, frames e três hashes, modos,
   tipos int/float, Unicode, ordenação, snapshots e branches.
2. Medir uma mudança pequena byte-equivalente em cópia/revalidação do histórico,
   com imutabilidade e fronteiras explícitas. Preservar detecção de mutações
   públicas/adulteração. Materialização única de agentes e reaproveitar hash da
   origem são alternativas menores; escolher um alvo pelo profile atual.
3. Comparar antes/depois em mesma condição, três processos novos por summary/trace
   10/30/60, bytes, RAM, profiler e dispersão. Não usar M3 histórico como controle
   causal. Piloto120 atual958,523s: ampliar somente quando o custo for razoável.
4. Suíte, três hashes, replay e isolamento devem passar. Consulta de trajetória
   mantém retorno independente; golden legado/schema2 e continuação em outro
   processo preservados. Nenhum cache ignora adulteração.
5. Manter D020: hash-v1. Reavaliar hashing somente se perfil posterior justificar.
   Algoritmo diferente
   exige hashVersion/trace/artifact/snapshot adequados, leitura/replay v1 explícitos
   e rejeição de versões desconhecidas/misturadas antes dos ticks.
6. Atualizar relatório, decisões, estado, Harness/checkpoint e Memory Core com
   evidência real. Não retirar sort_keys ou cópias necessárias por aparência de hotspot.

Sem dependências novas, providers, UI, banco ou frameworks. Git ainda sem commits;
checkpoint não supre histórico/backup. Versionamento local é uma missão própria
se autorizado; esta validação não criou commit.

## Histórico — proposta de perfil atendida por M6.1

# Próxima tarefa proposta — perfil e retenção do trace

Atualizado em 2026-10-01. **M3 concluída**: RNG contextual, trace/deltas, trajetórias,
hashes, replay e divergência, 164 testes OK. Ler [CURRENT_STATE](CURRENT_STATE.md),
[M3_REPORT](M3_REPORT.md), [AUDIT_TRAJECTORIES](AUDIT_TRAJECTORIES.md) e D016–D018.
Esta recomendação não autoriza automaticamente uma nova missão.

## Tarefa executável recomendada

Medir CPU/alocação/cópias/validação/hashing/serialização do engine-v2 nos horizontes
30/60, população 21 e seed 2026, summary/trace, antes de alterar a retenção. O perfil M3
mediu 3,638/10,321 s summary e 19,148/306,405 s trace; bytes trace 5,53/10,56MB. São
observações locais únicas, sem atribuição quantitativa do gargalo.

1. Confirmar baseline atual e reproduzir o mesmo protocolo com saída nova, sem outra
   suíte dos agentes simultânea. Registrar carga/escopo e separar a instrumentação.
2. Usar ferramentas stdlib, como cProfile/tracemalloc, para distinguir custo de
   deepcopy, validação histórica, hash de estado/memórias e serialização.
3. Registrar alternativas antes de mudar retenção/cópias: estruturas imutáveis de
   auditoria, coletor externo, validação por fronteira ou streaming explícito.
4. Implementar uma alteração justificada por medição e comparar antes/depois com
   mesmo cenário/configuração/seed/horizonte/versões e escopo de tempo.

## Critérios de aceite da futura tarefa

- Suíte completa passa; fixtures M1/schema1 mantêm bytes/checksums/continuação.
- Os três hashes, replay, divergência e consulta conservam resultados. Mudança
  incompatível exige novas versões; não reinterpretar artefatos M3 existentes.
- Snapshots/branches independentes; observação não modifica sociedade/RNG.
- Perfil original/posterior usa 10/30/60 ticks e ao menos uma repetição separada,
  bytes reais, tempo por fase e memória medida. Declarar variação da carga.
- Retenção explicita quais detalhes deixam de ser recuperáveis. Summary sem
  trace completo; nenhum detalhe ausente ou causalidade real inventados.
- Atualizar decisões/arquitetura/estado/Harness/Memory Core com evidências.

## Limites e retomada

Sem web, provider/LLM, instalação de dependências, banco externo ou frameworks de
agentes nesta proposta. Runtime híbrido fake/replay continua opção posterior.
Antes de iniciar, seguir AGENTS, consultar memória oficial/Git e confirmar escopo.
Comandos:

```powershell
python -m unittest discover -s tests -v
python -m futureos audit --seeds 2026 --mode summary --ticks 30
python -m benchmarks.audit --ticks 10,30,60 --output results/novo-perfil
```

Nesta máquina, prefixar shell com RTK quando
disponível. Git main sem commits/remoto; checkpoint Harness não é backup de código.

## Histórico — proposta M3 atendida em 2026-10-01

Atualizado em 2026-09-30. M2 concluída: experimentos multi-seed, agregação, comparação pareada, OAT e benchmark. Evidência final e status de aceite ficam em CURRENT_STATE e M2_REPORT. A fixture 70, 99,90 e 70 com incentivo 20 continua sintética; nenhum desses parâmetros é decisão comercial do Founder.

## M3 proposta, não iniciada nem autorizada por este documento

Reforçar auditoria determinística e controle dos choques antes de providers/web. M2 explicita uma stream por simulação; variar reach pode desalinha-la. Comparações finais não expõem transientes nem trajetória da divergência.

Primeira tarefa executável: registrar o desenho de RNG por mecanismo/agente/evento e um relatório opcional de métricas por tick, com teste de uma variação de reach que preserve choques de ruído/interação não relacionados. Comparar alternativas (streams por mecanismo versus draws indexados), custos e compatibilidade de snapshots antes de modificar o engine. Se a semântica mudar, versionar engine/RNG/snapshot explicitamente. Não reescrever resultados M1/M2.

## Critérios de aceite

- Trajetórias por tick conservam unidade, denominador, seed/branch, horizonte e versões; resultados finais concordam com a agregação M2.
- Alterar reach de um evento não muda draws de outros mecanismos quando a política nova prometer essa separação; ordem de seeds/branches mantém igualdade.
- Snapshot preserva todos os estados RNG necessários; replay completo entre processos e isolamento continuam passando.
- Auditoria computável sinaliza premissas, divergências de origem/consumo e dispersão, sem modificar sociedade observada ou emitir selo de previsão real.
- Perfil em horizontes 10/30/60 e população pequena registra tempo, bytes e memórias; propor otimização somente com gargalo demonstrado e ganho medido.
- Cenários/protocolos inválidos ainda falham antes dos ticks, e artefatos antigos têm política explícita de compatibilidade/rejeição.
- Suite atual, benchmark e OAT continuam reproduzíveis; atualizar docs/Harness/Memory Core com evidência real.
- Nenhuma instalação, web, banco externo, MCP externo ou LLM nesta proposta. Runtime híbrido com fake/replay continua opção posterior do roadmap, sem antecipar integração real.

## Limites mantidos

Sem web, SaaS, autenticação, banco externo, Supabase, Docker, CrewAI, LangGraph ou LLM obrigatório. Scientist continua verificação determinística; calibração com dados reais exige protocolo e origem próprios.

## Retomada

Ler AGENTS, README, CURRENT_STATE, DECISIONS, SIMULATION_ENGINE, EXPERIMENTS e M2_REPORT; conferir Git e alterações antes de editar. Executar `python -m unittest discover -s tests -v` e um experimento pequeno com diretório novo. Git está inicializado em main, sem commit/remoto nesta missão; checkpoint do Harness não é backup do código. A recomendação M3 requer autorização de trabalho nova do Founder.
Next: M16 or M14 execution with scenario + population.
Próxima missão recomendada: M18 (polimento/validação completa) ou M14 CLI execution se ainda pendente.
M18 concluída com limitações registradas. API Flask + HTML estático criados. Nenhum framework pesado. Nenhuma duplicação do core. Nenhum resultado inventado. Ambiente bloqueado documentado em M18_DEMO.md e M18_DEMO_VALIDATION.json. Próximo: M19 (demo script) ou validação completa quando ambiente permitir.
