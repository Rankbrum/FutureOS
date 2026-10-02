# Roadmap

Atualizado em 2026-10-01. Fases representam dependências de aprendizagem, não promessa de datas.

| Marco | Entrega | Critério para avançar | Estado |
|---|---|---|---|
| M0 — Fundação | Auditoria, arquitetura, decisões, arquivos comuns e Harness | Retomada pelos documentos e CLI local verificada | Concluído em 2026-09-29 |
| M1 — Kernel local | Cenário sintético, ticks, RNG, snapshot, retomada, A/B/C | 61 testes e demo 10+20 ticks, zero chamada externa | Concluído em 2026-09-30 |
| M2 — Experimentos e auditoria | Repetições por seed, comparação, OAT e benchmark | Relatório de dispersão, sensibilidade, invariantes e premissas | Concluído em 2026-09-30; aceite/evidência em CURRENT_STATE/M2_REPORT |
| M3 — Auditoria e trajetórias | RNG por contexto, trace/deltas, hashes, replay e divergência | 164 testes, compatibilidade legada e perfil 10/30/60 | Concluído em 2026-10-01; evidência em M3_REPORT |
| Perfil/retenção do trace — próxima tarefa técnica | Identificar custo de cópias/validação/hash antes de otimizar | Medição CPU/memória e igualdade dos compromissos M3 | Proposta em NEXT_STEPS, sem nova autorização de implementação |
| Runtime híbrido — posterior | Provedor falso/replay e depois adaptador LLM opcional | Orçamento, timeout, validação, retries e replay testados | Planejado; sequência anterior M3 adiada pela recomendação técnica, sem implementação |
| M4 — Web mínima | Criar, executar e comparar um experimento | Mesmo Core da CLI; estado de execução e limites visíveis | Planejado |
| M5 — Escala orientada por medidas | Concorrência, persistência/filas adequadas e operação | Perfil real de custo/latência e testes de isolamento | Adiado |

Branch Reality é parte de M1. Milhares de agentes, centenas de futuros, autenticação, cobrança, multiusuário, deploy, dashboards completos e serviços distribuídos não são requisitos da fundação.

A promoção entre marcos exige atualizar DECISIONS, CURRENT_STATE e NEXT_STEPS. Nenhum framework de agentes está pressuposto.
