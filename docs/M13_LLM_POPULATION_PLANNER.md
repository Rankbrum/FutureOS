# M13 — LLM Population Planner

**COMPLETE**, execução real em 2026-10-01, Python 3.13.15, somente biblioteca padrão.
Suíte: **243 testes OK**, 0 falhas/erros/skips, 20,613 s. [Resultado](evidence/M13_SUITE_RESULT.json),
[log](evidence/M13_SUITE.txt), [smoke](evidence/M13_SMOKE_RESULT.json).

## Fronteira e revisão humana

```text
descrição + tamanho/contexto opcionais
→ LLMPopulationPlanner → adapter M11 → resposta JSON
→ PopulationSpec.from_json → validate_population_spec
→ proposta PopulationSpec → JSON para revisão humana
→ geração explícita posterior com spec revisada + seed
→ agents → relationships → World → Simulation
```

`futureos/population_planner.py` não importa generator nem engine e não materializa
agentes. A CLI somente salva a proposta. JSON é a fronteira de revisão; não existe
UI nem registro de aprovação nesta missão. O operador pode editar weights, traits,
size, relationship_policy e assumptions e recarregar pelo mesmo validador. Chamadas
explícitas ao generator são a segunda etapa, de responsabilidade do chamador.

```python
from futureos.llm_provider import FakeLLMProvider
from futureos.population_planner import LLMPopulationPlanner

spec = LLMPopulationPlanner(FakeLLMProvider()).plan(
    "Donos de pequenos restaurantes avaliando uma solução de automação.",
    size=8, context={"country": "Brasil", "nature": "hipótese sintética"},
)
proposal = spec.to_json()  # dict independente, pronto para serializar/revisar
```

Sem provider, o planner falha com `LLMUnavailable`. A geração manual não importa
nem exige provider. O fake é uma fixture genérica e **não interpreta o setor**:
seu archetype padrão possui todos os traits 0.5 e weight 1. O exemplo de restaurantes
é entrada da execução, nunca uma população hardcodada no planner. Tamanho omitido
usa a proposta do provider; o fake escolhe 100. Tamanho explícito divergente falha.

## Contrato existente, prompt e validação

Não há schema paralelo. `PopulationSpec`, `Archetype` e `Traits` permanecem os
contratos M12. `Archetype.traits` contém valores numéricos; `trait_distributions`
contém overrides **globais**, aplicados a todos os archetypes. Distribuições por
archetype do exemplo conceitual do pedido não são suportadas pelo contrato atual.

Traits aceitos, derivados de `VALID_TRAIT_KEYS`: openness, risk_tolerance,
price_sensitivity, influence e conformity. Valores estão em [0,1]; campos
omitidos usam os defaults existentes de Traits (0.5). Não há mapeamento de
`technological_affinity` ou outro trait desconhecido.

`build_population_prompt()` explica população sintética, ausência de
representatividade/calibração, estatísticas como hipóteses, assumptions explícitas,
weights com soma 1 ± 0.01, bounds, traits/distribuições suportados, source obrigatório,
warnings e revisão. Mensagem system contém o contrato; description/context ficam em
JSON na mensagem user, tratados como dados. A implementação também valida a resposta
independentemente do cumprimento do prompt.

Distribuições: fixed (value), uniform (min/max), bounded_normal (mean/spread,
min/max opcionais 0/1). Mean é obrigatório e deve estar nos bounds; spread >= 0.
No generator reparado, bounded_normal usa Box-Muller com **clipping**, não uma
normal truncada por rejeição. Pode concentrar massa nos bounds. Fixed e intervalos
degenerados não consomem draws. Não há NumPy ou nova RNG.

JSON inválido, duplicação de campos, NaN/Infinity, tipos booleanos como números,
traits/distribuições/campos desconhecidos, IDs duplicados, weights/bounds inválidos,
source diferente, assumptions vazias e warnings incompletos falham com erro útil.
Valores significativos não são corrigidos silenciosamente. A alocação M12 usa
largest remainder, ordenado por ID; pesos já aceitos pela tolerância são normalizados
somente para calcular quotas inteiras, sem modificar a spec.

## Assumptions, warnings e provenance

Toda proposta usa `source="llm_generated"`, assumptions não vazias e ambos:

- `SYNTHETIC_POPULATION`
- `UNCALIBRATED_POPULATION`

As três assumptions da execução real do fake são:

1. Esta população é sintética e não calibrada.
2. Traits e pesos são hipóteses para revisão humana.
3. A proposta não representa estatísticas da população real.

O planner define somente `metadata.provider`, `metadata.model` quando disponível
(null quando ausente) e `metadata.planner_version="population-planner-v1"`.
Metadata vinda do LLM deve estar vazia, inclusive nos archetypes; não se copia
`__dict__`, configuração, request, header ou credencial do provider. Texto de erro
bruto do provider não é exibido nem persistido. Formas reconhecíveis de credentials,
como Authorization/Bearer, atribuições de API keys e private keys, são rejeitadas em
propostas/provenance, sem redigir silenciosamente. Essa verificação não certifica
qualquer segredo arbitrário escondido em prosa. Description/context não são salvos
na spec; o exemplo público escolhido para evidência não contém dados privados.

