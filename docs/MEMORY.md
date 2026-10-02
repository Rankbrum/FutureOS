# Memória e autoridade

## Três memórias distintas

| Memória | Conteúdo | Local |
|---|---|---|
| Desenvolvimento portátil | Arquitetura, decisões, estado, evidências, próxima missão | Documentos deste projeto |
| Operação de desenvolvimento | Tarefa atual, última IA e checkpoints resumidos | `.harness/` |
| Sociedade simulada | Observações dos agentes, relações, procedência e tick | M1: contratos em `futureos/models.py`, transições no engine e estado completo nos snapshots; permissões ampliadas futuras |

Agentes simulados não consultam o Memory Core pessoal do Founder nem recebem automaticamente skills/MCPs de desenvolvimento.

## Ponte local ao Memory Core

Fonte oficial nesta máquina: `C:\Users\renan\Memory Core`.

Memória específica: `04_PROJECTS\FutureOS\PROJECT.md`. A referência global a IA-Memory-System foi identificada como contexto de outro projeto; seus arquivos foram preservados. Não herdar sua stack, backlog ou implementação.

Precedência: decisão explícita do Founder > Memory Core oficial > caches operacionais. Os documentos de FutureOS são a base técnica portátil; decisões oficiais relevantes devem ser reconciliadas aqui, com ID e data. `.harness` e arquivos de cada IA não devem criar versões concorrentes.

Sem acesso ao Memory Core, ler o projeto e registrar a indisponibilidade. A ausência não exige instalar ferramenta nem impede a execução do produto. Evitar copiar registros globais privados para um repositório compartilhável.

## Atualização

Manter na memória externa apenas identidade, decisões duráveis, estado e ponte para os documentos, além do resumo de sessão exigido pelo protocolo do Codex. Não sincronizar automaticamente conversas, respostas completas de provedores ou credenciais.

Para memória de agentes, a arquitetura prevê registros versionados com origem, visibilidade, tempo lógico, branch e política de retenção. Embeddings e banco de grafos estão adiados.
