# Memória estável

FutureOS é o projeto desta pasta. A memória global que aponta IA-Memory-System refere-se a outro projeto.

A autoridade é: Founder explícito > Memory Core oficial > documentação portátil de FutureOS > Harness operacional/caches. A frase genérica do CLI não modifica essa hierarquia.

Leia [docs/MEMORY.md](../docs/MEMORY.md). Memory Core nesta máquina: `C:\Users\renan\Memory Core`; memória do projeto: `04_PROJECTS\FutureOS\PROJECT.md`. Sem acesso externo, os documentos locais permanecem suficientes para continuar.

Memória de agentes simulados faz parte dos snapshots M1 e não recebe memórias pessoais de desenvolvimento. Não guardar segredos ou conversas completas.

M2 acrescenta experimento por seeds pareadas, summaries independentes, estatística/distribuição e OAT com baseline explícito. Timings são separados da igualdade determinística. Nenhuma frequência sintética equivale a probabilidade real; leia docs/EXPERIMENTS e M2_REPORT para premissas, sizing e evidências. D013–D015 complementam D010–D012; status final e próximo passo em CURRENT_STATE/NEXT_STEPS.

M3 concluída em 2026-10-01: 164 testes OK, RNG contextual, trace/deltas/trajectory, hashes/replay/divergência. D016–D018; protocolo AUDIT_TRAJECTORIES e evidência M3_REPORT. Default M1/M2 v1 preservado, M3 v2 explícito. Trace60 teve overhead relevante; próximo perfil CPU/retensão é proposta, não execução autorizada.


## M6.1 — 2026-10-01

M6.1 substitui as alegações M4/M5/M6 não verificadas. Suite atual164/164OK24,373s,18 medições e profile60. _chain já incremental; deepcopy(rows) contratual. D020 mantém hash-v1 e prioriza cópia/validação. Fonte: docs/M6_1_VALIDATION.md.

## M13 — 2026-10-01, estado atual

M12.1 REAL8agentes/seed2026/5ticks; M13 planner opcional no schema PopulationSpec,
fake offline, JSON revisável, warnings/assumptions obrigatórios, provenance allowlist.
243testesOK20,613s; engine/models/RNG/audit/hash/codec/snapshots/validation/branches/
fixture population preservados byte a byte. Base incompleta M11/M12 e CLI reparadas
nesta missão; deepcopy consulta restaurado. Providers reais/ScientistExplainer não
validados; Scientist continua stub. Próxima proposta M14 em docs/NEXT_STEPS.md.
