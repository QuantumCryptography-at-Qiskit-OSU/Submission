# Benchmarks: every method we tried, per tier

Merged from `tierNN/benchmark.json`. Tiers 2, 3 and 9 have their comparisons in `tierNN/EXPLAINED.md`.

## Tier 1

Answer: `QC-01: Meet at the Oval when the clock reads 6:47`

| Method | Kind | Success | Queries / oracle calls | Wall s | Qubits | 2Q gates | Depth | Noisy success |
|---|---|---|---|---|---|---|---|---|
| A. classical, one bit per question | classical | 1.0 | 24 | 0.098 | 25 | 312 | - | - |
| B. classical, random questions + elimination | classical | 1.0 | 25.7 | - | 25 | - | - | - |
| C. classical brute force over all s | classical | 1.0 | 32 | 9.2 | 0 | 0 | 0 | - |
| D. Bernstein-Vazirani | quantum | 1.0 | 1 | 0.047 | 25 | 13 | 17 | cx_error_0.0: 1.0, cx_error_0.001: 0.96, cx_error_0.005: 0.94, cx_error_0.01: 0.87, cx_error_0.02: 0.77, cx_error_0.05: 0.6, cx_error_0.1: 0.3 |
| D2. Bernstein-Vazirani on the REAL oracle (solution.py) | quantum | 1.0 | 1 | - | 25 | 143 | 44 | cx_error_0.0: 1.0, cx_error_0.001: 0.86, cx_error_0.005: 0.5, cx_error_0.01: 0.28, cx_error_0.02: 0.12 |

## Tier 4

Answer: `QC-04: Brutus will whistle Carmen Ohio slightly off-key`

| Method | Kind | Success | Queries / oracle calls | Wall s | Qubits | 2Q gates | Depth | Noisy success |
|---|---|---|---|---|---|---|---|---|
| Classical brute force (ask all 1024 inputs) | classical | 1.0 | 1024 | 8.038 | 20 | 183 | 193 | - |
| Classical birthday search (random order) | classical | 1.0 | 40.1 | 0.765 | 20 | 183 | 193 | - |
| Simon + GF(2) elimination (submitted) | quantum | 1.0 | 10.7 | 0.27 | 20 | 183 | 195 | 0.0: 1.0, 0.0001: 0.0, 0.001: 0.0, 0.003: 0.0, 0.01: 0.0, 0.03: 0.0, 0.1: 0.0 |
| Simon + majority vote | quantum | 1.0 | 200 | 0.208 | 20 | 183 | 195 | 0.0: 1.0, 0.0001: 1.0, 0.001: 1.0, 0.003: 1.0, 0.01: 1.0, 0.03: 1.0, 0.1: 0.0 |
| Simon, output measured first | quantum | 1.0 | 60 | 0.498 | 20 | 183 | 196 | - |
| Grover search for s (f(x) = f(0), two marked states) | quantum | 1.0 | 35 | 12.291 | 20 | 7310 | 12095 | - |

## Tier 5

Answer: `QC-05: count the lamps on the Long Walk: there are nineteen`

| Method | Kind | Success | Queries / oracle calls | Wall s | Qubits | 2Q gates | Depth | Noisy success |
|---|---|---|---|---|---|---|---|---|
| Classical brute force, all keys | classical | 1.0 | 1024 | 0.010066888000437757 | - | - | - | - |
| Classical, stop at first hit | classical | 1.0 | 264 | 0.0029293669995240634 | - | - | - | - |
| Grover, 25 rounds (submitted) | quantum | 1.0 | 25 | 2.46 | 19 | 4750 | 4960 | cx_error: {'1e-05': 0.975, '0.0001': 0.7, '0.001': 0.05} |
| Grover, oracle: simplified, plain Toffoli | quantum | 1.0 | 25 | - | 19 | 6250 | 6112 | - |
| Grover, oracle: raw equations, RCCX | quantum | 1.0 | 25 | - | 21 | 6950 | 9531 | - |
| Grover, BBHT randomised rounds | quantum | 1.0 | 51 | - | 19 | - | - | - |

## Tier 6

Answer: `QC-06: the Thompson Library elevator stops twice on floor 8`

| Method | Kind | Success | Queries / oracle calls | Wall s | Qubits | 2Q gates | Depth | Noisy success |
|---|---|---|---|---|---|---|---|---|
| Classical brute force, full decrypt of every key | classical | 1.0 | 16384 | 8.151682228000027 | - | - | - | - |
| Classical brute force, staged (byte 0 first) | classical | 1.0 | 16384 | 0.10736733100020501 | - | - | - | - |
| Classical, stop at first full match | classical | 1.0 | 5402 | 0.044636569999966014 | - | - | - | - |
| Grover, 12 rounds, M = 64 (submitted) | quantum | 0.99975 | 12 | 0.22 | 16 | 2064 | 2826 | cx_error: {'1e-05': 0.97, '0.0001': 0.9, '0.001': 0.14} |
| Grover, BBHT randomised rounds (M unknown) | quantum | 1.0 | 27 | - | 16 | - | - | - |
| Grover, oracle: 1 byte, plain Toffoli | quantum | 0.9996666666666667 | 12 | - | 16 | 2592 | 3570 | - |
| Grover, oracle: trust 2 bytes 'QC' | quantum | 1.0 | 71 | - | 21 | 16472 | 17198 | - |

