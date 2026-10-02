# Experimentos multi-seed e sensibilidade M2

Protocolo local Python 3.13, somente biblioteca padrão. O kernel M1 e seus snapshots completos continuam intactos. O relatório usa snake_case, como o núcleo (D010): `adoptionRate` corresponde a `adoption_rate`, e analogamente para trust, sentiment, intent e contagens.

## Executar

```powershell
python -m futureos experiment --scenario scenarios/kernel-demo.json --seeds 1:100 --ticks 30 --output results/experiment-demo
python -m futureos experiment --scenario scenarios/kernel-demo.json --seeds 1:10 --ticks 30 --sensitivity scenarios/sensitivity-demo.json --output results/sensitivity-demo
python -m futureos experiment --scenario scenarios/kernel-demo.json --seeds 1:100 --ticks 30 --sensitivity scenarios/sensitivity-acceptance.json --output results/sensitivity-100
python -m benchmarks.experiment --seeds 100 --ticks 30 --output results/benchmark-new --verify-repeat
python -m unittest discover -s tests -v
```

`1:100` inclui os dois extremos; uma lista como `1,5,20` também é aceita. Seeds são inteiros uint64 distintos, não vazios, ordenados canonicamente. A CLI limita cada chamada a 100.000 seeds, rejeitando ranges/listas maiores antes de materializá-los; a API do runner não recebe esse limite operacional. Cada branch do cenário usa exatamente as mesmas seeds. `--ticks` é o horizonte **total**: 30 significa 10 ticks comuns e 20 por branch na fixture. O cenário legacy `kernel-demo.json` é reutilizado sem alterar seu schema; ID versionado mais SHA-256 canônico identifica conteúdo. Branches e eventos também são normalizados por ID/tempo.

O diretório de saída deve ser ausente ou vazio. Uma segunda execução deve usar um novo caminho. A CLI anterior (`python -m futureos --seed 2026`) continua sendo a demo M1 com snapshots completos.

## Execução e isolamento

`run_experiment(scenario, seeds, branches=None, ticks=None, population_overrides=None)` aceita caminho ou dict do cenário. `branches` pode substituir a lista de definições `{id,label,price,incentive}`. Cenário, seeds, parâmetros e todas as intervenções são validados antes do primeiro tick. Sensibilidade faz essa validação sobre todas as variantes antes de começar qualquer experimento.

Para cada seed, o runner gera uma população nova, executa o passado comum, cria um snapshot completo imutável e restaura A/B/C em cópias independentes. A comparação M1 verifica linhagem, configuração, seed, horizonte e elegibilidade. Os estados completos são liberados por seed; o lote conserva somente summaries, IDs/checksums e medidas de volume. Não há estado global de RNG ou de população.

Cada run identifica `run_id`, `experiment_id`, seed, scenario/engine/model/schema/RNG, branch, intervenção, configuração, horizonte, agentes ativos, snapshot/checksum de origem/final e as seis métricas. IDs usam hashes do protocolo, seed e branch, sem relógio. A origem é comum apenas entre branches da mesma seed. Outros experimentos têm suas próprias origens.

Pareamento RNG: `shared-origin-single-stream-v1`. Irmãos copiam exatamente estado e contador da mesma stream. A fórmula consome ruído para cada agente mesmo se noise=0; a fixture econômica A/B/C mantém consumo compatível. Alterar reach, especialmente para 0 ou 1, pode mudar o consumo e desalinha amostras futuras. Mesma seed conserva uma realização controlada, mas não promete choques idênticos por mecanismo após divergência de consumo. Não houve mudança de algoritmo/engine para M2.

## Agregação e comparação

Cada branch contém seis métricas: `adoption_rate`, `average_trust`, `average_sentiment`, `average_intent`, `interaction_count`, `event_count`. Adoção e médias usam agentes ativos no estado final. Contagens são acumuladas desde tick zero, incluindo o passado compartilhado. Não se agregam ticks de uma trajetória como se fossem repetições independentes.

Para cada métrica: count, mean, median, min, max, variance e standard_deviation **populacionais**, com denominador N (`statistics.pvariance`/`pstdev`). Para N=1, ambas as dispersões são zero. A distribuição conserva `{seed,run_id,value}` em ordem de seed. O método descreve o conjunto simulado; não estima erro amostral nem fornece intervalo de confiança de população real.

Cada par não ordenado de branches informa deltas de média/mediana, distribuição de deltas pareados, média/mediana/desvio dos deltas e contagens de maior/menor/empate. O sinal é **left minus right**. Diferença entre medianas e mediana das diferenças aparecem em campos distintos. `greater` significa apenas valor numericamente maior; trust/interações não recebem interpretação de preferência. Frequências descrevem somente esse espaço simulado.

