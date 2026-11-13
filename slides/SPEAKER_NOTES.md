# Speaker notes: Cryptographers, 10 minutes

This is the same text as the notes under each slide in `Cryptographers.pptx`. It is written to be spoken aloud, in full sentences. Read it out loud a few times, then change any sentence that does not sound like you.

Total: 1526 words. That is about 11.7 minutes at a calm 130 words per minute, and about 10.5 minutes at a normal 145.

If time runs short, slides 12 and 13 can each be cut to their first three sentences.

## Slide 1: Ten locks, one message

_61 words, about 28 seconds_

Good evening, everyone. We are team Cryptographers: Logan, Zach, Bryce, and me, Avaneesh. Our challenge was called Ten Locks, One Message. We were given ten locked files, and our job was to open every one of them with a quantum computer. In the next ten minutes, I will show you what we did, how we did it, and why it matters.

## Slide 2: The challenge: ten locked files, and a quantum circuit must find each key

_82 words, about 38 seconds_

Let me start with the problem. Each file was scrambled with encryption, so it looked like random nonsense. To unscramble a file, you need its key, and the key is just a secret number. The challenge was to build a quantum circuit that finds that number for us. Once we have the key, an ordinary computer unscrambles the file, and a readable sentence appears. Each lock was designed for a different quantum algorithm, and the locks get harder from one to ten.

## Slide 3: We opened all ten locks, and together they spell one message

_78 words, about 36 seconds_

Here is the result. We opened all ten locks. Each file gave us one line, and together the ten lines are secret directions around the Ohio State campus. The official checker confirmed that all ten lines are correct, and that every key really came from a quantum circuit. That gave us all forty points for solving the locks. We also ran one of our circuits on a real IBM quantum computer, and I will come back to that.

## Slide 4: The one idea behind every lock: make the wrong answers cancel

_101 words, about 47 seconds_

Before the locks, here is the one idea you need. A normal computer tests one key at a time. A quantum computer can hold all the possible keys at the same moment. But there is a catch: when you measure, you get only one answer back. So the real skill is to build the circuit so that the wrong answers cancel each other, like waves in water, and the right answer grows stronger. Every algorithm tonight is a different way of doing that. And although there are ten locks, there are only six ideas, because some locks share the same trick.

## Slide 5: Locks 1 and 3: in the query model, one quantum question replaces many

_131 words, about 60 seconds_

Locks one and three belong to the query model. The lock is a black box, and we count how many questions we must ask it. Lock one hides a code of twenty-four zeros and ones. A normal computer needs twenty-four questions, one for each digit. Our circuit asks one question about every input at once. The trick is called phase kickback: we put one extra qubit in a special state, and then the lock writes its answer as plus and minus signs. A second layer of H gates makes the wrong answers cancel, and the whole code appears. That is the Bernstein-Vazirani algorithm. Lock three uses its older relative, Deutsch-Jozsa. Each of twenty-four boxes is either constant or balanced, and one question tells us which. A normal computer may need thirty-three.

**If a judge asks, "What is phase kickback?"** The lock writes its answer as a plus or minus sign on the input, instead of writing it onto a separate qubit. This happens because the target qubit is in the state minus. Signs can cancel each other, and the last step of the circuit uses exactly that.

**If a judge asks, "What does the formula say?"** It describes a layer of H gates. An input x becomes an equal mix of all outputs y, and each y carries a plus or minus sign that depends on x · y. When many inputs are mixed, these signs decide which outputs add up and which cancel.

**If a judge asks, "What do constant and balanced mean?"** A constant box gives the same answer for all 64 inputs. A balanced box gives 0 for exactly half of them and 1 for the other half. The challenge promises that every box is one of the two.

## Slide 6: Lock 2: BB84 key distribution, where a spy cannot listen without leaving errors

_130 words, about 60 seconds_

Lock two is different, because here quantum physics protects a secret instead of breaking one. The method is called BB84. Alice sends a key, one qubit at a time, and for every bit she picks one of two bases at random, Z or X. In this lock, we are Bob. We also pick a random basis for every qubit, and we measure. Afterwards Alice tells us her bases, and we keep only the bits where our choices matched. Eve, the spy, has to guess the basis too, and a wrong guess changes the qubit. That shows up as errors. On line A we found zero errors. On line B, about one in five test bits was wrong. So line B was tapped, and we built the key from line A.

