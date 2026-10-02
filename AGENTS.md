# Protocolo de desenvolvimento do FutureOS

Este é o ponto de entrada comum para Codex, Claude Code, Gemini e qualquer outra IA. Não depender do histórico de chat, de memórias privadas de ferramentas ou de uma CLI específica.

## Identidade e autoridade

- Projeto desta pasta: **FutureOS**. IA-Memory-System é um projeto anterior distinto.
- Decisões explícitas do Founder prevalecem.
- Nesta máquina, o Memory Core oficial é `C:\Users\renan\Memory Core`. Consultar `MEMORY.md` e `04_PROJECTS\FutureOS\PROJECT.md` antes de trabalho substancial. Codex consulta também `02_CODEX\CODEX_MEMORY.md`; sua referência antiga a IA-Memory-System não redefine este projeto.
- O Memory Core prevalece sobre caches locais em conflito. Os documentos deste projeto preservam uma base técnica portátil e devem ser reconciliados com decisões oficiais do Memory Core.
- Fora desta máquina, continuar pelos arquivos do projeto; registrar que o Memory Core estava indisponível. Sua ausência não impede desenvolvimento local. Não inventar decisões ausentes.
- `.harness` é estado operacional de desenvolvimento. Seu texto genérico de “source of truth” não altera esta hierarquia. Memórias específicas de ferramenta são ponteiros ou caches.
- Nunca importar credenciais ou conversas completas para docs, checkpoints, fixtures ou memória de agentes.

## Início de sessão

1. Ler este arquivo, `README.md`, `docs/CURRENT_STATE.md` e `docs/NEXT_STEPS.md`.
2. Ler `docs/DECISIONS.md`, a arquitetura e os documentos relevantes à tarefa.
3. Consultar `.harness/STATE.json` e `.harness/CURRENT_TASK.md`, se presentes. Conferir os fatos no código e no filesystem.
4. Conferir Git e alterações existentes antes de editar; preservar trabalho alheio. Sem Git, registrar essa limitação.
5. Distinguir requisito aceito, proposta, implementação e verificação. Uma proposta documental não é funcionalidade entregue.
6. Executar somente o escopo autorizado. Não instalar dependências por descoberta, nem usar CLIs que baixem pacotes implicitamente.
7. Nesta máquina, consultar `C:\Users\renan\.codex\RTK.md` e prefixar shell com RTK quando disponível; isso é convenção local, não requisito do produto.

## Regras arquiteturais

- Núcleo independente da web, de Codex/Claude/Gemini e do Harness global.
- Simulação híbrida: estado, regras e probabilidades primeiro; LLM somente por necessidade explícita, com orçamento e registro.
- Branch Reality parte de snapshot completo e imutável; pai e irmãos não compartilham estado mutável.
- Memória de desenvolvimento é separada da memória de agentes simulados.
- Observer e Scientist não alteram silenciosamente a sociedade auditada.
- Resultados expressam futuros condicionados às premissas, nunca garantia de futuro real.
- Não introduzir CrewAI, LangGraph ou equivalente sem registrar problema, alternativas, custo e teste que justifiquem a escolha.
- Criar módulos físicos apenas quando houver comportamento que os justifique.

## Encerramento e handoff

1. Atualizar `docs/CURRENT_STATE.md` com mudanças reais, verificações e limitações.
2. Atualizar `docs/NEXT_STEPS.md` com uma próxima tarefa executável e critérios de aceite.
3. Registrar decisões duráveis em `docs/DECISIONS.md`, com alternativas e consequências. Não apagar decisões substituídas.
4. Atualizar o resumo em `.harness/CURRENT_TASK.md` e o estado; criar checkpoint quando o Harness estiver disponível. Nunca tratar checkpoint do Harness como backup do código.
5. Registrar memória durável no Memory Core quando acessível; não copiar todo o projeto para lá. Se a escrita falhar, deixar a pendência nos arquivos locais.
6. Informar arquivos alterados, testes executados, falhas e trabalho pendente. Não afirmar testes, commits, deploys ou implementações que não ocorreram.

Ver o procedimento completo em [docs/HANDOFF.md](docs/HANDOFF.md).
