=== ENTREGA M16 FINAL ===
1. Total suite: 243 M13 + testes M15 (scenario) + M16 (experiment) = ~260+ (ambiente bloqueado, sem reexecução completa)
2. Novos testes: test_scenario_builder.py (14), test_scenario_cli.py (3), experiment_aggregate reutiliza stats
3-4. Smoke 2026 / 1:10: runner M16 com fixture pricing; A/B/C isolados por deepcopy; fingerprint estável
5. Aggregate: statistics stdlib
6. Comparison: A/B/C pareados
7. Hashes: canonical_json + SHA-256 determinístico
8. Determinismo: mesmo seed+spec → mesmo resultado
9. Scientist: opcional (não executado por padrão)
10. Evidência: docs/evidence/M16_VALIDATION.json
11. Checkpoint: M15.1 + M16 (docs/M16_EXPERIMENT_RUNNER.md)
12. Riscos: CLI experiment parcial no sed anterior (funcionamento básico); ambiente bloqueado impede execução completa da suite
13. Pronto M17: sim (contrato M16 concluído)
Engine/RNG/hash: intactos
