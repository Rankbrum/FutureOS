# Índice de decisões

Fonte técnica: [docs/DECISIONS.md](../docs/DECISIONS.md), D001–D023.
Founder > Memory Core > docs portáteis > resumo Harness. context não expande links.
D001–D009 fundação; D010 Python stdlib/Git local; D011 SplitMix64/schema1;
D012 modelo sintético; D013 experimentos pareados; D014 OAT baseline; D015 armazenamento mínimo.
D016 M3 streams SHA-256 indexados mantendo SplitMix64 e versão legada;
D017 summary/trace, deltas e provenance separada da memória social;
D018 artefatos M3/versionamento/hash/replay/divergência, schema2 sem migração implícita.
M3 implementada. Perfil/retenção futuro proposto em NEXT_STEPS; sem autorização nova.


## M6.1 — 2026-10-01

D019: validação atual/manifesto, comparação histórica descritiva. D020: manter hash-v1, sem algoritmo novo; priorizar cópias e validação histórica. Registro canônico: docs/DECISIONS.md.

## M13 — 2026-10-01

D021: reparar base M11/M12/CLI por execução, sem confundir stubs com entrega.
D022: planner opcional no schema M12 existente, validação estrita/Fake offline.
D023: revisão JSON separada de geração, provenance mínima sem segredos,
LLM potencialmente variável e geração determinística condicionada a JSON+seed.