**If a judge asks, "Why 21% and not 25%?"** The theory says 25% on average. We tested only 125 bits, so the measured number moves a little by chance. We found 26 wrong out of 125, which is 21%.

**If a judge asks, "Where does 25% come from?"** Eve picks the wrong basis half of the time. When she does, our result is random, so it is wrong half of the time. Half of a half is a quarter.

**If a judge asks, "Why can Eve not simply copy the qubit?"** The no-cloning theorem says that an unknown quantum state cannot be copied. Eve has to measure it, and measuring in the wrong basis changes it.

## Slide 7: Lock 4: the same circuit shape with a catch, because each run gives only a clue

_125 words, about 58 seconds_

Lock four looks like the same circuit, but with a catch. This is Simon's problem. The lock hides a secret pattern, s, of ten zeros and ones, and two inputs give the same output exactly when they differ by s. This time there is no phase kickback, so one run gives us only a clue. Think of a detective: each new clue rules out half of the remaining suspects. We ran the circuit forty times, and ordinary algebra combined the clues into one answer. About eleven runs are enough. A normal computer has to find two inputs with the same output, which takes about forty tries. That is the birthday paradox, and the chart shows how quickly the gap grows as the secret gets longer.

**If a judge asks, "What does y · s = 0 mean?"** Write y above s. Look only at the positions where both have a 1, and count them. For every clue, that count is an even number.

**If a judge asks, "What is the birthday paradox?"** In a room of only 23 people, two of them probably share a birthday. In the same way, two inputs with the same output turn up after roughly the square root of the number of inputs. For n digits that is about 1.25 × 2^(n/2) tries, which is 40 for 10 digits.

**If a judge asks, "Why is there no phase kickback here?"** Phase kickback needs a target qubit in the state minus. Here the output qubits start at zero, so the lock stores f(x) as a value next to x. The cancelling happens between the two inputs that share that value, x and x ⊕ s.

## Slide 8: Locks 5 and 6: finding one key among 1,024 in 25 steps

_118 words, about 54 seconds_

Locks five and six are a search, like looking for a needle in a haystack. Lock five has about a thousand possible keys. A normal computer tries them one by one, so on average it needs about five hundred tries. Grover's algorithm needs twenty-five steps. Each step makes the right key a little more likely. In the plot, the line is the theory, and the dots are our results. After twenty-five steps we find the key every time. But if we keep going, the chance drops again, so we have to stop at the right moment. In lock six, sixty-four keys look correct at first. Grover finds all sixty-four, and then a quick check keeps the real one.

**If a judge asks, "Why do more steps make it worse?"** Each step turns the state by a fixed angle towards the right key. After 25 steps it points straight at the key. More steps turn it past the key.

## Slide 9: Lock 7: reading a hidden angle one digit at a time, with only 2 qubits

_115 words, about 53 seconds_

Lock seven hides its key as an angle, like the position of a hand on a clock. The key is that angle, written with fourteen zeros and ones. The textbook method needs fifteen qubits to read it. We read it with only two. One helper qubit reads the last digit. Then we use the same helper again for the next digit, fourteen times in total. Each time, we first subtract the digits we already know, so every answer is a clear zero or a clear one. This matters because today's quantum computers make small mistakes. Our version uses two of the most error-prone operations in each circuit. The textbook version uses two hundred and thirty.

**If a judge asks, "What is a two-qubit gate, and why count it?"** It is an operation that makes two qubits interact. On today's machines it fails much more often than an operation on a single qubit, so a circuit with fewer of them gives cleaner results.

## Slide 10: Locks 8, 9 and 10: breaking RSA by finding a repeating pattern

_126 words, about 58 seconds_

The last three locks are the famous ones, because they attack RSA, the encryption that protects the internet. RSA is safe only because it is very hard to split a huge number into the two smaller numbers that multiply to make it. Shor's algorithm turns that into a different problem: finding a repeating pattern. Look at the row of numbers. We keep doubling, and we keep only the remainder after dividing by thirty-five. After twelve steps, the numbers start again. A quantum computer is very good at spotting that kind of rhythm. Once we know the twelve, simple arithmetic gives us thirty-five equals five times seven. Lock nine splits seventy-seven in the same way, and lock ten uses the same idea to uncover a shared secret.

