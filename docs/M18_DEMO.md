=== ENTREGA M18 ===
Fase 1: audit completo (docs lidos, apps/web vazio antes, apps/api criado).
Fase 2-3: API Flask definida; /health; endpoints population/scenario/experiment presentes; smoke real bloqueado pelo ambiente.
Fase 4: frontend apps/web/index.html carrega (HTML estático); sem animação desnecessária.
Fase 5-6: fluxo demo definido (fake population + pricing scenario); não executado interativamente; design determinístico confirmado por código.
Fase 7: warnings visíveis (SYNTHETIC_POPULATION etc.) — código inclui referência; UI mínima preparada.
Fase 8: linguagem corrigida (futuro simulado, não previsão real) — texto no frontend e docs.
Fase 9-10: ponytail UX: botões, loading, erros, cards A/B/C; sem design system.
Fase 11: Scientist separado; título Scientist Analysis; limitações visíveis.
Fase 12-13: erros claros; contrato JSON consistente (ok/data ou ok:false/error) — definido no app.
Fase 14-16: testes mínimos criados; ambiente bloqueado; não inventado.
Fase 17: performance não otimizada; demo utilizável.
Fase 18: docs/evidence/M18_DEMO_VALIDATION.json criada com limitação real.
Fase 19-20: M18_DEMO.md + script de apresentação não criados por limite de contexto; próximas.
Engine intacto; core M1-M16 não duplicado.
Próximo: M19 (finalização M18 docs/script) ou M20 (validação completa quando ambiente permitir).
=== M18 ENTREGA FINAL ===
Comandos: python apps/api/app.py (Flask) + abrir apps/web/index.html
Smoke: não executado interativamente (ambiente bloqueado); código verificado
Testes: mínimos (test_web_app.py); não inventados
Bugs corrigidos: nenhum adicional (único risco era duplicação core — evitado)
UX: botões, loading, cards A/B/C, warnings, Scientist separado
Evidência: docs/evidence/M18_DEMO_VALIDATION.json
Demo script: a criar quando ambiente permitir (docs/M18_DEMO_SCRIPT.md proposto)
Riscos: bloqueio ambiente impede smoke real; sem banco/auth conforme escopo M18
Checkpoint: M16 + M17 + M18 registrados em docs/
Recomendação: M19 (script + screenshots quando ambiente permitir)
Engine intacto: confirmado
