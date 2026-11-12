# Speaker notes: Cryptographers, 10 minutes

Same text as the notes under each slide in `Cryptographers.pptx`. Rewrite it in your own words before rehearsing.

Total: 1294 words, about 10.0 minutes at 130 words per minute.

## Slide 1: Ten locks, one message

_60 words, about 28 seconds_

Good evening. We are team Cryptographers. Ten files were locked. Each lock opens with a different quantum algorithm. In the next ten minutes I will show you how we opened all ten, what each circuit costs, and what happens at real key sizes. The model on the right is a quantum computer I built in 3D for my own website.

## Slide 2: We opened all ten locks, and each one ran a quantum circuit

_51 words, about 24 seconds_

Here is the message. Ten lines, one from each file. Every line matches the official hash, and every tier ran a quantum circuit inside solve. That is all forty tier points in the checker. We also ran one tier on a real IBM quantum computer. I will come back to that.

## Slide 3: Six ideas open ten locks: what each scored circuit costs

_61 words, about 28 seconds_

This table is every tier on one slide. The numbers come from the official checker. Ten tiers, but only six ideas. Tiers one and three are the same trick. Five and six are both Grover. Eight, nine and ten are all Shor. So I will explain six ideas. Look at tier seven: two qubits and two two-qubit gates. Remember that one.

## Slide 4: Tiers 1 and 3: one question answers what classical needs 24 or 33 for

_119 words, about 55 seconds_

Tiers one and three use the same trick. First, we put the target qubit in the minus state. Now the oracle does not flip a bit. It puts a plus or minus sign on the input. That is phase kickback. Second, Hadamard gates put all inputs into one question. One oracle call signs all of them. Third, Hadamards again, and the signs add up or cancel. In tier one the hidden twenty-four bit string appears directly. All sixteen shots agree. In tier three, a constant function always gives all zeros, and a balanced function never does. You see both cases in the histograms. Classically, tier one needs twenty-four questions and tier three needs up to thirty-three. We need one.

## Slide 5: Tier 2: the eavesdropper leaves 21% errors, the clean link leaves none

_107 words, about 49 seconds_

Tier two is BB84. Alice sends qubits in four possible states. You see them on the Bloch spheres. We measure each qubit in a random basis. Later Alice tells us her bases, and we keep only the matching ones. Now the important part. Eve measured one link. She had to guess the basis. Half the time she guessed wrong, and then half of our results flip. So we expect twenty-five percent errors. We measured zero on link A and twenty-one percent on link B. So link B is tapped. We build the key from link A. The security comes from physics. Measuring an unknown qubit changes it.

## Slide 6: Tier 4: every run returns one equation about the secret

_96 words, about 44 seconds_

Tier four is Simon's algorithm. The function repeats with a hidden shift s. We want s. Each run of the circuit gives a random string y. But not fully random. Every y satisfies y dot s equals zero. So each run is one equation about the secret. We took forty shots and got thirty-seven different strings. All of them satisfy the equation. Then ordinary linear algebra gives one answer for s. On average eleven runs are enough. A classical search needs about forty queries to find a collision, and this gap grows exponentially with the size.

## Slide 7: Tiers 5 and 6: Grover finds the key in 25 rounds, and more rounds make it worse

_117 words, about 54 seconds_

Tiers five and six are Grover search. The oracle marks the right key with a minus sign. Each round moves probability towards that key. Look at the left plot. The grey line is theory and the red dots are our measurements. At twenty-five rounds we find the key every time. But at fifty rounds the probability is back to zero. Grover is a rotation. If you rotate too far, you pass the answer. In tier six, sixty-four keys pass the test. So Grover needs only twelve rounds, and it returns all sixty-four. Then a classical checksum keeps one. We also made the oracle cheaper. Our version uses thirty-two percent fewer CNOT gates than a plain Toffoli build.

## Slide 8: Tier 7: we read a 14-bit angle with 2 qubits instead of 15

