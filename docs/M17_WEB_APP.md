# M17 Web App (primeira interface)
Stack: Flask (API) + HTML estático (frontend). Nenhum framework pesado.
Estrutura: apps/web/index.html (UI), apps/api/app.py (API).
Endpoints: /health, /api/population/plan, /api/population/validate, /api/scenario/validate, /api/experiments.
Demo offline: population fake + pricing scenario + seed 2026.
Limitações: sem banco, sem auth, sem LLM obrigatório, sem distribuição.
Core intacto: todos os contratos M1-M16 reutilizados; nenhuma lógica científica movida para frontend.
