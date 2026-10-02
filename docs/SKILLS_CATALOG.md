# Catálogo local de skills

Data da observação: **2026-09-29**. Este catálogo registra arquivos encontrados na máquina durante a descoberta, não dependências do FutureOS.

## Escopo e interpretação

Cada nome abaixo é um diretório relativo à raiz indicada, contendo um `SKILL.md`. Alguns são templates aninhados em outros projetos. Encontrar o arquivo não significa que a ferramenta atual o carregou, que suas dependências estão prontas ou que deva ser utilizado.

O catálogo detalha as três raízes pessoais e as duas raízes principais do ECC 2.2.2 no Codex. Também foram contados, sem listar cada cópia, 989 `SKILL.md` em `C:\Users\renan\.codex\plugins\cache` e 1962 em `C:\Users\renan\.claude\plugins`. Esses totais incluem múltiplas versões, marketplaces, cópias e templates; não devem ser somados como skills únicas. As raízes ECC abaixo já estão incluídas no total do cache Codex.

A sessão expôs explicitamente skills do catálogo de sistema, de raízes pessoais, ECC e plugins OpenAI. Há arquivos locais, como as skills Graphify, que não constavam da lista inicial exposta. Para usar qualquer skill, ler seu arquivo e verificar os requisitos no contexto da tarefa. Não instalar ou ativar todos os itens por padrão.

## Seleção pertinente à fundação

| Necessidade | Candidatos presentes |
|---|---|
| Descoberta de código e ambiente | `codebase-onboarding`, `repo-scan`, `workspace-surface-audit` (ECC) |
| Decisões e contratos de arquitetura | `architecture-decision-records`, `agent-architecture-audit`, `contract-first` (ECC) |
| Harness e continuidade | `agent-harness-construction`, `autonomous-agent-harness`, `context-budget`, `unified-memory` (ECC); `para-memory-files` (pessoal) |
| Avaliação e custo | `agent-eval`, `benchmark-methodology`, `eval-harness`, `cost-aware-llm-pipeline`, `cost-tracking` (ECC) |
| Futuro desenvolvimento/testes | `python-testing`, `verification-loop`, `security-review`, `mcp-server-patterns` (ECC) |
| Grafo do projeto | `graphify` (arquivos pessoais Codex e Claude) |

A tabela indica pertinência por disponibilidade e finalidade nominal; não afirma que todas essas skills foram aplicadas ou auditadas integralmente nesta missão. Regras do projeto e decisões explícitas do Founder prevalecem. Não copiar workflows específicos de uma IA para o runtime do produto.

## Skills pessoais e de sistema Codex

Raiz: `C:\Users\renan\.codex\skills`.

Arquivos encontrados: **29**.

```text
.system/imagegen
.system/openai-docs
.system/plugin-creator
.system/review-agent
.system/skill-creator
.system/skill-installer
calcom-api
changelog
cleanup
code-review
create-app
design-motion-principles
develop-app
docstring
graphify
instagram-carousel
manage-app
paperclip
paperclip-board
paperclip-converting-plans-to-tasks
paperclip-create-agent
para-memory-files
pr-description
pr-submit
prose-review
publish-app
update-docs
use-twenty-mcp
vercel-react-best-practices
```

## Skills compartilhadas de agentes

Raiz: `C:\Users\renan\.agents\skills`.

Arquivos encontrados: **11**.

```text
computer-use
find-skills
higgsfield-generate
microsoft-foundry
microsoft-foundry/finetuning
microsoft-foundry/models/deploy-model
microsoft-foundry/models/deploy-model/capacity
microsoft-foundry/models/deploy-model/customize
microsoft-foundry/models/deploy-model/preset
orca-cli
orchestration
```

## Skills pessoais Claude

Raiz: `C:\Users\renan\.claude\skills`.

Arquivos encontrados: **26**.