_116 words, about 54 seconds_

Tier seven hides a fourteen-bit angle inside a gate. The textbook method is phase estimation with fourteen control qubits. We use one control qubit and repeat it fourteen times. Each round reads one bit. We start with the lowest bit, because its phase is exactly zero or pi. So the result is certain. Then a phase gate removes the bits we already know, and we read the next one. The result is two qubits, and two two-qubit gates per circuit, against two hundred and thirty for the textbook version. This is why the checker shows a flag for a small number of qubits. The scoring rules say this recycling technique is allowed, if we explain it.

## Slide 9: Tiers 8, 9 and 10: breaking RSA means finding a period

_118 words, about 54 seconds_

Tiers eight, nine and ten are Shor's algorithm. The key idea: factoring becomes finding a period. Take powers of two, modulo thirty-five. They repeat with period twelve. The circuit measures a number y, and y is always near a multiple of one thousand twenty-four divided by twelve. You see the evenly spaced peaks. From the period, two greatest common divisors give the factors, seven and five. Tier nine is the same with N equals seventy-seven and period thirty. Tier ten is Diffie-Hellman. There we measure two phases, and each shot votes for the secret exponent. Fourteen wins with thirty-four of forty votes. Like tier seven, we reuse one control qubit, so tier nine needs ten qubits, not twenty-one.

## Slide 10: At these sizes classical wins, so the argument is about growth

_103 words, about 48 seconds_

Now the analysis. First, classical computers win at these sizes. A brute-force search of tier five takes ten milliseconds. Our simulated Grover takes two and a half seconds. So the argument is not speed today. It is growth. Double the key size, and classical work squares, while Grover's work only doubles. For Shor the gap is bigger: polynomial against sub-exponential. Second, some of our circuits are still toys. Our Shor multiplier is built from a table of all values. That table is more classical work than factoring seventy-seven by hand. A scalable version uses adder circuits. We say this clearly in our write-up.

## Slide 11: It ran on a real quantum computer: 14 of 14 bits correct on ibm_kingston

_113 words, about 52 seconds_

We ran tier seven on a real IBM quantum computer, ibm kingston. All fourteen bits came out correct, and the decrypted line matches the hash. On the left, each point is one key bit. The grey circle is the ideal result with no noise. Our points sit very close to it. The average contrast is zero point nine seven. One honest note. This is a variant of our scored circuit. The scored version feeds each bit into the next circuit, which means fourteen jobs in the queue. For hardware we read each round in two bases and do the correction in software. So it is one job. The quantum part is the same.

## Slide 12: Noise decides what survives: the gate count is the whole story

_114 words, about 53 seconds_

What about noise on the bigger circuits? We simulated every tier with an error after each two-qubit gate. At zero point one percent error, which is close to today's hardware, tier seven with two gates always works. Tier one with one hundred forty-three gates still works eighty-six percent of the time. Tier five with almost five thousand gates finds the key in only five percent of runs. The rule is simple. A circuit survives while error rate times gate count stays well below one. Our Shor circuit for seventy-seven has twenty-four thousand gates. That is about twenty-four errors per run. It needs error correction. We did not run error mitigation, and we say so.

## Slide 13: From toy locks to real keys: what would have to change

_119 words, about 55 seconds_

Last slide: what changes at real sizes. For RSA, we factored seventy-seven with ten qubits. RSA two thousand forty-eight needs thousands of error-corrected qubits and billions of gates. Published estimates went from twenty million noisy qubits in two thousand nineteen to under one million in two thousand twenty-five. For Grover, a one hundred twenty-eight bit key still needs two to the sixty-four rounds. Doubling the key length is enough defence. For BB84, real links have noise even without Eve, so they need error correction and a threshold. To close: we opened all ten locks. The algorithms are ready. The machines that can run them at real size are not here yet. Thank you. I am happy to take questions.
