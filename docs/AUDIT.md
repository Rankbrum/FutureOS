# Auditoria de fundação — 2026-09-29

## Método e escopo

Inspeção local de arquivos, comandos de versão, metadados e implementação do Harness. Nenhuma dependência instalada, atualização de ferramenta, chamada a modelo, extração Graphify ou migração de dados. A disponibilidade observada é específica desta máquina e sessão; configuração de MCP não comprova conectividade.

Memórias consultadas: MEMORY.md, protocolo CODEX_MEMORY.md e cinco arquivos de IA-Memory-System no Memory Core. O projeto anterior é distinto; não existia memória específica FutureOS no início. As conclusões portáteis foram registradas nesta pasta.

## Estrutura encontrada antes de alterações

Foram encontrados **9 arquivos, todos com zero bytes**, sem código ou manifestos:

```text
FutureOS/
  .env.example
  CLAUDE.md
  README.md
  .harness/
    checkpoints/ experiments/ logs/ memory/ state/
  agents/
    citizen/ influencer/ observer/ scientist/
  apps/web/
  docs/
    AGENTS.md
    ARCHITECTURE.md
    AVAILABLE_CAPABILITIES.md
    MEMORY.md
    ROADMAP.md
    SIMULATION_ENGINE.md
  packages/
    agents/ analytics/ core/ experiments/ memory/ population/ simulation/
  results/
  scenarios/
  simulations/
  skills/
    behavior/ decision/ influence/ persuasion/ trust/ validation/
  tests/
```

Todos os diretórios listados estavam sem arquivos, exceto os documentos explicitados em docs. A pasta .harness existia, mas não continha STATE.json.

`git status` e `git rev-parse --show-toplevel` retornaram ausência de repositório. Não há branch, histórico, remoto ou alterações rastreadas a reportar. Nenhum Git foi inicializado nesta missão.

Não havia package.json, pyproject.toml, requirements, lockfiles, node_modules ou ambiente virtual no projeto. Bibliotecas globais não são dependências do FutureOS.

## Inventário

Detalhes em [AVAILABLE_CAPABILITIES.md](AVAILABLE_CAPABILITIES.md) e [SKILLS_CATALOG.md](SKILLS_CATALOG.md).

- Git, RTK, Node/npm, Python/uv, gh, Codex, Claude e ripgrep encontrados.
- ECC instalado; skills físicas incluem duplicatas, templates e múltiplas versões de cache.
- Harness Universal local encontrado e inspecionado antes de qualquer integração.
- Graphify CLI instalado; wrapper MCP sem dependências opcionais completas.
- Docker CLI instalado, daemon indisponível no teste.
- Não foi encontrado CLI Gemini no PATH; o protocolo documental já contempla Gemini.
- MCPs expostos na sessão e MCPs encontrados em configurações foram diferenciados; não foram conectados servidores novos.

## Árvore recomendada

Preservar o esqueleto, manter a fundação pequena e criar código apenas em M1:

```text
FutureOS/
  README.md
  AGENTS.md                   protocolo independente de ferramenta
  CLAUDE.md                   ponteiro para AGENTS
  GEMINI.md                   ponteiro para AGENTS
  .env.example
  .gitignore
  .harness/                   contexto operacional de desenvolvimento
    STATE.json
    PROJECT.md
    CURRENT_TASK.md
    DECISIONS.md              índice para docs/DECISIONS
    MEMORY.md
    LESSONS.md
    HARNESS.md
    checkpoints/
  docs/                       contexto técnico portátil
    ARCHITECTURE.md
    DECISIONS.md
    ROADMAP.md
    CURRENT_STATE.md
    NEXT_STEPS.md
    AVAILABLE_CAPABILITIES.md
    SKILLS_CATALOG.md
    AUDIT.md
    HANDOFF.md
    HARNESS.md
    MEMORY.md
    AGENTS.md                 papéis da simulação
    SIMULATION_ENGINE.md
  apps/web/                   UI futura; continua vazia
  packages/
    core/                     contratos e casos de uso
    experiments/              protocolo e comparação
    simulation/               ticks, eventos, snapshots, branches
    population/               geração e validação
    agents/                   runtime e políticas
    memory/                   memórias e relações simuladas
    analytics/                métricas e auditoria
  agents/                     futuras definições declarativas dos quatro papéis
  skills/                     futuras políticas/capacidades da sociedade
  scenarios/                  cenários e premissas versionados
  simulations/                configurações de modelos; não resultados mutáveis
  results/                    saídas geradas, fora do histórico por padrão
  tests/                      testes de comportamento e isolamento em M1
```

As responsabilidades são fronteiras lógicas propostas; diretório vazio não é módulo implementado. Providers podem começar como interfaces/adaptadores dentro de agents/core; persistência dentro de simulation/memory; Scientist dentro de analytics. Não criar pacotes extras ou serviços só para preencher o diagrama. Layout de imports e manifestos será decidido após a linguagem em D006. Git não preserva diretórios vazios; recriar somente os necessários ou documentar placeholders quando houver versionamento.

## Riscos técnicos e mitigação

| Risco | Consequência | Mitigação / marco |
|---|---|---|
| Snapshots incompletos | Retomada ou branches incorretos | Preservar RNG, filas, relações, memórias e métricas; testes M1 |
| Estado mutável compartilhado | Contaminação entre universos | Cópia independente e testes de ordem de execução M1 |
| RNG global dependente da ordem | Diferença atribuída indevidamente à intervenção | Streams/ordenação especificadas; política pareada explícita quando usada |
| LLM remoto não determinístico | Reexecução não reproduz narrativa | Kernel offline; registrar respostas para replay em M3 |
| Uso irrestrito de LLM | Custo/latência crescentes | Budgets, limite de retries, fallback e observabilidade |
| População e premissas artificiais | Aparência de previsão/causalidade real | Proveniência, sensibilidade, dispersão e calibração externa |
| Auditoria circular por LLM | Confiança sem evidência | Scientist computável primeiro; separar observação/intervenção |
| Métricas de preço incompatíveis | Comparação enganosa entre mensalidade e compra | Horizonte, denominador e custo explícitos |
| Memória e ferramentas pessoais em agentes | Vazamento ou efeitos fora da simulação | Contratos explícitos; zero acesso externo no kernel |
| Docs, Harness e Memory Core divergentes | Handoff com tarefa errada | Documento canônico por assunto, ponteiros e encerramento disciplinado |
| Harness init não completa .harness existente | Integração aparentemente feita, mas inválida | Arquivos compatíveis adicionados; CLI testado |
| Harness sem lock/validação transacional | Escritas concorrentes/corrupção | Um responsável por estado/checkpoint; JSON validado |
| Checkpoint confundido com backup | Perda de código e histórico | Git na próxima missão; registrar limites do checkpoint |
| Versões e caminhos divergentes na máquina | Comando resolve binário inesperado | Inventário registra PATH vs pacote; revalidar runtime na M1 |
| Dependência de runtime empacotado em IA | Falha em outra máquina/ferramenta | Manifesto e comandos próprios do projeto; ferramentas opcionais |
| Escala antecipada | Complexidade antes de evidência | Um processo, uma fixture, medir antes de distribuir |

## Resultado e limitações

A auditoria comprova o ponto de partida e as capacidades locais, não funcionamento de serviços externos nem qualidade científica de futuras simulações. Não foi necessário iniciar aplicativo, fazer build ou testar produto inexistente.

As verificações finais e o estado do Harness constam em [CURRENT_STATE.md](CURRENT_STATE.md). A primeira comunicação mencionou dez arquivos; a contagem recursiva confirmou nove e este registro contém o inventário corrigido.