**If a judge asks, "How does 12 give the factors?"** Half of 12 is 6. Two to the power 6 is 64, and 64 leaves 29 after dividing by 35. The neighbours of 29 are 28 and 30. 28 shares the factor 7 with 35, and 30 shares the factor 5.

## Slide 11: We ran lock 7 on a real IBM quantum computer, and all 14 digits were correct

_111 words, about 51 seconds_

Everything so far ran on a simulator, which is a normal computer pretending to be a quantum one. So we also ran lock seven on a real machine: an IBM quantum computer called Kingston. All fourteen digits of the key came out correct. Each bar in the chart is one digit of the key. A bar at one hundred percent would be a perfect signal with no noise. Our average is ninety-seven percent. It worked this well because the circuit is tiny. One honest note: for the real machine we changed how the digits are read out, so that everything could run as one job. The quantum part is the same.

**If a judge asks, "What is signal strength?"** The write-up calls it contrast. It measures how clearly the qubit points in the expected direction. 100% is a perfect signal and 0% is pure noise. Each value is estimated from 1,024 runs, so a value can land slightly above 100% by chance.

## Slide 12: Today a laptop still wins, so what matters is how the work grows

_109 words, about 50 seconds_

Now let me be honest. At these small sizes, a laptop beats our quantum circuits easily. A laptop opens lock five in ten milliseconds, while simulating our circuit takes two and a half seconds. What matters is how the work grows when the key gets longer. Every extra bit doubles the work for a normal computer. For Grover, the work doubles only after two extra bits. For Shor the gap is even bigger, and that is why RSA is the one people worry about. One more honest point: our Shor circuits use a shortcut that works only for small numbers, so a real attack needs a much bigger circuit.

**If a judge asks, "What is the shortcut in the Shor circuits?"** The multiplication step is built from a list of all its answers, which we work out beforehand on a normal computer. That list is as long as the number we are factoring, so it is impossible for a real key. A real attack builds the multiplication from adder circuits instead.

## Slide 13: Why real encryption is still safe today: noise

_99 words, about 46 seconds_

And here is the reason nobody can break real encryption yet: noise. Every operation on a real quantum computer has a small chance of going wrong. We tested this in simulation with one error in every thousand operations, which is roughly where today's machines are. Lock seven, with two operations, always works. But lock five has almost five thousand operations, and it finds the key only five times in a hundred. Our circuit for seventy-seven has twenty-four thousand, so it would suffer about twenty-four errors in every run. Long circuits need error correction, and that is still being built.

**If a judge asks, "Did you use error mitigation?"** No. We measured how the plain circuits behave under noise, and we say so in the write-up.

## Slide 14: What difference does this make?

_111 words, about 51 seconds_

So what difference does this make? First, we showed that these attacks really work from start to finish. Every key came out of a quantum circuit, and one came out of a real machine. Second, we showed that small circuits are what today's machines can actually run. Third, the warning is real. In 2019, experts estimated that breaking real RSA would need twenty million qubits. In 2025, that estimate dropped below one million. So the world is already moving to new encryption that is designed to resist quantum computers. To sum up: we opened all ten locks. The algorithms are ready. The machines are not ready yet, but they are coming.

**If a judge asks, "Where do the RSA numbers come from?"** Gidney and Ekerå, 2019: about 20 million noisy qubits for 8 hours. Gidney, 2025: under one million noisy qubits in under a week. The new quantum-safe standards are NIST FIPS 203, 204 and 205, published in August 2024.

## Slide 15: Thank you

_29 words, about 13 seconds_

Thank you for listening. Our thanks also go to the Qiskit YouTube channel and IBM Quantum Learning, where we learned these algorithms. I am happy to take your questions.

## Backup slides

Slide 16 is the table of circuit costs from the official checker. Slides 17 to 26 hold one page for each lock, with its circuit, its measured result and its numbers. Jump to them if a judge asks about one lock in detail.
