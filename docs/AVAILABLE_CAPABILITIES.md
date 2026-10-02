# Capacidades disponíveis — auditoria local

Data: **2026-09-29**. Ambiente auditado: Windows, workspace `C:\projetos\FutureOS`.

Este é um inventário observado nesta máquina, não uma lista de dependências do FutureOS. Nenhuma nova dependência foi instalada. Os comandos de descoberta não executaram `npx`, `uvx`, instaladores ou atualização de pacotes.

## Como interpretar o inventário

- **Presente:** arquivo, executável ou metadado localizado em disco.
- **Configurado:** declarado em configuração; isso não comprova disponibilidade ou autenticação.
- **Exposto:** uma ferramenta está disponível na sessão de auditoria; outra IA/sessão pode não recebê-la.
- **Verificado:** uma checagem específica foi executada e seu alcance é indicado abaixo. `--version` não valida uma aplicação inteira.

Não transportar configurações pessoais, credenciais, variáveis de ambiente ou caches das ferramentas para o repositório. O projeto deve continuar utilizável quando qualquer capacidade opcional desta lista estiver ausente.

## Estado do projeto na descoberta

A inspeção inicial encontrou nove arquivos vazios (oito Markdown e `.env.example`), nenhum `.git`, nenhum manifesto de aplicação, lockfile, ambiente virtual ou diretório de dependências. Não havia código de produto, testes, framework ou dependências declaradas. A estrutura após esta missão está em [CURRENT_STATE.md](CURRENT_STATE.md).

## CLIs e runtimes

| Ferramenta | Resultado observado | Verificação e ressalva |
|---|---|---|
| Git | `2.54.0.windows.1` | `--version`; executável em `C:\Program Files\Git\cmd\git.exe` |
| RTK | `0.44.2` | `--version`; `C:\Users\renan\.local\bin\rtk.exe`; prefixo exigido pelo protocolo local |
| Node.js | `v24.13.0` | `--version`; `C:\Program Files\nodejs\node.exe` |
| npm | `11.6.2` | `--version` e inventário global com `--offline` |
| pnpm | `9.15.4` | Pacote global presente e versão verificada por `node ...\pnpm\bin\pnpm.cjs --version` |
| Python | `3.13.15` | `py -3.13`; interpretador real em `...\Programs\Python\Python313\python.exe` |
| Python alternativo | `3.11.16` | Registrado pelo launcher `py -0p`, gerenciado por uv; não usado na auditoria de pacotes |
| SQLite da biblioteca padrão Python | `3.50.4` | `import sqlite3` e leitura de `sqlite_version` |
| uv | `0.12.6` | `--version`; executável em `...\AppData\Local\hermes\bin\uv.exe` |
| Docker | Cliente `29.1.3` | Cliente responde; consulta ao servidor falhou por ausência do pipe `dockerDesktopLinuxEngine` |
| GitHub CLI | `2.97.0` | `--version`; autenticação e acesso a repositórios não testados |
| Codex no PATH | `0.149.0` | `--version`; instalação desktop em `...\Programs\OpenAI\Codex\bin\codex.exe` |
| Claude Code no PATH | `2.1.285` | `--version`; `C:\Users\renan\.local\bin\claude.exe` |
| ripgrep | `15.2.0`, PCRE2 `10.45` | `--version`; busca local disponível |
| PowerShell (`pwsh`) | `7.6.5` | `--version`; resolvido no runtime privado do Codex, portanto não é dependência portátil |
| Ollama | Executável localizado | `...\Programs\Ollama\ollama.exe`; serviço, modelos e inferência não testados |

`pnpm` resolve primeiro para um shim Corepack em `C:\Program Files\nodejs`; a checagem de versão usou diretamente o pacote global existente para evitar download implícito. `python`/`python3` resolvem para aliases WindowsApps; a auditoria usou `py -3.13` para selecionar o interpretador real.

Não encontrados no PATH consultado: `gemini`, `bun`, `yarn`, `pip`, `go`, `rustc`, `cargo`, `dotnet`, `sqlite3`, `psql`, `cmake`, `make` e `jq`. Isso não prova ausência em toda a máquina. O módulo Python `pip` está instalado, apesar de o comando isolado não ter sido resolvido.

### Instalações concorrentes

O inventário npm global registra `@openai/codex 0.154.0` e `@anthropic-ai/claude-code 2.1.268`, diferentes dos executáveis usados pelo PATH. Há também múltiplos shims de pnpm. Ao reproduzir um problema, registrar o executável efetivamente resolvido e sua versão; não inferir a versão executada pelo inventário npm.

## Pacotes já existentes fora do projeto

### npm global

