
# Missão atual — M2 concluída

## Objective

M2 - Experimentos multi-seed, comparacao pareada e sensibilidade local

## Estado verificado

M2 implementada em Python 3.13 stdlib. Aceite principal de 100 seeds, 21 agentes, 3 branches e 30 ticks e repeat passaram; 100 testes OK em 34,736s. Sensibilidade demonstrativa de 10 seeds e OAT de aceite de 100 seeds concluídos. Estado final completed refere-se à missão M2.

## Concluído

Runner/summaries/IDs/hash, estatística populacional e distribuições das seis métricas, comparação pareada, OAT com baseline explícito, relatórios mínimos e CLI compatível. Baseline 100: 383,342s / 0,783 runs/s; repeat 318,193s, manifest/runs/aggregate/comparison iguais. A 43,7619%, B 28,3333%, C 61,0952%; A > B 94/100, C > A 97/100, C > B 100/100. Saída: 305 arquivos, 892.504 bytes, sem snapshots completos. Replay entre processos: estado completo dos ticks 11–30 e final iguais; origem intacta. OAT 10: 12 experimentos, 360 runs, 436,767s. Reagregação final dos artefatos coincide.

OAT 100: 2 experimentos únicos / 600 runs / 756,925s. Incentivo C 20→30: média 61,0952%→70,1429%, maior em 84/100 seeds e 16 empates; A/B métricas e hashes finais iguais por seed. Baseline CLI idêntico ao benchmark e todos os relatórios de variantes revalidados. Saída 3.586.770 bytes. Docs, decisões e Memory Core atualizados no encerramento; checkpoint final referencia este resumo, ID no STATE.

## Limites

Modelo sintético não calibrado e sem representatividade real; frequência simulada não é probabilidade real. Uma stream RNG pode desalinha-la após consumo diferente. Cópias/logs/memórias crescem; benchmark sob carga concorrente não prova escala. Summaries não retomam estado final; escrita de lote sem transação. Git main sem commit/remoto. Sem dependências novas, web, LLM, banco ou MCP externo. Root único escritor Harness; seus checkpoints não são backup de código.

## Ação pendente e continuidade

Ler docs/EXPERIMENTS e M2_REPORT além de CURRENT_STATE/NEXT_STEPS/DECISIONS; não depender deste resumo. D013–D015 implementadas. Próxima proposta M3: trajetórias/RNG por mecanismo; ainda não iniciada, aguarda escopo autorizado pelo Founder. Resultados são ignorados pelo Git; docs preservam evidência portátil. Fonte oficial FutureOS no Memory Core; nenhuma memória pessoal/credencial importada para a sociedade. Não executar instalação ou avançar para UI/LLM automaticamente.
