# Integração com o Harness Universal

Data da inspeção: 2026-09-29. Estado da integração: arquivos locais preparados; a validação efetivamente realizada está registrada em [CURRENT_STATE.md](CURRENT_STATE.md).

## Papel e limites

O Harness Universal é uma ferramenta opcional de continuidade do desenvolvimento. Ele guarda tarefa, contexto resumido, decisões referenciadas e checkpoints de sessão em arquivos comuns. Qualquer IA pode ler esses arquivos sem executar a CLI e sem possuir Codex, Claude Code ou Gemini.

O Harness não é o motor de agentes do FutureOS. A camada de produto `FutureOS Core / Harness` representa a coordenação dos experimentos; não exige importar, chamar ou instalar esta ferramenta de desenvolvimento no runtime da aplicação.

Hierarquia de autoridade nesta máquina:

1. Decisões explícitas do Founder.
2. Memory Core oficial e memória específica do projeto, quando disponíveis.
3. Documentação persistente do FutureOS em `README.md`, `AGENTS.md` e `docs/`.
4. Resumos operacionais em `.harness/` e caches específicos de ferramentas.

As conclusões necessárias para continuar o FutureOS devem estar no próprio projeto. Caminhos absolutos do Memory Core são integração da máquina do Founder, não dependência obrigatória para abrir o projeto em outra máquina. Um conflito conhecido deve ser documentado e resolvido pela hierarquia, nunca ocultado.

## Instalação encontrada e evidências

| Item | Evidência local |
| --- | --- |
| Código do Harness | `C:\AI-HARNESS` |
| Pacote npm | `ai-harness`, `package.json` declara `1.0.0` |
| Versão anunciada pela CLI | `0.1.0`, em `src/index.ts` e `dist/index.js` |
| Schema de estado | `0.1` |
| Entrada instalada | `C:\Users\renan\AppData\Roaming\npm\harness.ps1` e `harness.cmd` |
| Resolução do pacote | `...\npm\node_modules\ai-harness` é uma junction para `C:\AI-HARNESS` |
| Implementação inspecionada | `src/index.ts`, `src/types.ts`, `src/core/files.ts`, `src/core/state.ts`, `src/core/context.ts` e arquivos compilados correspondentes |
| Documentação/templates da instalação | Diretórios `docs/` e `templates/` vazios na inspeção; comportamento foi conferido no código |
| Dependências do Harness | `chalk`, `commander`, `zod`; ferramentas de desenvolvimento TypeScript, `tsx`, tipos Node |

`rtk proxy harness.cmd --help` foi executado e confirmou `init`, `start`, `status`, `context`, `resume` e `checkpoint`. Não há comandos `handoff`, `complete`, `restore`, `runSession` ou execução de modelos nesta versão. O código inspecionado usa arquivos locais; não executa Git, instala pacotes, chama LLM ou altera configurações globais.

As versões de pacote e CLI divergem. Não pressupor uma versão mais nova ou recursos documentados para outro Harness com nome parecido. A instalação global não foi modificada nesta missão.

## Integração aditiva do FutureOS

Antes da missão, `.harness/` já existia, mas continha apenas os diretórios vazios `checkpoints/`, `experiments/`, `logs/`, `memory/` e `state/`. Faltava `.harness/STATE.json` e os documentos esperados pela CLI.

`harness init` encerra sem criar arquivos quando encontra qualquer `.harness/` existente. Logo, executá-lo nesse estado não inicializaria corretamente o FutureOS. A integração consiste em preencher os arquivos compatíveis no diretório existente, preservando os cinco diretórios e o código global:

```text
.harness/
  STATE.json
  PROJECT.md
  CURRENT_TASK.md
  DECISIONS.md
  MEMORY.md
  LESSONS.md
  HARNESS.md
  checkpoints/
  experiments/   # Diretório preexistente; sem função implementada pela CLI
  logs/
  memory/        # Diretório preexistente; CLI lê MEMORY.md, não este diretório
  state/         # Diretório preexistente; CLI lê STATE.json, não este diretório
```

