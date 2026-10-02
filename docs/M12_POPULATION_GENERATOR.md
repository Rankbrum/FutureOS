# M12 Population Generator — pipeline verificado

Atualizado em 2026-10-01. **M12.1 VALIDATED**, execução real:
[resultado JSON](M12_1_SMOKE_RESULT.json). Seed2026, 8 agentes, 16 relações,
5 ticks/trace, métricas e repetição completa com três hashes iguais.

```text
Manual/JSON → PopulationSpec → validação → traits por archetype + overrides globais
→ generate_population → generate_relationships → World → Simulation
```

`generate_population_with_relationships(spec,seed)` é a orquestração oficial.
`create_simulation_from_population_spec(spec,seed,simulation_id="population-simulation",
world_id="population-world",audit_mode="summary")` monta World/provenance e chama
o engine existente. Não altera engine, models, RNG ou hash.

Archetype.traits é Traits numérico. PopulationSpec.trait_distributions contém
overrides globais fixed/uniform/bounded_normal. Largest remainder aloca tamanho
exato com desempate por ID; pesos aceitos no epsilon0.01 são normalizados somente
para quotas, mantendo spec intacta. IDs agent-001..., metadata archetype_id/source.
bounded_normal usa Box-Muller clipped aos bounds; não é amostragem por rejeição.

SeededRandom/derive_seed existentes: stream agents e relationships/policy separadas.
Políticas random_sparse, clustered, influencer_centered; uniform preserva vínculos
de entrada e não gera novos (a população criada inicia sem vínculos). Cópias não
compartilham traits, state, metadata ou vínculos mutáveis; policies inválidas falham.
35 testes M12/relationships reais passam na suíte243. Manual não exige provider.

Este arquivo anterior alegava integração completa, mas a tentativa inicial desta
missão encontrou import inválido, spec ignorada e helper ausente. Esses comportamentos
foram reparados agora; não atribuir entrega ao histórico de chat. M13 propõe a mesma
spec antes da geração: [relatório](M13_LLM_POPULATION_PLANNER.md).
Sem dataset/calibração/UI; warnings e assumptions permanecem como provenance.
