# Phase 11 Guardrail Report

Generated: 2026-04-16T04:24:55.889975+00:00

## Snapshot
- Command: C:\Users\wikiepeidia\AppData\Local\Programs\Python\Python312\python.exe scripts/phase11_route_snapshot.py --out .planning/phases/11-baseline-contract-guardrails/11-endpoint-snapshot.json
- Status: PASS
- Exit Code: 0

### Stdout
```
Snapshot written: .planning/phases/11-baseline-contract-guardrails/11-endpoint-snapshot.json | total: 19 | found: 19 | missing_paths: 0 | method_mismatches: 0
```

### Stderr
```
(no output)
```

## Contract Tests
- Command: C:\Users\wikiepeidia\AppData\Local\Programs\Python\Python312\python.exe -m pytest tests/contracts -q
- Status: PASS
- Exit Code: 0

### Stdout
```
..........                                                               [100%]
```

### Stderr
```
(no output)
```

## Overall Gate
- Status: PASS
- Rule: Phase 12 extraction remains blocked unless Overall Gate is PASS.
