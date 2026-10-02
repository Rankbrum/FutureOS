# Continuidade entre IAs

## Entrada comum

Toda IA começa em AGENTS.md, CURRENT_STATE e NEXT_STEPS. README indexa a arquitetura e as decisões. CLAUDE.md e GEMINI.md apenas encaminham para o protocolo; não contêm versões paralelas de contexto.

Um leitor sem a conversa anterior precisa conseguir responder: o que existe, o que é proposta, por que foi escolhido, o que foi verificado e qual é o próximo trabalho. Os documentos portáteis atendem a esse contrato sem o Harness instalado.

## Retomar com o Harness disponível

Na raiz do projeto:

```text
harness status
harness context
harness resume --ai Claude
```

Trocar Claude por Codex, Gemini ou outra identificação conforme a sessão real. Nesta máquina, usar `rtk proxy harness.cmd ...`. `resume --ai` altera somente identificação e timestamp; não executa a próxima tarefa. Sem `--ai`, resume é leitura.

O contexto do CLI não expande referências: ler também os documentos citados. Seu rodapé genérico não revoga a hierarquia de AGENTS.md. Não executar `start` para retomar uma tarefa existente, pois ele substitui CURRENT_TASK por um template.

## Encerramento

1. Conferir alterações e executar validações adequadas ao que mudou.
2. Atualizar estado, decisões e próxima tarefa nos docs.
3. Preencher CURRENT_TASK do Harness com objetivo, concluído, evidência, pendências e próximo passo.
4. Manter STATE.json coerente. O schema aceita idle, in_progress, paused e completed; completed refere-se à missão atual, não ao produto inteiro.
5. Criar checkpoint com resumo e próxima ação. Não assumir que ele contém código ou todos os docs.
6. Registrar ponte e resumo durável no Memory Core quando disponível.
7. Conferir a consistência entre docs, estado e checkpoint; registrar falhas sem apagá-las.

## Sem Harness

Ler e atualizar os mesmos Markdown. STATE.json é JSON legível, mas não é obrigatório para construir ou executar o produto. Manter evidências e próxima ação em CURRENT_STATE e NEXT_STEPS. Não instalar o Harness como pré-condição.

## Verificação de handoff

Uma nova sessão deve identificar FutureOS, reconhecer M0 documental e M1/M2/M3 executáveis, localizar D001–D018, distinguir Harness de snapshot e ler EXPERIMENTS/M2_REPORT e AUDIT_TRAJECTORIES/M3_REPORT além do estado. Executar unittest e um experimento pequeno dentro do escopo autorizado. M1 verificou kernel/snapshots; M2 ampliou comparação/replay e dispersão; M3 acrescenta RNG contextual, trace/deltas, trajetória, hashes e divergência, com 164 testes finais e perfil 10/30/60. M1/M2 continuam no caminho legado v1; audit_mode seleciona M3 v2. Evidências e checkpoint final ficam em CURRENT_STATE/STATE. Nesta continuação Codex conferiu o estado persistido após a tentativa anterior relatada de Claude; não presume implementação anterior M3 nem equivalência de ambientes. A próxima tarefa é recomendação, não execução autorizada pelo documento.

## Concorrência

Definir um responsável pela tarefa e pelos arquivos de estado. Agentes paralelos devem ter arquivos distintos; consolidar antes do checkpoint. O Harness atual não tem locks nem transação multi-arquivo. Não iniciar duas sessões escrevendo STATE/CURRENT_TASK simultaneamente.