```text
brand-guidelines
canvas-design
docx
frontend-design
graphify
langflow/.agents/skills/backend-code-review
langflow/.agents/skills/component-refactoring
langflow/.agents/skills/e2e-testing
langflow/.agents/skills/frontend-code-review
langflow/.agents/skills/frontend-i18n
langflow/.agents/skills/frontend-query-mutation
langflow/.agents/skills/frontend-testing
langflow/.agents/skills/ibm-a11y-level1-audit
langflow/.agents/skills/ibm-a11y-pr-remediation
langflow/.agents/skills/ibm-a11y-route-scan
langflow/.agents/skills/ibm-a11y-testing-guide
mcp-builder
open-saas/template/app/.agents/skills/add-wasp-skills
open-saas/template/app/.agents/skills/getting-started
open-saas/template/app/.agents/skills/guided-tour
pdf
ponytail
pptx
web-artifacts-builder
webapp-testing
xlsx
```

## ECC 2.2.2 — skills

Raiz: `C:\Users\renan\.codex\plugins\cache\ecc\ecc\2.2.2\skills`.

Arquivos encontrados: **293**.

```text
accessibility
agent-architecture-audit
agent-eval
agent-harness-construction
agent-introspection-debugging
agent-payment-x402
agent-self-evaluation
agent-sort
agentic-engineering
agentic-os
ai-first-engineering
ai-regression-testing
android-clean-architecture
angular-developer
api-connector-builder
api-design
architecture-decision-records
article-writing
automation-audit-ops
autonomous-agent-harness
autonomous-loops
backend-patterns
benchmark
benchmark-methodology
benchmark-optimization-loop
blender-motion-state-inspection
blueprint
brand-discovery
brand-voice
browser-qa
bun-runtime
canary-watch
carrier-relationship-management
cisco-ios-patterns
ck
claude-devfleet
click-path-audit
clickhouse-io
code-tour
codebase-onboarding
codehealth-mcp
coding-standards
competitive-platform-analysis
competitive-report-structure
compose-multiplatform-patterns
config-gc
configure-ecc
connections-optimizer
content-engine
content-hash-cache-pattern
context-budget
continuous-agent-loop
continuous-learning
continuous-learning-v2
contract-first
cost-aware-llm-pipeline
cost-tracking
council
council-multi-model
counterparty-channel-discipline
cpp-coding-standards
cpp-testing
crosspost
csharp-testing
customer-billing-ops
customs-trade-compliance
dart-flutter-patterns
dashboard-builder
data-scraper-agent
data-throughput-accelerator
database-migrations
deep-research
defi-amm-security
delivery-gate
deployment-patterns
design-system
dev-team
django-celery
django-patterns
django-security
django-tdd
django-verification
dmux-workflows
docker-patterns
documentation-lookup
dotnet-patterns
dynamic-workflow-mode
e2e-testing
ecc-guide
ecc-recipes
ecc-tools-cost-audit
email-ops
energy-procurement
enterprise-agent-ops
error-handling
esign-field-placement
eval-harness
evm-token-decimals
exa-search
fal-ai-media
fastapi-patterns
finance-billing-ops
flox-environments
flutter-dart-code-review
foundation-models-on-device
frontend-a11y
frontend-design-direction
frontend-patterns
frontend-slides
fsharp-testing
gan-style-harness
gateguard
generating-python-installer
git-workflow
github-ops
golang-patterns
golang-testing
google-workspace-ops
growth-log
healthcare-cdss-patterns
healthcare-emr-patterns
healthcare-eval-harness
healthcare-phi-compliance
hermes-imports
hexagonal-architecture
hipaa-compliance
homelab-network-readiness
homelab-network-setup
homelab-pihole-dns
homelab-vlan-segmentation
homelab-wireguard-vpn
hookify-rules
i18n-sync
inherit-legacy-style
intent-driven-development
inventory-demand-planning
investor-materials
investor-outreach
ios-icon-gen
iterative-retrieval
ito-baskets
ito-compute
ito-inference
ito-training
java-coding-standards
jira-integration
jpa-patterns
knowledge-ops
kotlin-coroutines-flows
kotlin-exposed-patterns
kotlin-ktor-patterns
kotlin-patterns
kotlin-testing
kubernetes-patterns
laravel-patterns
laravel-plugin-discovery
laravel-security
laravel-tdd
laravel-verification
latency-critical-systems
lead-intelligence
liquid-glass-design
living-docs-governance
llm-trading-agent-security
logistics-exception-management
loop-design-check
mailtrap-email-integration
make-interfaces-feel-better
manim-video
market-research
marketing-campaign
master-agreement-generator
mcp-server-patterns
messages-ops
ml-adoption-playbook
mle-workflow
motion-advanced
motion-foundations
motion-patterns
mysql-patterns
nanoclaw-repl
nasiko-control-plane
nestjs-patterns
netmiko-ssh-automation
network-bgp-diagnostics
network-config-validation
network-interface-health
nextjs-turbopack
nodejs-keccak256
nutrient-document-processing
nuxt4-patterns
openclaw-persona-forge
opensource-pipeline
operator-approval-loop
orch-add-feature
orch-build-mvp
orch-change-feature
orch-fix-defect
orch-pipeline
orch-refine-code
parallel-execution-optimizer
perl-patterns
perl-security
perl-testing
plan-canvas
plan-orchestrate
plankton-code-quality
postgres-patterns
prediction-market-oracle-research
prediction-market-risk-review
prisma-patterns
product-capability
product-lens
production-audit
production-scheduling
project-flow-ops
prompt-optimizer
python-patterns
python-testing
pytorch-patterns
quality-nonconformance
quarkus-patterns
quarkus-security
quarkus-tdd
quarkus-verification
rails-patterns
ralphinho-rfc-pipeline
react-native-patterns
react-patterns
react-performance
react-testing
recsys-pipeline-architect
recursive-decision-ledger
redis-patterns
regex-vs-llm-structured-text
remotion-video-creation
repo-scan
research-ops
returns-reverse-logistics
rules-distill
rust-patterns
rust-testing
safety-guard
santa-method
scientific-db-pubmed-database
scientific-db-uspto-database
scientific-pkg-gget
scientific-thinking-literature-review
scientific-thinking-scholar-evaluation
search-first
security-bounty-hunter
security-review
security-scan
seo
skill-comply
skill-scout
skill-stocktake
social-graph-ranker
social-publisher
springboot-patterns
springboot-security
springboot-tdd
springboot-verification
strategic-compact
swift-actor-persistence
swift-concurrency-6-2
swift-protocol-di-testing
swiftui-patterns
taste
taste-application
taste-distillation
tasteforge-video
tdd-workflow
team-agent-orchestration
team-builder
terminal-opener
terminal-ops
tinystruct-patterns
token-budget-advisor
ui-demo
ui-to-vue
uncloud
unified-memory
unified-notifications-ops
verification-loop
video-editing
videodb
visa-doc-translate
vite-patterns
vue-patterns
windows-desktop-e2e
workspace-surface-audit
x-api
```