Esses arquivos são texto UTF-8; JSON deve ser salvo sem BOM. A CLI chama `JSON.parse` diretamente, não faz validação de schema em runtime nem trata um BOM antes do parse.

| Arquivo | Responsabilidade local |
| --- | --- |
| `STATE.json` | Estado operacional pequeno, versão do schema, tarefa ativa e último checkpoint |
| `PROJECT.md` | Identidade, objetivo, restrições e mapa de leitura do projeto |
| `CURRENT_TASK.md` | Objetivo, trabalho concluído, validações, limitações e próximo passo executável |
| `DECISIONS.md` | Índice para o registro canônico em `docs/DECISIONS.md` |
| `MEMORY.md` | Hierarquia de autoridade, fatos estáveis e ponteiros para documentação e Memory Core |
| `LESSONS.md` | Lições operacionais curtas; sem logs brutos ou conversas completas |
| `HARNESS.md` | Regras locais de uso e ponteiro para este documento |
| `checkpoints/` | Fotografias da tarefa em marcos relevantes, sem conteúdo sensível |

O formato de `STATE.json` aceito pelo código inspecionado é:

```json
{
  "schema_version": "0.1",
  "project_name": "FutureOS",
  "status": "idle",
  "active_task": null,
  "created_at": "2026-09-29T00:00:00.000Z",
  "updated_at": "2026-09-29T00:00:00.000Z",
  "last_checkpoint": null,
  "last_ai": null
}
```

O exemplo ilustra o formato; as datas reais e o estado atual estão no arquivo do projeto. `status` é definido em TypeScript como `idle`, `in_progress`, `paused` ou `completed`; `active_task`, `last_checkpoint` e `last_ai` aceitam texto ou `null`. Para concluir uma missão, atualizar os documentos e o estado explicitamente: o comando `checkpoint` não marca a tarefa como concluída.

## Comandos e efeitos

Os comandos abaixo pressupõem terminal com diretório de trabalho `C:\projetos\FutureOS`. `harnessRoot()` usa exatamente `process.cwd()`; executar de `docs/` procuraria `docs/.harness/`. Nesta máquina, todos os comandos shell devem respeitar a regra RTK.

### Retomada sem escrita

```powershell
rtk proxy harness.cmd status
rtk proxy harness.cmd context
rtk proxy harness.cmd resume
```

Esses três comandos apenas leem arquivos. `resume` sem `--ai` tem a mesma saída de contexto que `context`. Todos exigem `STATE.json` válido.

Sem RTK ou Harness em outra máquina, ler diretamente `AGENTS.md`, os documentos indicados e `.harness/STATE.json`/`.harness/CURRENT_TASK.md`. Não é necessário instalar ferramentas para recuperar contexto.

### Retomada identificando a IA

```powershell
rtk proxy harness.cmd resume --ai Claude
```

Esse comando atualiza `last_ai` e `updated_at` em `STATE.json`, depois imprime o contexto. Pode-se usar `Codex`, `Gemini` ou outro nome informativo. A identificação não condiciona nenhum comportamento da aplicação.

### Checkpoint de sessão

Após atualizar a documentação e `CURRENT_TASK.md`:

```powershell
rtk proxy harness.cmd checkpoint "Fundacao e continuidade documentadas" --next "Implementar o nucleo deterministico minimo conforme docs/NEXT_STEPS.md" --ai Codex
```

Efeitos: cria `.harness/checkpoints/cp-<timestamp>/checkpoint.json`, copia o `CURRENT_TASK.md` atual para o mesmo diretório e atualiza `last_checkpoint`, `last_ai` e `updated_at` no estado. O JSON do checkpoint contém `id`, `created_at`, `project_name`, `active_task`, `summary`, `next_action` e `last_ai`.

