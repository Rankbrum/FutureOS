# M11 — adapter mínimo usado por M13

Atualizado em 2026-10-01. Os arquivos iniciais eram stubs (classes vazias,
Registry.register sem efeito). Nesta missão foram implementados os contratos
necessários ao planner opcional, sem SDK/rede. **9 testes adapter passaram**.

`llm_provider.py`: LLMProvider.generate(LLMRequest) → LLMResponse;
LLMMessage(role,content), LLMRequest(messages,model,metadata,response_format),
LLMResponse(content,provider,model,usage), UsageMetadata(input_tokens,output_tokens),
ProviderError e LLMUnavailable. Texto da response é validado pelo recurso chamador.

FakeLLMProvider(response=None,error=None,model="fake-population-v1") aceita fixture
JSON/texto/response ou erro; guarda requests somente em memória. Para purpose
population_plan propõe archetype genérico com todos os traits0.5, assumptions e
warnings, tamanho solicitado ou100. Não interpreta o setor nem inventa fatos.

Registry registra/seleciona providers explicitamente e falha quando indisponível.
M13 usa esse adapter, prompt grounding e validação pelo contrato PopulationSpec.
Não há Claude/OpenAI/local funcional/configurado nesta entrega. Compatibilidade de
providers futuros depende de implementarem LLMProvider/LLMResponse; nenhuma chamada
real foi verificada. Não há claim de determinismo remoto.

O ScientistExplainer preexistente continua stub, fora do aceite desta missão.
O texto anterior alegava grounding/validação de relatórios e adapters reais em stub;
isso não é evidência de execução. No planner, requests/config/credenciais não entram
em spec; erros brutos são substituídos por diagnóstico seguro. Ver
[M13](M13_LLM_POPULATION_PLANNER.md) e D021–D023.