## ECC 2.2.2 — comandos migrados

Raiz: `C:\Users\renan\.codex\plugins\cache\ecc\ecc\2.2.2\.codex-plugin\migrated-command-skills`.

Arquivos encontrados: **35**.

```text
source-command-auto-update
source-command-build-fix
source-command-cpp-review
source-command-ecc-guide
source-command-epic-claim
source-command-epic-decompose
source-command-epic-publish
source-command-epic-review
source-command-epic-sync
source-command-epic-unblock
source-command-epic-validate
source-command-fastapi-review
source-command-feature-dev
source-command-go-build
source-command-go-review
source-command-gradle-build
source-command-hookify
source-command-hookify-configure
source-command-hookify-help
source-command-hookify-list
source-command-instinct-export
source-command-instinct-import
source-command-instinct-status
source-command-jira
source-command-learn
source-command-plan-canvas
source-command-projects
source-command-promote
source-command-prune
source-command-refactor-clean
source-command-review-pr
source-command-setup-pm
source-command-test-coverage
source-command-update-codemaps
source-command-update-docs
```

## Manutenção

Revalidar as raízes e versões quando uma capacidade for necessária. Não usar estes caminhos absolutos como requisitos de execução do FutureOS. Uma IA em outra máquina deve conseguir retomar pelo `README.md`, `AGENTS.md` e documentos de estado sem acesso a nenhuma destas skills. A lista não inclui segredos nem conteúdo de configurações pessoais.
