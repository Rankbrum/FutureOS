# M19 — Demo Script (2–4 min)

Estado: M18 concluído com limitações reais documentadas. Engine intacto. Nenhuma arquitetura nova.

Demo padrão: pequenos restaurantes avaliando solução de automação; pricing 70 → 100.

## 1. Problema (20s)
"Decisões sobre automação são tomadas depois do impacto. FutureOS cria sociedades sintéticas e permite comparar intervenções antes da decisão real."
Aviso de transparência: população sintética, modelo não calibrado, não representa probabilidade real.

## 2. População (20s)
- PopulationSpec carregada. Warnings: SYNTHETIC_POPULATION / UNCALIBRATED.
- 8 agentes sintéticos, relações definidas (seed 2026).

## 3. Cenário (20s)
- ScenarioSpec: pricing 70 → 100. Branches A / B / C.

## 4. Branches (30s)
- A: manter 70. B: subir para 100. C: manter 70 + incentivo.

## 5. Simulação (30s)
- Experimento pareado. Nenhuma previsão real — comparação de cenários simulados.

## 6. Comparação (30s)
- Aggregate A vs B vs C. Diferença visível; replay possível (seed fixa).

## 7. Scientist (20s)
- Scientist Analysis separado. Limitações explicitadas. Sem afirmação de certeza.

## 8. Limitações (15s)
- População sintética; não calibrado. Dados reais/calibração são extensões futuras (característica de transparência).

## 9. Encerramento (15s)
- "Explorar cenários, comparar intervenções, observar sensibilidade."
- Próximo: validação visual quando ambiente permitir.

Duração alvo: ~3 min. Fallback: outputs previamente verificados.

## Arquitetura Visual (Fase 13)
Human Decision
↓
PopulationSpec → ScenarioSpec → Experiment Runner → Branch Reality → Aggregate → Scientist → Human Review

Limitações (Fase 14): população sintética; modelo não calibrado; não probabilidade real; calibração futura.
