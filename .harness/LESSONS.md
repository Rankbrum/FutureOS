# Lições operacionais

- Diretórios vazios não comprovam implementação. Nove arquivos iniciais tinham zero bytes.
- Harness init encerra quando .harness existe; preencher compatibilidade local foi necessário.
- context/resume mostram resumos e não expandem links.
- Checkpoint do Harness salva metadados e CURRENT_TASK; não salva código ou simulação.
- O wrapper graphify-mcp existir não comprova dependências MCP presentes.
- Bibliotecas globais e MCPs do desenvolvedor não são dependências ou permissões do FutureOS.
- RTK executa binários; cmdlets PowerShell precisam de `rtk proxy powershell -NoProfile -Command ...` e leitura UTF-8 explícita.
- Snapshot de simulação conserva RNG, eventos futuros, memória e métricas; checkpoint do Harness guarda somente continuidade do desenvolvimento.
- Validação deve preceder deepcopy, e JSON deve rejeitar ciclos, profundidade excessiva e Unicode inválido com mensagem clara.
- Um mesmo seed em branches só é pareamento válido quando origem completa, horizonte, versões, intervenção e elegibilidade são coerentes.
- Tempo de relógio não integra igualdade de resultados reproduzíveis; medir escopo e carga concorrente explicitamente.
- Baseline OAT uniforme é diferente da população sintética heterogênea; reach0/1 pode mudar consumo do RNG compartilhado.
- Reagregação de summaries deve validar configuração/intervenção completas, não apenas tipos dict e métricas finitas.

- Streams por mecanismo não isolam automaticamente agentes/ticks: usar contexto indexado onde necessário.
- Todo loop que emite trace deve ter ordem canônica, inclusive limpeza de overrides.
- IDs estruturados evitam aliases de trajetória; não inferir dono por prefixo textual.
- Coerção int/float no decoder pode mudar hashes JSON; schema2 preserva tipos numéricos aceitos.
- Medir trace e summary completos antes de atribuir custo a cópia/validação/hash.


## M6.1 — 2026-10-01

- Inspeção/documentação não comprova mudança no arquivo. M5 alegava return rows, mas código e teste preservam retorno independente.
- _chain incremental não elimina extração/cópias/validação histórica.
- Cumulativos se sobrepõem; RSS Windows inclui imports. Preservar dispersão e não dar mediana ao piloto120.