## Tier 7

Answer: `QC-07: ask the night librarian for Folio 1870-Q, not 1870-R`

| Method | Kind | Success | Queries / oracle calls | Wall s | Qubits | 2Q gates | Depth | Noisy success |
|---|---|---|---|---|---|---|---|---|
| A. classical brute force over keys | classical | 1.0 | 16384 | 0.17 | 0 | 0 | 0 | - |
| B. classical angle scan vs matrix of U | classical | 1.0 | 16384 | 0.016 | 0 | 0 | 0 | - |
| C. repeated Hadamard test (1 use of U per shot) | classical | 0.2 | 2000000 | 25.3 | 2 | 2 | 17 | - |
| D. textbook QPE, 14 counting qubits + inverse QFT | quantum | 1.0 | 16383 | 1.934 | 15 | 230 | 269 | 0: 1.0, 0.0001: 0.9733333333333334, 0.001: 0.8366666666666667, 0.01: 0.17, 0.03: 0.006666666666666667 |
| D. textbook QPE, t=4 (too few bits) | quantum | 0.0 | 15 | 0.077 | 5 | 26 | 79 | - |
| D. textbook QPE, t=8 (too few bits) | quantum | 0.0 | 255 | 0.073 | 9 | 84 | 159 | - |
| D. textbook QPE, t=12 (too few bits) | quantum | 0.0 | 4095 | 0.076 | 13 | 174 | 239 | - |
| E. iterative (semiclassical) QPE, 2 qubits [submitted] | quantum | 1.0 | 16383 | 0.182 | 2 | 2 | 17 | 0: 1.0, 0.0001: 1.0, 0.001: 1.0, 0.01: 1.0, 0.03: 1.0 |

## Tier 8

Answer: `QC-08: inside is a map of old tunnels under Ohio Stadium`

| Method | Kind | Success | Queries / oracle calls | Wall s | Qubits | 2Q gates | Depth | Noisy success |
|---|---|---|---|---|---|---|---|---|
| classical trial division | classical | 1.0 | 4 | 2.424310000606056e-07 | 0 | 0 | 4 | - |
| classical Fermat | classical | 1.0 | 1 | 1.8384999998488639e-07 | 0 | 0 | 1 | - |
| classical Pollard rho | classical | 1.0 | 1 | 2.1201250001467997e-07 | 0 | 0 | 1 | - |
| Shor, recycled control (submitted) | quantum | 1.0 | 24 | 1.1684160232543945 | 9 | 5053 | 10425 | cx_error=0.0: 0.992, cx_error=0.0001: 0.996, cx_error=0.0003: 0.97, cx_error=0.001: 0.642 |
| Shor, textbook full register | quantum | 1.0 | 24 | 90.76163792610168 | 18 | 4966 | 10007 | - |
| Grover factoring | quantum | 0.964 | 3 | 0.7669568061828613 | 12 | 1776 | 2278 | cx_error=0.0: 0.9775, cx_error=0.0001: 0.83, cx_error=0.0003: 0.65, cx_error=0.001: 0.31 |

## Tier 10

Answer: `QC-10: knock four times, shout O-H, and wait for the I-O`

| Method | Kind | Success | Queries / oracle calls | Wall s | Qubits | 2Q gates | Depth | Noisy success |
|---|---|---|---|---|---|---|---|---|
| classical brute force | classical | 1.0 | 15 | 6.466739996540128e-07 | 0 | 0 | 15 | - |
| classical lookup table | classical | 1.0 | 41 | 1.15784640001948e-05 | 0 | 0 | 41 | - |
| classical baby-step giant-step | classical | 1.0 | 10 | 1.6453479993288056e-06 | 0 | 0 | 10 | - |
| classical Pollard rho | classical | 1.0 | 12 | 2.7264730000752025e-05 | 0 | 0 | 12 | - |
| Shor dlog, recycled control (submitted) | quantum | 1.0 | 40 | 3.8680949211120605 | 10 | 13157 | 26139 | cx_error=0.0: 1.0, cx_error=0.0001: 0.9525, cx_error=0.001: 0.0 |
| Shor dlog, textbook two registers | quantum | - | 40 | - | 23 | 13313 | 26178 | - |
| Grover over exponents | quantum | 0.9991823155419229 | 4 | 437.758846282959 | 15 | 49698 | 97786 | cx_error=0.0: 0.9991823155419229, cx_error=0.0001: 0.03115804126835243, cx_error=0.001: 0.024390243902439025 |