M11 usa `LLMRequest(messages, metadata, response_format)` e `LLMResponse(content,
provider, model, usage)`. Fake configurável aceita JSON/texto/response ou ProviderError,
guarda requests somente em memória e não acessa rede. Providers reais poderão
implementar esse contrato; não foram conectados nem validados nesta missão.

## CLI e segunda etapa

Na raiz, usando Python 3.13 (nesta máquina, `rtk proxy py -3.13`):

```powershell
python -m futureos population plan --description "Donos de pequenos restaurantes avaliando software de automação" --size 100 --provider fake --output population-spec.json
```

A CLI valida, salva JSON UTF-8, imprime warnings/assumptions e recusa sobrescrever
arquivo existente. `--size` e `--context` são opcionais. Comando real size100 foi
executado com saída em `results/m13/population-spec-cli.json`; nenhum tick foi
iniciado pelo comando. A spec real do smoke size8 está em
[M13_POPULATION_SPEC.json](evidence/M13_POPULATION_SPEC.json).

Após revisão, carregar o JSON e executar explicitamente:

```python
from pathlib import Path
from futureos.population_spec import PopulationSpec
from futureos.population_generator import (
    generate_population_with_relationships, create_simulation_from_population_spec,
)
from futureos.engine import run_ticks

spec = PopulationSpec.from_json(Path("population-spec.json").read_text(encoding="utf-8"))
agents = generate_population_with_relationships(spec, seed=2026)
initial = create_simulation_from_population_spec(spec, seed=2026, audit_mode="trace")
final = run_ticks(initial, 5)
print(final.metrics)
```

O helper materializa a população novamente; o exemplo compara as etapas e não
anexa agentes duplicados. A spec revisada completa permanece na metadata do World,
montada fora do engine. O planner real pode variar entre chamadas; **JSON validado
igual + seed igual** é o compromisso determinístico da geração posterior.

## Execução real e reparos da base

A tentativa inicial executou 160 testes, com 4 falhas e 4 erros (14,978 s), e o
smoke falhou num import M12 inválido. Não foi bloqueio de ambiente. M11 tinha stubs,
a CLI antiga não existia, dois arquivos de testes eram texto inválido, a geração
ignorava a spec e o helper de Simulation estava ausente. Docs/Harness/Memory Core
ainda registravam M6.1. Os reparos necessários foram feitos nesta missão; não se
atribui essa entrega a conversas anteriores. Histórico anterior foi preservado.

[M12.1](M12_1_SMOKE_RESULT.json): seed2026, 8 agentes, 16 relações, 5 ticks,
21 interações, average_intent0.35038789263698844. [M13](evidence/M13_SMOKE_RESULT.json):
fake → spec → validação → JSON → generator/relationships → Simulation → 5 ticks;
8 agentes, 24 relações, 41 interações, average_intent0.3638538198226207, adoption_rate0.
Ambos em trace, repetidos com igualdade completa e três hashes iguais.
Esses números são resultados sintéticos condicionados aos parâmetros, sem
probabilidade real ou conclusão comercial sobre restaurantes.

Suíte completa: **243 testes OK** (164 legados + 9 adapter + 19 generator +
16 relationships + 35 planner/CLI), sem skips. Golden legado, replay entre
processos, summary/trace, snapshots e isolamento passam. Engine, models, RNG,
audit/hash, codec, snapshots, validation, branches e fixture population estão
byte a byte iguais à cópia do início desta missão; SHAs na evidência M13.
`audit_runs.trajectory_from_run` voltou a retornar deepcopy, corrigindo alias
da consulta, sem mudar o algoritmo de hash.

## Inventário e limites

Criados: population_planner.py, tests/test_population_planner.py,
tests/test_relationships.py, benchmarks/m13_validation.py, este relatório,
M12_1_SMOKE_RESULT.json e evidências M13 JSON/log.
Alterados: population_spec.py, population_validation.py, population_generator.py,
relationship_generator.py, llm_provider.py, llm_registry.py, __main__.py,
audit_runs.py, tests/test_m11_llm.py e tests/test_population_generator.py; README,
CURRENT_STATE, NEXT_STEPS, DECISIONS, ARCHITECTURE, M11/M12 docs, Harness e Memory Core.

Reexecutar evidência: `python -m benchmarks.m13_validation m12|m13|suite` (escolher
um stage, sem o separador literal). A conferência de bytes no stage m13 exige
a cópia local ignorada `results/m13-baseline/futureos`; em outra máquina, executar
unittest e definir uma baseline própria. Não instala dependências.

Sem agentes LLM nos ticks, RAG, embeddings, dataset, calibração, UI, banco, CRM
ou scraping. ScientistExplainer anterior continua stub, fora do aceite M13.
Git main sem commits/remoto; não existe diff Git histórico. Checkpoint do Harness
é resumo, não backup. Próxima missão recomendada M14 em [NEXT_STEPS](NEXT_STEPS.md).
