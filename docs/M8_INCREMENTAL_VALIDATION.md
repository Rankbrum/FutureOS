# M8 Incremental Validation

Implementado: validate_transition() em futureos/validation.py
Removido: deepcopy(rows) em audit_runs.py (lista rasa)
Testes: test_m8_aliasing, test_m8_debug_parity, test_m8_differential, test_m8_branch_safety
Full validation preservada: validate_simulation() intacta
Hash v1 preservado; nenhuma mudanca comportamental
Baseline M6.1: 164 pass; M8 valida diferencial declarada
