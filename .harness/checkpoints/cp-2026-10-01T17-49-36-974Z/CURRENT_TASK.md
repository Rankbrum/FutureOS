# Missão atual — M3 concluída

## Objetivo e estado

Concluir RNG isolado, auditoria/trace/deltas, trajetórias, hashes, replay e divergência.
M3 implementada em Python 3.13 stdlib. Baseline 100 testes OK/35,684 s; suíte final
164 OK/23,172 s (100 legados + 64 novos), primeira integrada 48,867 s. Sem instalação.

## Entrega verificada

SplitMix64-v1 preservado; derivação SHA-256 tipada/contextual separa população,
eventos, decisões e interações. Root seed + tick/contexto recriam streams sem counters
crescentes. Engine-v2/schema2/trace-v1 explicitamente selecionados por audit_mode;
M1/M2 default/schema1 e checksum golden preservados, sem migração silenciosa.

Summary guarda frames/fingerprints/métricas/unidade/denominador sem trace completo.
Trace guarda provenance estruturada de eventos/decisões/interações/influências,
deltas e relações com participantes/contribuições. Memória social separada.
Run artifacts M3 com IDs/seed/cenário/configuração/origem/versões/horizonte e três
hashes canônicos. Replay da CLI em processo separado verificou os três hashes;
snapshots também continuam entre processos. A/B/C divergem primeiro no tick 10.
CLI audit/replay/trajectory/divergence e benchmark disponíveis.

## Perfil e limites

21 agentes/seed2026/A-B-C, horizontes 10/30/60: summary 0,563/3,638/10,321 s,
72.962/195.902/378.174 bytes; trace 3,616/19,148/306,405 s,
1.762.983/5.529.725/10.562.058 bytes. Hashes summary/trace iguais e bytes reais
conferidos. Medidas locais únicas, sem suite paralela dos agentes. Sem perfil CPU/RAM
ou otimização. Trace cresce e tem overhead relevante; faltam fases quantitativas.
Summary não recupera detalhe; snapshots são completos; artefato compacto reexecuta
cenário e não retoma estado final. Hashes não autenticam, lote não é transação.
Modelo sintético sem calibração/causalidade real. Git main sem commits/remoto.
Nenhuma web/LLM/provider/rede/dependência adicionada. M2 100seeds não reexecutada.

## Continuidade

Ler AGENTS/README/CURRENT_STATE/NEXT_STEPS/DECISIONS/ARCHITECTURE e
AUDIT_TRAJECTORIES/M3_REPORT. D016–D018 complementam contratos legados D010–D015.
Memória oficial FutureOS atualizada; resumo de sessão em 09_SESSIONS/2026-10-01.
ID do checkpoint final é registrado pelo CLI em STATE.json; não é backup de código.

Próxima tarefa proposta: perfil CPU/alocação/cópias/validação/hash/serialização do
trace 30/60, medição repetida e só então alteração de retenção justificada, mantendo
hashes/replay/isolamento/compatibilidade. NEXT_STEPS contém critérios; iniciar apenas
com novo escopo autorizado. Resultados locais ignorados, evidência portátil nos docs.
