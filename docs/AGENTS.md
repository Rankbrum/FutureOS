# Agentes do produto FutureOS

Data de referência: 2026-09-29. Status: **papéis e contratos propostos; não implementados**.

Este arquivo descreve agentes da sociedade simulada. O [AGENTS.md da raiz](../AGENTS.md) contém o protocolo para IAs que desenvolvem o projeto. As duas funções são distintas.

## Modelo compartilhado

Todo agente tem identidade, papel, atributos, estado, política de decisão, memória acessível e permissões explícitas. Agentes pertencem ao estado de uma execução; sua origem e sua população devem ser rastreáveis.

Um papel não implica uma chamada de LLM a cada tick, nem exige um framework próprio. O runtime em `packages/agents` executa regras e probabilidades e só solicita LLM quando a política identifica uma necessidade concreta. A ausência de provider deve permitir cenários integralmente baseados em regras.

Proposta de ciclo:

```text
observação permitida
  → política do papel
  → regra/probabilidade ou escalonamento seletivo para LLM
  → intenção estruturada
  → validação pelo runtime
  → aplicação pelo motor de simulação
  → evento e atualização de memória
```

Uma intenção não é um efeito confirmado. O motor resolve conflitos, valida permissões e determina o resultado. Saídas de LLM são dados externos sujeitos às mesmas verificações.

## Papéis iniciais

| Papel e diretório | Responsabilidade | Entradas e saídas | Limites |
| --- | --- | --- | --- |
| Citizen Agent — `agents/citizen` | Representar um participante da população, com comportamento condicionado a atributos e observações | Recebe observações permitidas; produz intenções de ação ou diálogo | Não presume racionalidade perfeita, representatividade ou acesso a todo o mundo |
| Influencer Agent — `agents/influencer` | Produzir ou propagar mensagens conforme um mecanismo de influência declarado | Recebe estado e relações permitidos; produz mensagens/intensões com alcance definido | Poder de influência, confiança e propagação são parâmetros e premissas, não fatos universais |
| Observer Agent — `agents/observer` | Observar acontecimentos e registrar sinais de interesse | Recebe eventos ou projeções autorizadas; produz registros e observações | Não altera silenciosamente a sociedade; observação invasiva precisa ser modelada como intervenção |
| Scientist Agent — `agents/scientist` | Auditar premissas, protocolo, execução, comparação e interpretação | Recebe manifestos, métricas e evidências autorizadas; produz achados e recomendações | Não certifica previsão e não modifica a execução auditada |

Citizen e Influencer podem participar do mundo simulado. Observer e Scientist cumprem funções de observação e auditoria; não é necessário inseri-los como cidadãos que afetam o mesmo mundo. Se uma futura experiência incluir um observador com influência, isso deverá ser uma escolha explícita do modelo.

## Memória, relações e observabilidade

Memórias devem registrar origem, tempo lógico e escopo de acesso. Relações precisam declarar participantes, direção ou simetria, significado e atributos. A semântica de confiança, por exemplo, não pode mudar entre cenários sem uma nova versão de política.

Agentes só enxergam o estado que a política lhes concede. Conhecimento global disponível para análise não deve vazar automaticamente para decisões individuais. O snapshot de uma sociedade preserva memórias, relações, suas permissões e todas as informações necessárias à retomada.

Memórias dos agentes são dados do produto. Não carregar automaticamente o Memory Core do desenvolvedor, histórico de conversas, arquivos pessoais, credenciais ou estado privado de Codex/Claude/Gemini.

## Skills comportamentais

Os diretórios `skills/*` existentes representam capacidades planejadas do produto:

| Diretório | Uso proposto |
| --- | --- |
| `skills/behavior` | Regras de comportamento observável |
| `skills/decision` | Políticas de seleção de ações e escalonamento para LLM |
| `skills/influence` | Mecanismos de alcance e propagação social |
| `skills/persuasion` | Respostas condicionais a mensagens, quando o cenário as modelar |
| `skills/trust` | Evolução e uso de confiança nas relações |
| `skills/validation` | Verificações de entrada, intenção e invariantes |

Essas capacidades não são automaticamente equivalentes às skills instaladas nas ferramentas de desenvolvimento. Não executar instruções locais como código de um agente só porque estão num arquivo chamado skill.

Cada mecanismo implementado deve declarar entradas, saídas, parâmetros, versão, necessidade de aleatoriedade, uso permitido de LLM e limitações conhecidas. Começar com um mecanismo pequeno na próxima missão; a árvore existente não obriga implementar todos simultaneamente.

## Permissões e ferramentas externas

O runtime concentra autorização, orçamento, validação e registro. Providers, MCPs e ferramentas são adaptadores substituíveis, não dependências de cada papel.

Na primeira implementação, agentes não executam ações fora da sociedade simulada. Uma futura integração deve distinguir consultar um dado externo de enviar mensagens, alterar arquivos, gastar dinheiro ou modificar sistemas reais. Nenhuma dessas capacidades surge implicitamente a partir de texto produzido por um agente.

Aplicar limites por execução, tick, agente e categoria quando LLM for integrado. Registrar fallback e falha porque eles alteram as condições efetivas da simulação. Ver [SIMULATION_ENGINE.md](SIMULATION_ENGINE.md).

## Scientist Agent

Começar por verificações programáticas reproduzíveis e um relatório estruturado. Uma etapa posterior pode usar LLM para interpretar evidências ou sugerir novos experimentos, mantendo rastreabilidade entre conclusão e observação.

Escopo planejado:

- **Premissas:** identificar parâmetros ausentes, mecanismos sem justificativa e diferenças entre configuração declarada e executada.
- **Viés:** examinar composição da população, cobertura de perfis, acesso a informação e mecanismos que favoreçam artificialmente um resultado.
- **Sensibilidade:** comparar resultados quando parâmetros ou seeds variam segundo um protocolo explícito.
- **Consistência:** verificar invariantes, unidades, métricas e compatibilidade entre execuções.
- **Artefatos:** procurar efeitos de ordenação, respostas repetidas, concentração artificial, fallbacks e comportamento incompatível com as regras.
- **Confiabilidade:** descrever quais conclusões são sustentadas, quais dependem de premissas frágeis e quais permanecem sem validação.

Relatório mínimo: pergunta do experimento, versões, premissas, origem da população, políticas, intervenções, seeds, métricas, custos, falhas, diferenças entre execuções, achados, evidências e limitações.

O Scientist não deve produzir um único número de confiança sem método definido. Concordância entre agentes LLM também não substitui validação externa. Frequências obtidas em cenários sintéticos permanecem condicionais ao modelo; não devem ser apresentadas como probabilidades garantidas de acontecimentos reais.

Uma recomendação do Scientist para mudar uma premissa cria uma nova configuração/execução ou uma intervenção registrada. O experimento anterior permanece auditável.

## Garantias a testar

1. Um agente não acessa memória fora de seu escopo.
2. Regras e probabilidades funcionam sem provider externo.
3. Solicitações de LLM respeitam elegibilidade, orçamento e validação.
4. Snapshot e branching preservam estado sem compartilhar objetos mutáveis entre universos.
5. Observer e Scientist não alteram o mundo por efeito colateral de uma leitura.
6. Relatórios identificam premissas, evidências e limites das conclusões.

Essas garantias serão implementadas por etapas; não representam testes já existentes ou aprovados.
