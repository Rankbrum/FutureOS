
# Missão atual — M1

## Objetivo

Provar o kernel local sem LLM: população, 10 ticks, snapshot completo, três branches isolados, 20 ticks adicionais e comparação numérica.

## Estado

Em implementação. Entradas do projeto, Harness e Memory Core consultados; workspace FutureOS confirmado. Git inicializado em main sem commit/remoto; runtime Python 3.13.15 verificado. D010 registra stack e horizonte autorizado.

## Divisão de trabalho

Contratos/RNG/validação, motor/população e testes são arquivos separados. Codex principal consolida snapshots/branches/CLI e é o único escritor do Harness e da memória durável.

## Validação pendente

Determinismo, retomada, serialização, isolamento, origem, ordem dos branches, eventos/reach, métricas e entradas inválidas; demo e documentação final. Não há teste aprovado registrado nesta etapa.

## Próxima ação

Consolidar módulos, executar unittest e demo, corrigir falhas, documentar evidências e criar checkpoint final. Checkpoints do Harness não armazenam código nem snapshots da sociedade.
