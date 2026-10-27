# Eval results

Written by `redline eval`. Do not edit by hand.

## Detection

Model: claude-sonnet-5-5  
Date: 2026-10-27T08:36:06Z  
Command: `redline eval --detection contractnli --n 25`

ContractNLI test split, n = 25 documents. A rule should be flagged when the ContractNLI label is Contradiction, or NotMentioned for a required rule. Rates are k/n with a Wilson 95% interval.

| rule | hypothesis | precision | recall | F1 |
|---|---|---|---|---|
| ci-oral | nda-3 | 0/1 = 0.00 [0.00, 0.79] | 0/1 = 0.00 [0.00, 0.79] | 0.00 |
| disc-employees | nda-5 | 5/13 = 0.38 [0.18, 0.64] | 5/5 = 1.00 [0.57, 1.00] | 0.56 |
| disc-advisors | nda-7 | 3/10 = 0.30 [0.11, 0.60] | 3/4 = 0.75 [0.30, 0.95] | 0.43 |
| disc-legal | nda-8 | 9/19 = 0.47 [0.27, 0.68] | 9/13 = 0.69 [0.42, 0.87] | 0.56 |
| term-survival | nda-19 | 4/6 = 0.67 [0.30, 0.90] | 4/8 = 0.50 [0.22, 0.78] | 0.57 |
| ret-destroy | nda-16 | 19/22 = 0.86 [0.67, 0.95] | 19/20 = 0.95 [0.76, 0.99] | 0.90 |
| ret-retention | nda-20 | 21/22 = 0.95 [0.78, 0.99] | 21/21 = 1.00 [0.85, 1.00] | 0.98 |
| overall | | 61/93 = 0.66 [0.55, 0.74] | 61/72 = 0.85 [0.75, 0.91] | 0.74 |

Model calls: 25, input tokens: 174868, output tokens: 115769, mean latency: 32.2 s

## Edits

Model: claude-sonnet-5-5  
Date: 2026-10-27T08:47:43Z  
Command: `redline eval --edits eval/gold`

Gold files: 1. An edit matches when (paragraph_id, rule_id) agree. Rates are k/n with a Wilson 95% interval.

| metric | value |
|---|---|
| precision | 9/10 = 0.90 [0.60, 0.98] |
| recall | 9/9 = 1.00 [0.70, 1.00] |
| find F1: mean token F1 of the targeted wording, matched edits | 0.74 |
| replace F1: mean token F1 of the proposed wording, matched edits | 0.73 |

Model calls: 1, input tokens: 6193, output tokens: 4101, mean latency: 24.5 s