Agregação/comparação rejeitam summaries sem proveniência, duplicações e versões/configurações/horizontes/populações incoerentes. Comparação exige conjunto completo das mesmas seeds. Intervenção e label de uma branch devem ser uniformes em todas as seeds; origens e elegibilidade devem coincidir entre irmãos da mesma seed.

## Sensibilidade One-At-A-Time

O protocolo versionado em `scenarios/sensitivity-demo.json` define uma lista de fatores. Cada análise fixa um baseline explícito e muda somente um parâmetro:

- `population`: price_sensitivity, openness, trust, conformity, influence, risk_tolerance. Valor absoluto [0,1] aplicado a **todos** os agentes no tick zero, depois da geração e antes de eventos/ticks; não consome RNG adicional. Isso também sobrescreve traits especiais do influenciador. As labels de grupo geradas permanecem fixas. Baseline 0,50 uniforme é diferente da população heterogênea original.
- `event`: evento identificado por `event_id`; altera reach ou um campo existente do payload (`amount`, `sentiment_delta`, etc.), preservando tipo, instante, ID e demais campos. O contrato do kernel limita valores conforme evento.
- `branch`: branch identificada por `branch_id`; muda price ou incentive, preservando os demais campos. O incentive vira payload amount do evento INCENTIVE no tick da bifurcação.

Cada variante é um experimento próprio, com mesmas seeds, horizonte e branches, e novo conteúdo/hash quando há alteração. As comparações internas A/B/C continuam exigindo origem comum por seed. A sensibilidade compara summaries entre variantes por **branch e seed**, com baseline, deltas de mean/median e deltas pareados. Não afrouxa `compare_branches` para comparar mundos com origens diferentes. Especificações exatamente iguais podem reutilizar execução compacta por cópia independente.

O protocolo completo, valores, baseline, manifestos, runs e agregados das variantes ficam em `sensitivity.json`. Seus tempos variáveis ficam em `benchmark.json`. Sem protocolo, `sensitivity.json` registra `status: not_requested`.

## Artefatos e medição

```text
results/experiment_<id>/
  manifest.json
  runs/run-000001.json ...
  aggregate.json
  comparison.json
  sensitivity.json
  benchmark.json
```

Arquivos de runs usam índice, nunca o ID fornecido como caminho. Manifesto guarda cenário completo uma vez; runs guardam resumos e proveniência. Nenhum snapshot completo é gravado no lote. Esses resumos permitem repetir pelo protocolo, mas não retomar do estado final; a API/CLI M1 continua disponível quando retomada é necessária. Saídas geradas são ignoradas pelo Git.

`perf_counter` mede preflight, simulação, serialização temporária para sizing e relatório; escrita dos arquivos fica fora do tempo total. Há duração total, média por run, runs/s, agentes/seeds/branches/ticks, ticks físicos executados, tempo do passado comum e da continuação. Duração atribuída a uma run = continuação + quota igual do passado comum da sua seed; overhead geral só entra no total. O benchmark inclui runtime/plataforma, bytes de snapshots de origem/final e contagem de memórias. Assim é possível medir crescimento sem persistir os snapshots.

Manifest/runs/aggregate/comparison/sensitivity são determinísticos. Relógio, plataforma e performance são evidência variável e ficam separados. O benchmark `--verify-repeat` compara todos os campos determinísticos da reexecução com seeds em ordem invertida; a execução interna permanece canônica. Não houve otimização antecipada, paralelismo de runs, cache de snapshots persistido ou dependência numérica externa.

Salvar vários arquivos não forma uma transação: erro de disco pode deixar lote parcial. Diretório novo reduz mistura acidental e não substitui backup/versionamento. Checksums detectam conteúdo, não autenticam autor. Volumes/timing dependem de máquina/carga; não demonstram escala fora do caso medido.

## Limites científicos

O modelo ainda é sintético; suas regras não foram calibradas; agentes não representam população real; frequência simulada não equivale a probabilidade real. Resultados servem para testar infraestrutura e explorar comportamento do modelo. Não são recomendações comerciais ou prescritivas. Sem web, SaaS, banco externo, MCP externo, LLM, análise generativa ou calibração real.

Evidência de execução, benchmark e exemplos numéricos ficam em [M2_REPORT.md](M2_REPORT.md); estado e continuidade em [CURRENT_STATE.md](CURRENT_STATE.md) e [NEXT_STEPS.md](NEXT_STEPS.md).