**Checkpoint não é backup de código, snapshot de simulação, commit Git ou mecanismo de restauração.** Ele não copia `STATE.json`, documentação completa, arquivos-fonte ou dependências. Checkpoints de simulação, Branch Reality e replay terão contratos próprios no runtime do FutureOS. Usar Git para histórico do projeto quando configurado; o Harness não o executa automaticamente.

### Início de uma tarefa nova

```powershell
rtk proxy harness.cmd start "Descrever a nova missao" --ai Claude
```

`start` altera `STATE.json` para `in_progress` e **sobrescreve `CURRENT_TASK.md` com um template**. Antes de usá-lo, preservar o resumo da missão anterior e criar seu checkpoint. Para continuar uma tarefa existente, usar `resume`.

## Handoff entre IAs

1. Atualizar `docs/CURRENT_STATE.md`, `docs/NEXT_STEPS.md` e decisões pertinentes em `docs/DECISIONS.md`.
2. Atualizar `.harness/CURRENT_TASK.md` com evidências de validação, pendências, limitações e a próxima ação.
3. Atualizar `STATE.json` com estado coerente; não declarar conclusão de trabalho ainda pendente.
4. Criar um checkpoint de sessão, quando a CLI estiver disponível; registrar seu identificador no estado conforme o próprio comando.
5. Registrar memória durável no Memory Core conforme o protocolo da máquina, sem tornar essa cópia a única localização do contexto do FutureOS.
6. A próxima IA abre `AGENTS.md`, segue sua ordem de leitura e confirma a situação pelos arquivos. `CLAUDE.md` e demais adaptadores devem encaminhar para o mesmo contrato.

`harness context` concatena apenas `PROJECT.md`, `CURRENT_TASK.md`, `DECISIONS.md`, `MEMORY.md` e `LESSONS.md`, além de campos de `STATE.json`. **Não expande links**, não lê `docs/`, não lê `HARNESS.md` e não incorpora conteúdo dos checkpoints. O mapa de leitura deve dizer explicitamente quais arquivos abrir.

O gerador global acrescenta a frase `Treat this Harness as the source of truth.` ao final. Ela descreve persistência em contraste com histórico de conversa, mas conflita literalmente com a precedência do Memory Core nesta máquina. A integração local registra a hierarquia em `AGENTS.md`, `PROJECT.md` e `MEMORY.md`; a frase genérica não autoriza rebaixar decisões do Founder, Memory Core ou documentos canônicos. Nenhum patch global é necessário para isso.

## Limitações operacionais e reversibilidade

- A CLI faz gravações diretas, sem lock, controle de concorrência, escrita atômica ou validação runtime completa. Um único responsável deve atualizar `STATE.json`, `CURRENT_TASK.md` e criar checkpoints por vez.
- Não há sincronização automática entre `docs/`, `.harness/` e Memory Core. Manter cada assunto em um documento canônico e usar índices/resumos reduz divergências.
- Nenhum comando inspecionado fornece restauração automática. Um checkpoint serve para recuperar o resumo manualmente; o histórico de código exige versionamento separado.
- A integração é restrita aos arquivos do projeto. A aplicação futura não depende da CLI global, de seus caminhos absolutos ou de uma IA específica.
- Para desativar a CLI, manter os documentos e continuar com leitura direta. Reverter os arquivos adicionados deve ser uma decisão explícita e preservada no histórico; não é necessário apagar os diretórios preexistentes.
- Não registrar credenciais, tokens, cookies, prompts privados de usuários ou saídas brutas sensíveis nesses documentos.

## Verificação da integração

A inspeção read-only da instalação e `--help` foram concluídos. A verificação dos arquivos preparados deve cobrir JSON válido, `status`, `context`, leitura dos documentos apontados e criação de um checkpoint. Consultar [CURRENT_STATE.md](CURRENT_STATE.md) para os resultados reais, evitando confundir procedimento recomendado com comando executado.