| Pacote | Versão presente |
|---|---|
| `@anthropic-ai/claude-code` | `2.1.268` |
| `@deepseek-ai/dsh` | `0.1.0-rc.8` |
| `@earendil-works/pi-coding-agent` | `0.84.2` |
| `@higgsfield/cli` | `1.0.1` |
| `@openai/codex` | `0.154.0` |
| `@openhands/agent-canvas` | `1.18.0` |
| `9router` | `0.5.59` |
| `ai-harness` | `1.0.0`, link local para `C:\AI-HARNESS` |
| `better-sqlite3` | `13.0.3` |
| `cline` | `3.0.65` |
| `omniroute` | `3.8.50` |
| `openclaw` | `2026.6.35` |
| `opencode-ai` | `1.18.25` |
| `pixel-agents` | `1.4.1` |
| `pnpm` | `9.15.4` |
| `sql.js` | `1.14.1` |

Evidência: `rtk proxy npm list --global --depth=0 --json --offline`. Presença desses pacotes não significa seleção arquitetural ou configuração de seus serviços.

### Python 3.13 global

Foram encontradas **140 distribuições** por `importlib.metadata`, sem instalar ou importar bibliotecas de terceiros. Seleção útil para decisões futuras:

| Finalidade possível | Pacotes presentes |
|---|---|
| Simulação e análise numérica | `numpy 2.5.3`, `scipy 1.18.1`, `pandas 2.3.3` |
| Grafos e relações | `networkx 3.6.1` |
| Contratos e validação | `pydantic 2.12.3`, `jsonschema 4.26.0`, `PyYAML 6.0.3` |
| Testes e qualidade | `pytest 8.4.2`, `ruff 0.16.8` |
| APIs e HTTP | `fastapi 0.141.1`, `uvicorn 0.52.4`, `httpx 0.28.1` |
| Visualização | `matplotlib 3.11.2`, `plotly 6.9.0`, `altair 6.2.2` |
| Provedores e modelos | `openai 2.54.0`, `torch 2.14.0`, `transformers 5.8.0`, `tiktoken 0.14.0` |
| Gerenciamento | `pip 26.2.1`, `setuptools 84.0.0` |

Compatibilidade, importação, GPU e comportamento funcional desses pacotes não foram validados. A futura implementação precisa declarar suas próprias dependências e versões; não deve depender acidentalmente deste ambiente global.

## Skills e ECC

O [catálogo local](SKILLS_CATALOG.md) registra nomes, raízes, contagens e a distinção entre arquivos encontrados e skills expostas.

| Local inspecionado | Arquivos `SKILL.md` encontrados |
|---|---:|
| `C:\Users\renan\.codex\skills` | 29 |
| `C:\Users\renan\.agents\skills` | 11 |
| `C:\Users\renan\.claude\skills` | 26 |
| `C:\Users\renan\.codex\plugins\cache` | 989 |
| `C:\Users\renan\.claude\plugins` | 1962 |

Contagens recursivas incluem cópias, versões, templates e arquivos aninhados; **não são quantidades de skills distintas ou ativas**.

**ECC 2.2.2** está presente e habilitado nas configurações do Codex e do Claude Code. Raízes observadas:

- `C:\Users\renan\.codex\plugins\cache\ecc\ecc\2.2.2`
- `C:\Users\renan\.claude\plugins\cache\ecc\ecc\2.2.2`

O pacote Codex contém 293 skills em `skills/` e 35 comandos migrados em `.codex-plugin/migrated-command-skills/`. Há regras, agentes, hooks, scaffolds, testes e configurações MCP no pacote. A presença de um hook no cache não comprova que esteja ativo no projeto. A auditoria não instalou nem habilitou hooks.

Skills pertinentes incluem `codebase-onboarding`, `architecture-decision-records`, `agent-architecture-audit`, `agent-harness-construction`, `agent-eval`, `cost-aware-llm-pipeline`, `benchmark-methodology`, `python-testing` e `verification-loop`. Usá-las exige ler o respectivo `SKILL.md`; elas auxiliam o desenvolvimento e não fazem parte do runtime do produto.

## MCPs e ferramentas de sessão

Foram lidos apenas campos selecionados de configuração para o relatório: nomes, transporte, comando e habilitação. Argumentos, ambientes, segredos, cabeçalhos e URLs privadas foram omitidos.

| Capacidade | Onde foi encontrada | Estado observado |
|---|---|---|
| `node_repl` | `C:\Users\renan\.codex\config.toml` | Configurado como stdio com executável local; 3 ferramentas expostas nesta sessão |
| `chrome-devtools` | `.mcp.json` do ECC 2.2.2 | Configurado como stdio via `npx`; 30 ferramentas expostas; navegador não acionado nesta auditoria |
| `context7` | `C:\Users\renan\.claude.json`, escopo global | Configurado como stdio via `npx`; não exposto nesta sessão e não iniciado |
| `obsidian` | Configuração Claude, escopo de outro projeto | Configurado como stdio via `npx`; não atribuir ao FutureOS; não iniciado |
| `playwright` | Configuração Claude, escopo de outro projeto | Configurado como stdio via `npx`; não atribuir ao FutureOS; não iniciado |
| `codex_app` | Ferramentas disponibilizadas pelo aplicativo | 41 ferramentas expostas; recursos específicos do ambiente de desenvolvimento |
| `codex_apps` | Ferramentas disponibilizadas por conectores/plugins | 50 ferramentas expostas; exposição não valida autorização, conta ou serviço de cada conector |
| CUA / `mcp__cua_repl` | Ferramenta explícita da sessão | APIs de automação de navegador expostas; não utilizadas para a auditoria |

Além disso, a sessão expõe ferramentas de arquivos/processos, pesquisa web, geração de imagens e colaboração entre agentes. Elas são facilidades desta sessão e não dependências da aplicação FutureOS.

No início da auditoria não havia `.mcp.json` do FutureOS nem `C:\Users\renan\.gemini\settings.json`. Não foi validada conectividade de nenhum servidor MCP externo. Um comando configurado com `npx` pode baixar pacotes ao iniciar; não foi executado nesta fase.

### Plugins configurados

Codex: `documents`, `pdf`, `spreadsheets`, `presentations`, `template-creator`, `visualize`, `superpowers`, `browser`, `codex-app-tools`, `computer-use`, `unified-computer-use` e `ecc` aparecem habilitados no arquivo de configuração. Isso não garante que todos os recursos estejam expostos em todas as sessões.

Claude: `plugin-dev`, `pyright-lsp`, `security-guidance`, `commit-commands`, `superpowers 6.4.1`, `ponytail 4.10.0` e `ecc 2.2.2` aparecem habilitados e registrados no inventário de plugins instalados. Não foram disparados agentes, hooks ou serviços desses plugins para testar disponibilidade.

## Harness Universal, Graphify e Memory Core

- **Harness Universal:** instalação local encontrada em `C:\AI-HARNESS`, também registrada como pacote npm global `ai-harness 1.0.0`. Sua integração e limitações são documentadas em [HARNESS.md](HARNESS.md). Não é um MCP exposto nesta sessão nem uma dependência de produto.
- **Graphify:** a auditoria específica verificou `graphify --version` como **0.9.48** e ambiente uv `graphifyy`. Há wrappers `graphify.exe` e `graphify-mcp.exe` em `C:\Users\renan\.local\bin` e skills nas raízes pessoais Codex/Claude com stamp 0.9.48. Não foi encontrada configuração MCP Graphify nas configurações examinadas; as sondagens do ambiente retornaram `find_spec('mcp') = None` e `find_spec('starlette') = None`. Portanto, o wrapper MCP presente não comprova servidor pronto. Graphify não está exposto como MCP nesta sessão. Nenhuma extração foi realizada. Uma futura análise somente de código pode extrair AST sem LLM, mas ainda precisa ser avaliada no contexto do projeto; ver [HARNESS.md](HARNESS.md).
- **Memory Core:** fonte local de memória encontrada em `C:\Users\renan\Memory Core`. O protocolo e o registro antigo consultados ainda identificavam `IA-Memory-System`; isso é contexto histórico e não muda a missão explícita de criar FutureOS. A política de continuidade do repositório resolve a relação entre memória externa e documentação portátil.

## Riscos observados e limites

1. **Dependência acidental de instalações pessoais:** runtimes privados e pacotes globais não viajam com o projeto. Documentação e comandos de produto precisam funcionar sem Codex/Claude/ECC.
2. **Versões concorrentes no PATH:** Codex, Claude e pnpm têm mais de uma instalação/shim. Registrar resolução e versão ao reproduzir verificações.
3. **Docker indisponível no teste:** não assumir banco ou worker em container sem verificar primeiro o daemon. A fundação não precisa de Docker.
4. **Presença confundida com funcionamento:** skills em caches, MCPs configurados e bibliotecas globais não equivalem a integração validada.
5. **Downloads implícitos:** Corepack, `npx` e `uvx` podem buscar dependências. A fase de descoberta evitou esses caminhos.
6. **Escopo da descoberta:** não foi feita varredura de todos os discos, WSL, hosts remotos ou cada ambiente virtual. Ausências são limitadas ao PATH e às raízes examinadas.
7. **Validade temporal:** este inventário é um snapshot; revalidar antes de depender de uma ferramenta. Não atualizar a arquitetura automaticamente porque uma ferramenta foi instalada.

## Evidências reproduzíveis

Comandos usados ou equivalentes de leitura, sem instalar pacotes:

```powershell
rtk proxy powershell -NoProfile -Command 'Get-Command git,node,npm,pnpm,py,uv,docker,gh,codex,claude,rg -All | Select-Object Name,Source'
rtk git --version
rtk proxy node --version
rtk proxy py -0p
rtk proxy py -3.13 -c "import sys,sqlite3; print(sys.version); print(sqlite3.sqlite_version)"
rtk proxy npm list --global --depth=0 --json --offline
rtk proxy docker version --format "{{.Server.Version}}"
```

As configurações MCP foram inspecionadas por parser TOML/JSON com seleção de campos, sem copiar o conteúdo bruto. Nomes e versões Python vieram de `importlib.metadata`; contagens de skills vieram de busca recursiva por `SKILL.md`. Não há credenciais neste relatório.
