// Builds slides/Cryptographers.pptx and slides/SPEAKER_NOTES.md.
// Run:  NODE_PATH=<node_modules with pptxgenjs and sharp> node build_deck.js
// The plots in slides/figures/ come from make_figures.py.
const pptxgen = require("pptxgenjs");
const sharp = require("sharp");
const fs = require("fs");
const SKILL = "/home/avopti/.claude/skills/synced/a2ad65a7-7655-4bae-a49d-422dfad1841b_6001c603-3df1-4a5c-b446-eca2626d28bb/pptx";
const { applyTheme } = require(SKILL + "/scripts/apply_theme.js");

const SUB = "/home/avopti/Documents/QiskitFallFest2026/Submission";
const FIG = SUB + "/slides/figures/";
const OUT = SUB + "/slides/Cryptographers.pptx";
const NOTES_OUT = SUB + "/slides/SPEAKER_NOTES.md";

// Blue, pink and white, the colours Qiskit uses.
const NAVY = "001141", BLUE = "0F62FE", PINK = "D02670", GRID = "D0E2FF";
const THEME = {
  name: "Cryptographers",
  headFontFace: "Arial",
  bodyFontFace: "Calibri",
  colors: {
    dk1: NAVY, lt1: "FFFFFF", dk2: "001D6C", lt2: "EDF5FF",
    accent1: BLUE, accent2: PINK, accent3: "A6C8FF", accent4: "FF7EB6",
    accent5: "FFF0F7", accent6: "002D9C", hlink: BLUE, folHlink: PINK,
  },
};
const W = 13.333, H = 7.5, MX = 0.6;

// ---------- what I say on each slide ----------
// "ask" holds short answers for questions a judge may ask about that slide.
const TALK = [
  { title: "Ten locks, one message",
    say: "Good evening, everyone. We are team Cryptographers: Logan, Zach, Bryce, and me, Avaneesh. Our challenge was called Ten Locks, One Message. We were given ten locked files, and our job was to open every one of them with a quantum computer. In the next ten minutes, I will show you what we did, how we did it, and why it matters." },
  { title: "The challenge: ten locked files, and a quantum circuit must find each key",
    say: "Let me start with the problem. Each file was scrambled with encryption, so it looked like random nonsense. To unscramble a file, you need its key, and the key is just a secret number. The challenge was to build a quantum circuit that finds that number for us. Once we have the key, an ordinary computer unscrambles the file, and a readable sentence appears. Each lock was designed for a different quantum algorithm, and the locks get harder from one to ten." },
  { title: "We opened all ten locks, and together they spell one message",
    say: "Here is the result. We opened all ten locks. Each file gave us one line, and together the ten lines are secret directions around the Ohio State campus. The official checker confirmed that all ten lines are correct, and that every key really came from a quantum circuit. That gave us all forty points for solving the locks. We also ran one of our circuits on a real IBM quantum computer, and I will come back to that." },
  { title: "The one idea behind every lock: make the wrong answers cancel",
    say: "Before the locks, here is the one idea you need. A normal computer tests one key at a time. A quantum computer can hold all the possible keys at the same moment. But there is a catch: when you measure, you get only one answer back. So the real skill is to build the circuit so that the wrong answers cancel each other, like waves in water, and the right answer grows stronger. Every algorithm tonight is a different way of doing that. And although there are ten locks, there are only six ideas, because some locks share the same trick." },
  { title: "Locks 1 and 3: in the query model, one quantum question replaces many",
    say: "Locks one and three belong to the query model. The lock is a black box, and we count how many questions we must ask it. Lock one hides a code of twenty-four zeros and ones. A normal computer needs twenty-four questions, one for each digit. Our circuit asks one question about every input at once. The trick is called phase kickback: we put one extra qubit in a special state, and then the lock writes its answer as plus and minus signs. A second layer of H gates makes the wrong answers cancel, and the whole code appears. That is the Bernstein-Vazirani algorithm. Lock three uses its older relative, Deutsch-Jozsa. Each of twenty-four boxes is either constant or balanced, and one question tells us which. A normal computer may need thirty-three.",
    ask: [["What is phase kickback?", "The lock writes its answer as a plus or minus sign on the input, instead of writing it onto a separate qubit. This happens because the target qubit is in the state minus. Signs can cancel each other, and the last step of the circuit uses exactly that."],
          ["What does the formula say?", "It describes a layer of H gates. An input x becomes an equal mix of all outputs y, and each y carries a plus or minus sign that depends on x · y. When many inputs are mixed, these signs decide which outputs add up and which cancel."],
          ["What do constant and balanced mean?", "A constant box gives the same answer for all 64 inputs. A balanced box gives 0 for exactly half of them and 1 for the other half. The challenge promises that every box is one of the two."]] },
  { title: "Lock 2: BB84 key distribution, where a spy cannot listen without leaving errors",
    say: "Lock two is different, because here quantum physics protects a secret instead of breaking one. The method is called BB84. Alice sends a key, one qubit at a time, and for every bit she picks one of two bases at random, Z or X. In this lock, we are Bob. We also pick a random basis for every qubit, and we measure. Afterwards Alice tells us her bases, and we keep only the bits where our choices matched. Eve, the spy, has to guess the basis too, and a wrong guess changes the qubit. That shows up as errors. On line A we found zero errors. On line B, about one in five test bits was wrong. So line B was tapped, and we built the key from line A.",
    ask: [["Why 21% and not 25%?", "The theory says 25% on average. We tested only 125 bits, so the measured number moves a little by chance. We found 26 wrong out of 125, which is 21%."],
          ["Where does 25% come from?", "Eve picks the wrong basis half of the time. When she does, our result is random, so it is wrong half of the time. Half of a half is a quarter."],
          ["Why can Eve not simply copy the qubit?", "The no-cloning theorem says that an unknown quantum state cannot be copied. Eve has to measure it, and measuring in the wrong basis changes it."]] },
  { title: "Lock 4: the same circuit shape with a catch, because each run gives only a clue",
    say: "Lock four looks like the same circuit, but with a catch. This is Simon's problem. The lock hides a secret pattern, s, of ten zeros and ones, and two inputs give the same output exactly when they differ by s. This time there is no phase kickback, so one run gives us only a clue. Think of a detective: each new clue rules out half of the remaining suspects. We ran the circuit forty times, and ordinary algebra combined the clues into one answer. About eleven runs are enough. A normal computer has to find two inputs with the same output, which takes about forty tries. That is the birthday paradox, and the chart shows how quickly the gap grows as the secret gets longer.",
    ask: [["What does y · s = 0 mean?", "Write y above s. Look only at the positions where both have a 1, and count them. For every clue, that count is an even number."],
          ["What is the birthday paradox?", "In a room of only 23 people, two of them probably share a birthday. In the same way, two inputs with the same output turn up after roughly the square root of the number of inputs. For n digits that is about 1.25 × 2^(n/2) tries, which is 40 for 10 digits."],
          ["Why is there no phase kickback here?", "Phase kickback needs a target qubit in the state minus. Here the output qubits start at zero, so the lock stores f(x) as a value next to x. The cancelling happens between the two inputs that share that value, x and x ⊕ s."]] },
  { title: "Locks 5 and 6: finding one key among 1,024 in 25 steps",
    say: "Locks five and six are a search, like looking for a needle in a haystack. Lock five has about a thousand possible keys. A normal computer tries them one by one, so on average it needs about five hundred tries. Grover's algorithm needs twenty-five steps. Each step makes the right key a little more likely. In the plot, the line is the theory, and the dots are our results. After twenty-five steps we find the key every time. But if we keep going, the chance drops again, so we have to stop at the right moment. In lock six, sixty-four keys look correct at first. Grover finds all sixty-four, and then a quick check keeps the real one.",
    ask: [["Why do more steps make it worse?", "Each step turns the state by a fixed angle towards the right key. After 25 steps it points straight at the key. More steps turn it past the key."]] },
  { title: "Lock 7: reading a hidden angle one digit at a time, with only 2 qubits",
    say: "Lock seven hides its key as an angle, like the position of a hand on a clock. The key is that angle, written with fourteen zeros and ones. The textbook method needs fifteen qubits to read it. We read it with only two. One helper qubit reads the last digit. Then we use the same helper again for the next digit, fourteen times in total. Each time, we first subtract the digits we already know, so every answer is a clear zero or a clear one. This matters because today's quantum computers make small mistakes. Our version uses two of the most error-prone operations in each circuit. The textbook version uses two hundred and thirty.",
    ask: [["What is a two-qubit gate, and why count it?", "It is an operation that makes two qubits interact. On today's machines it fails much more often than an operation on a single qubit, so a circuit with fewer of them gives cleaner results."]] },
  { title: "Locks 8, 9 and 10: breaking RSA by finding a repeating pattern",
    say: "The last three locks are the famous ones, because they attack RSA, the encryption that protects the internet. RSA is safe only because it is very hard to split a huge number into the two smaller numbers that multiply to make it. Shor's algorithm turns that into a different problem: finding a repeating pattern. Look at the row of numbers. We keep doubling, and we keep only the remainder after dividing by thirty-five. After twelve steps, the numbers start again. A quantum computer is very good at spotting that kind of rhythm. Once we know the twelve, simple arithmetic gives us thirty-five equals five times seven. Lock nine splits seventy-seven in the same way, and lock ten uses the same idea to uncover a shared secret.",
    ask: [["How does 12 give the factors?", "Half of 12 is 6. Two to the power 6 is 64, and 64 leaves 29 after dividing by 35. The neighbours of 29 are 28 and 30. 28 shares the factor 7 with 35, and 30 shares the factor 5."]] },
  { title: "We ran lock 7 on a real IBM quantum computer, and all 14 digits were correct",
    say: "Everything so far ran on a simulator, which is a normal computer pretending to be a quantum one. So we also ran lock seven on a real machine: an IBM quantum computer called Kingston. All fourteen digits of the key came out correct. Each bar in the chart is one digit of the key. A bar at one hundred percent would be a perfect signal with no noise. Our average is ninety-seven percent. It worked this well because the circuit is tiny. One honest note: for the real machine we changed how the digits are read out, so that everything could run as one job. The quantum part is the same.",
    ask: [["What is signal strength?", "The write-up calls it contrast. It measures how clearly the qubit points in the expected direction. 100% is a perfect signal and 0% is pure noise. Each value is estimated from 1,024 runs, so a value can land slightly above 100% by chance."]] },
  { title: "Today a laptop still wins, so what matters is how the work grows",
    say: "Now let me be honest. At these small sizes, a laptop beats our quantum circuits easily. A laptop opens lock five in ten milliseconds, while simulating our circuit takes two and a half seconds. What matters is how the work grows when the key gets longer. Every extra bit doubles the work for a normal computer. For Grover, the work doubles only after two extra bits. For Shor the gap is even bigger, and that is why RSA is the one people worry about. One more honest point: our Shor circuits use a shortcut that works only for small numbers, so a real attack needs a much bigger circuit.",
    ask: [["What is the shortcut in the Shor circuits?", "The multiplication step is built from a list of all its answers, which we work out beforehand on a normal computer. That list is as long as the number we are factoring, so it is impossible for a real key. A real attack builds the multiplication from adder circuits instead."]] },
  { title: "Why real encryption is still safe today: noise",
    say: "And here is the reason nobody can break real encryption yet: noise. Every operation on a real quantum computer has a small chance of going wrong. We tested this in simulation with one error in every thousand operations, which is roughly where today's machines are. Lock seven, with two operations, always works. But lock five has almost five thousand operations, and it finds the key only five times in a hundred. Our circuit for seventy-seven has twenty-four thousand, so it would suffer about twenty-four errors in every run. Long circuits need error correction, and that is still being built.",
    ask: [["Did you use error mitigation?", "No. We measured how the plain circuits behave under noise, and we say so in the write-up."]] },
  { title: "What difference does this make?",
    say: "So what difference does this make? First, we showed that these attacks really work from start to finish. Every key came out of a quantum circuit, and one came out of a real machine. Second, we showed that small circuits are what today's machines can actually run. Third, the warning is real. In 2019, experts estimated that breaking real RSA would need twenty million qubits. In 2025, that estimate dropped below one million. So the world is already moving to new encryption that is designed to resist quantum computers. To sum up: we opened all ten locks. The algorithms are ready. The machines are not ready yet, but they are coming.",
    ask: [["Where do the RSA numbers come from?", "Gidney and Ekerå, 2019: about 20 million noisy qubits for 8 hours. Gidney, 2025: under one million noisy qubits in under a week. The new quantum-safe standards are NIST FIPS 203, 204 and 205, published in August 2024."]] },
  { title: "Thank you",
    say: "Thank you for listening. Our thanks also go to the Qiskit YouTube channel and IBM Quantum Learning, where we learned these algorithms. I am happy to take your questions." },
];

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.title = "Cryptographers: Ten Locks, One Message";
  pres.author = "Cryptographers";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;

  pres.defineSlideMaster({
    title: "TITLE", background: { color: NAVY },
    objects: [
      { rect: { x: 8.1, y: 0, w: W - 8.1, h: H, fill: { color: "FFFFFF" }, line: { color: "FFFFFF", width: 0 } } },
      { placeholder: { options: { name: "title", type: "title", x: MX, y: 1.5, w: 6.9, h: 1.7, fontSize: 48, bold: true, color: C.background1, valign: "top", align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: MX, y: 3.3, w: 6.9, h: 2.4, fontSize: 22, color: C.background1, valign: "top", margin: 0 }, text: "" } },
    ],
  });
  for (const name of ["CONTENT", "BACKUP"]) {
    pres.defineSlideMaster({
      title: name, background: { color: "FFFFFF" },
      objects: [
        { placeholder: { options: { name: "title", type: "title", x: MX, y: 0.35, w: W - 2 * MX, h: 1.05, fontSize: name === "CONTENT" ? 30 : 28, bold: true, color: C.text1, valign: "middle", align: "left", margin: 0 }, text: "" } },
      ],
      slideNumber: { x: W - MX - 0.6, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: C.text1, align: "right" },
    });
  }

  // ---------- helpers ----------
  let uid = 0;
  const nm = (p) => `${p} ${++uid}`;
  async function img(slide, file, x, y, w, h, alt) {
    const meta = await sharp(file).metadata();
    const r = meta.width / meta.height;
    let iw = w, ih = w / r;
    if (ih > h) { ih = h; iw = h * r; }
    slide.addImage({ path: file, x: x + (w - iw) / 2, y: y + (h - ih) / 2, w: iw, h: ih, altText: alt, objectName: nm("Picture") });
  }
  const text = (slide, t, o) => slide.addText(t, Object.assign({ isTextBox: true, margin: 0, color: C.text1, fontSize: 16, valign: "top", objectName: nm("Text") }, o));
  const panel = (slide, x, y, w, h, fill) => slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.08, fill: { color: fill || C.background2 }, line: { color: fill || C.background2, width: 0 }, objectName: nm("Panel") });
  // A big number with one plain sentence under it.
  function stat(slide, x, y, w, big, label, pink, h) {
    h = h || 1.5;
    panel(slide, x, y, w, h, pink ? C.accent5 : C.background2);
    text(slide, big, { x: x + 0.2, y: y + 0.1, w: w - 0.4, h: 0.7, fontSize: 32, bold: true, color: pink ? C.accent2 : C.accent1, fontFace: THEME.headFontFace, valign: "middle" });
    text(slide, label, { x: x + 0.2, y: y + 0.78, w: w - 0.4, h: h - 0.85, fontSize: 14 });
  }
  // Numbered steps: a bold line and one or two plain sentences.
  function steps(slide, x, y, w, items, gap) {
    gap = gap || 1.0;
    items.forEach((it, i) => {
      const yy = y + i * gap;
      slide.addShape(pres.ShapeType.ellipse, { x, y: yy, w: 0.48, h: 0.48, fill: { color: C.accent1 }, line: { color: C.accent1, width: 0 }, objectName: nm("Step dot") });
      text(slide, String(i + 1), { x, y: yy, w: 0.48, h: 0.48, fontSize: 16, bold: true, color: C.background1, align: "center", valign: "middle" });
      text(slide, [{ text: it[0], options: { bold: true, fontSize: 17, breakLine: true } }, { text: it[1] }],
        { x: x + 0.66, y: yy - 0.02, w: w - 0.66, h: gap - 0.1, fontSize: 15 });
    });
  }
  const cell = (t, o) => ({ text: t, options: Object.assign({ fontSize: 14, color: C.text1, valign: "middle", margin: [0.03, 0.1, 0.03, 0.1] }, o || {}) });
  const head = (t, o) => cell(t, Object.assign({ bold: true, color: C.background1, fill: { color: C.accent6 } }, o || {}));
  function table(slide, x, y, w, colW, header, rows, opts) {
    const size = (opts && opts.fontSize) || 14;
    const data = [header.map((h) => head(h, { fontSize: size }))].concat(rows.map((r, i) => r.map((v) => {
      const o = { fontSize: size, fill: { color: i % 2 ? C.background2 : C.background1 } };
      if (typeof v === "object") return cell(v.text, Object.assign(o, v.options));
      return cell(v, o);
    })));
    slide.addTable(data, { x, y, w, colW, rowH: (opts && opts.rowH) || 0.42, border: { type: "solid", pt: 0.5, color: GRID }, objectName: nm("Table") });
  }
  const chartLook = (title) => ({
    barDir: "col", chartColors: [BLUE], showLegend: false,
    showTitle: true, title, titleFontSize: 14, titleColor: NAVY, titleFontFace: "+mn-lt",
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 13, dataLabelColor: NAVY, dataLabelFontFace: "+mn-lt",
    catAxisLabelColor: NAVY, valAxisLabelColor: NAVY, catAxisLabelFontSize: 12, valAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
    valAxisMinVal: 0, valGridLine: { color: GRID, size: 0.5 }, catGridLine: { style: "none" },
  });
  let n = 0;
  function add(layout) {
    const t = TALK[n++];
    const s = pres.addSlide({ masterName: layout || "CONTENT", sectionTitle: "Talk" });
    s.addText(t.title, { placeholder: "title" });
    s.addNotes(t.say);
    return s;
  }

  // ================= MAIN TALK =================
  pres.addSection({ title: "Talk" });

  // 1 Title
  {
    const s = add("TITLE");
    s.addText([
      { text: "How we opened ten encrypted files with quantum circuits", options: { breakLine: true } },
      { text: " ", options: { fontSize: 12, breakLine: true } },
      { text: "Team Cryptographers", options: { bold: true, color: C.accent4, breakLine: true } },
      { text: "Avaneesh  ·  Logan  ·  Zach  ·  Bryce" },
    ], { placeholder: "body" });
    text(s, "Qiskit Fall Fest 2026 at The Ohio State University  ·  Challenge 2: Quantum Cryptography", { x: MX, y: 6.55, w: 6.9, h: 0.6, fontSize: 14, color: C.accent3 });
    await img(s, FIG + "model.png", 8.5, 0.4, W - 8.9, 6.7, "3D model of a quantum computer, built by our team");
  }

  // 2 The challenge
  {
    const s = add();
    const cw = 3.55, gap = 0.74, top = 1.7, ch = 3.15;
    const cards = [
      ["1", "A locked file", "The file is scrambled, so it looks like random nonsense.", "8d 44 e1 a7 92 c6 5c 9a 05 b4 6d f5 22 e5 …", false],
      ["2", "A quantum circuit finds the key", "The key is a secret number. Our circuit has to work it out.", "key = 18", true],
      ["3", "The key opens the file", "A normal computer unscrambles the file, and a sentence appears.", "QC-08: inside is a map of old tunnels under Ohio Stadium", false],
    ];
    cards.forEach((c, i) => {
      const x = MX + i * (cw + gap);
      panel(s, x, top, cw, ch, c[4] ? C.accent5 : C.background2);
      s.addShape(pres.ShapeType.ellipse, { x: x + 0.25, y: top + 0.25, w: 0.5, h: 0.5, fill: { color: c[4] ? C.accent2 : C.accent1 }, line: { color: c[4] ? C.accent2 : C.accent1, width: 0 }, objectName: nm("Step dot") });
      text(s, c[0], { x: x + 0.25, y: top + 0.25, w: 0.5, h: 0.5, fontSize: 16, bold: true, color: C.background1, align: "center", valign: "middle" });
      text(s, c[1], { x: x + 0.9, y: top + 0.2, w: cw - 1.1, h: 0.6, fontSize: 18, bold: true, valign: "middle" });
      text(s, c[2], { x: x + 0.25, y: top + 0.95, w: cw - 0.5, h: 0.85, fontSize: 15 });
      text(s, c[3], { x: x + 0.25, y: top + 1.9, w: cw - 0.5, h: 1.0, fontSize: 16, bold: true, fontFace: "Courier New", color: c[4] ? C.accent2 : C.accent1, valign: "middle" });
      if (i < 2) s.addShape(pres.ShapeType.rightArrow, { x: x + cw + 0.14, y: top + ch / 2 - 0.23, w: gap - 0.28, h: 0.46, fill: { color: C.accent3 }, line: { color: C.accent3, width: 0 }, objectName: nm("Arrow") });
    });
    const half = (W - 2 * MX - 0.4) / 2;
    [["The rule. ", "The key must come out of a quantum circuit. Guessing it with a normal computer earns only a quarter of the points."],
     ["Ten locks, ten levels. ", "Each lock is built for a different quantum algorithm, and the locks get harder from 1 to 10."]].forEach((r, i) => {
      const x = MX + i * (half + 0.4);
      text(s, [{ text: r[0], options: { bold: true, color: C.accent1 } }, { text: r[1] }], { x, y: 5.3, w: half, h: 1.4, fontSize: 18, valign: "middle" });
    });
  }

  // 3 The message
  {
    const s = add();
    const lines = [
      "Meet at the Oval when the clock reads 6:47", "bring 3 buckeyes, a blue pen", "Mirror Lake hides a brass key by the northeast rock",
      "Brutus will whistle Carmen Ohio slightly off-key", "count the lamps on the Long Walk: there are nineteen", "the Thompson Library elevator stops twice on floor 8",
      "ask the night librarian for Folio 1870-Q, not 1870-R", "inside is a map of old tunnels under Ohio Stadium", "follow it south past Gate 17 to a door painted scarlet",
      "knock four times, shout O-H, and wait for the I-O",
    ];
    panel(s, MX, 1.6, 8.3, 5.2);
    lines.forEach((l, i) => {
      const y = 1.8 + i * 0.48;
      text(s, String(i + 1).padStart(2, "0"), { x: MX + 0.3, y, w: 0.6, h: 0.42, fontSize: 17, bold: true, color: C.accent1, valign: "middle" });
      text(s, l, { x: MX + 0.95, y, w: 7.2, h: 0.42, fontSize: 17, valign: "middle" });
    });
    stat(s, 9.3, 1.6, 3.43, "10 of 10", "locks opened, and every key came from a quantum circuit", false, 1.6);
    stat(s, 9.3, 3.4, 3.43, "40 of 40", "points for solving the locks, confirmed by the official checker", false, 1.6);
    stat(s, 9.3, 5.2, 3.43, "1 machine", "Lock 7 also ran on a real IBM quantum computer", true, 1.6);
  }

  // 4 The one idea, and the map of the talk
  {
    const s = add();
    steps(s, MX, 1.75, 5.2, [
      ["Hold every possible key at once", "A normal computer tests one key at a time. A quantum computer can hold all of them together."],
      ["Measuring gives only one answer", "So we cannot simply read all the keys out. We need a trick."],
      ["Make the wrong answers cancel", "Like waves in water, wrong answers cancel and the right answer grows. Then we measure."],
    ], 1.6);
    text(s, "Ten locks, but only six ideas", { x: 6.3, y: 1.6, w: 6.43, h: 0.4, fontSize: 17, bold: true });
    table(s, 6.3, 2.1, 6.43, [1.15, 3.18, 2.1], ["Locks", "The idea in plain words", "Algorithm"], [
      ["1 and 3", "Ask one clever question instead of many", "Bernstein-Vazirani, Deutsch-Jozsa"],
      ["2", "Catch a spy on the line", "BB84"],
      ["4", "Collect clues, then solve them", "Simon"],
      ["5 and 6", "Search a haystack faster", "Grover"],
      ["7", "Read a hidden angle digit by digit", "Phase estimation"],
      ["8, 9, 10", "Find a repeating pattern", "Shor"],
    ].map((r) => [{ text: r[0], options: { bold: true, color: C.accent1 } }, r[1], r[2]]), { rowH: [0.5, 0.78, 0.6, 0.6, 0.6, 0.6, 0.6] });
  }

  // 5 Locks 1 and 3
  {
    const s = add();
    steps(s, MX, 1.7, 5.5, [
      ["The query model: count the questions", "The lock is a black box. We can only ask it questions, and the cost is the number of questions."],
      ["Phase kickback: the answer becomes a sign", "We put the target qubit in the state |−⟩. Then the lock marks every input with a plus or a minus sign."],
      ["Interference: the wrong answers cancel", "A second layer of H gates turns the signs into digits that we can measure."],
    ], 1.14);
    panel(s, MX, 5.2, 5.5, 1.6);
    await img(s, FIG + "formula_hadamard.png", MX + 0.2, 5.27, 5.1, 0.72, "Formula: H gates turn an input x into an equal mix of all y, each with the sign minus one to the power x dot y");
    text(s, "This is the rule for a layer of H gates. Its plus and minus signs decide which answers add up and which cancel.", { x: MX + 0.2, y: 6.03, w: 5.1, h: 0.5, fontSize: 13, valign: "middle" });
    text(s, "Formula as taught by IBM Quantum Learning on the Qiskit YouTube channel.", { x: MX + 0.2, y: 6.52, w: 5.1, h: 0.25, fontSize: 11, color: C.accent6, valign: "middle" });
    await img(s, SUB + "/tier01/diagram_bernstein_vazirani.png", 6.5, 1.5, 6.23, 2.1, "Circuit for lock 1, drawn with 4 inputs: H gates, the lock, H gates again, then measure. The target qubit gets X and H.");
    s.addChart(pres.charts.BAR, [
      { name: "Normal computer", labels: ["Lock 1", "Lock 3, per box"], values: [24, 33] },
      { name: "Our circuit", labels: ["Lock 1", "Lock 3, per box"], values: [1, 1] },
    ], Object.assign(chartLook("Questions needed"), { x: 6.5, y: 3.7, w: 2.85, h: 3.1, chartColors: [PINK, BLUE], showLegend: true, legendPos: "b", legendFontSize: 12, legendColor: NAVY, legendFontFace: "+mn-lt", dataLabelFormatCode: "0", valAxisMaxVal: 40, barGapWidthPct: 60, objectName: "Question chart" }));
    panel(s, 9.5, 3.7, 3.23, 1.5);
    text(s, [{ text: "Lock 1: Bernstein-Vazirani", options: { bold: true, fontSize: 15, breakLine: true } }, { text: "The lock hides a 24-digit code. One question returned the whole code, in 16 runs out of 16." }], { x: 9.65, y: 3.75, w: 2.93, h: 1.4, fontSize: 13, valign: "middle" });
    panel(s, 9.5, 5.3, 3.23, 1.5, C.accent5);
    text(s, [{ text: "Lock 3: Deutsch-Jozsa", options: { bold: true, fontSize: 15, breakLine: true } }, { text: "Each of 24 boxes is constant or balanced. A constant box always measures 000000, and a balanced box never does." }], { x: 9.65, y: 5.35, w: 2.93, h: 1.4, fontSize: 13, valign: "middle" });
  }

  // 6 Lock 2
  {
    const s = add();
    // how a bit becomes a qubit
    text(s, "How Alice turns a bit into a qubit", { x: MX, y: 1.5, w: 3.3, h: 0.35, fontSize: 15, bold: true });
    table(s, MX, 1.92, 3.3, [1.1, 1.1, 1.1], ["Basis", "Bit 0", "Bit 1"], [
      [{ text: "Z", options: { bold: true, color: C.accent1 } }, "|0⟩", "|1⟩"],
      [{ text: "X", options: { bold: true, color: C.accent1 } }, "|+⟩", "|−⟩"],
    ], { rowH: 0.42, fontSize: 15 });
    text(s, "Table and example after the Qiskit YouTube channel and IBM Quantum Learning, “Quantum key distribution”.", { x: MX, y: 3.25, w: 3.3, h: 0.45, fontSize: 11, color: C.accent6 });

    // Alice -> Eve -> Bob
    const person = (x, y, col) => {
      s.addShape(pres.ShapeType.ellipse, { x: x + 0.22, y, w: 0.46, h: 0.46, fill: { color: col }, line: { color: col, width: 0 }, objectName: nm("Head") });
      s.addShape(pres.ShapeType.round2SameRect, { x, y: y + 0.52, w: 0.9, h: 0.55, fill: { color: col }, line: { color: col, width: 0 }, objectName: nm("Body") });
    };
    const tokens = (x, y, list, size) => list.forEach((t, i) =>
      text(s, t[0], { x: x + i * 0.52, y, w: 0.5, h: 0.36, fontSize: size || 16, bold: true, fontFace: "Courier New", align: "center", valign: "middle", color: t[1] ? C.accent2 : C.text1 }));
    const arrow = (x, w) => s.addShape(pres.ShapeType.rightArrow, { x, y: 2.72, w, h: 0.3, fill: { color: C.accent3 }, line: { color: C.accent3, width: 0 }, objectName: nm("Arrow") });
    person(4.35, 1.75, C.accent1);
    text(s, "Alice", { x: 4.05, y: 2.9, w: 1.5, h: 0.32, fontSize: 15, bold: true, align: "center", color: C.accent1 });
    text(s, "She sends the key.", { x: 4.05, y: 3.2, w: 1.5, h: 0.5, fontSize: 12, align: "center" });
    text(s, "Alice's bases and qubits", { x: 5.55, y: 1.5, w: 2.1, h: 0.3, fontSize: 12, align: "center" });
    tokens(5.57, 1.82, [["X"], ["Z"], ["X"], ["Z"]]);
    tokens(5.57, 2.22, [["|+⟩"], ["|0⟩"], ["|−⟩"], ["|1⟩"]], 15);
    arrow(5.55, 2.1);
    person(7.95, 1.75, C.accent2);
    text(s, "Eve, the spy", { x: 7.65, y: 2.9, w: 1.5, h: 0.32, fontSize: 15, bold: true, align: "center", color: C.accent2 });
    text(s, "She measures and resends.", { x: 7.65, y: 3.2, w: 1.5, h: 0.5, fontSize: 12, align: "center" });
    text(s, "Eve's guesses and her qubits", { x: 8.95, y: 1.5, w: 2.5, h: 0.3, fontSize: 12, align: "center" });
    tokens(9.17, 1.82, [["Z", 1], ["Z"], ["X"], ["X", 1]]);
    tokens(9.17, 2.22, [["|1⟩", 1], ["|0⟩"], ["|−⟩"], ["|+⟩", 1]], 15);
    arrow(9.15, 2.1);
    text(s, "A wrong guess changes the qubit.", { x: 8.95, y: 3.08, w: 2.5, h: 0.3, fontSize: 12, bold: true, align: "center", color: C.accent2 });
    await img(s, FIG + "bob.png", 11.45, 1.5, 1.28, 1.4, "Bob the Builder, a cartoon builder with a yellow helmet");
    text(s, "Bob", { x: 11.34, y: 2.9, w: 1.5, h: 0.32, fontSize: 15, bold: true, align: "center", color: C.accent1 });
    text(s, "In this lock, we are Bob.", { x: 11.34, y: 3.2, w: 1.5, h: 0.5, fontSize: 12, align: "center" });

    steps(s, MX, 4.02, 6.5, [
      ["We pick a basis for every qubit, without knowing hers", "Z: we measure directly. X: we apply one H gate first, and then we measure."],
      ["We keep only the bits where the bases matched", "Alice announces her bases afterwards. With the same basis, our bit must equal hers."],
      ["We compare a public sample to catch the spy", "Eve guesses wrong half of the time, and half of those bits flip. That is about 25% errors."],
    ], 0.95);
    s.addChart(pres.charts.BAR, [{ name: "Wrong test bits", labels: ["Line A", "Line B"], values: [0, 20.8] }],
      Object.assign(chartLook("Test bits that came out wrong (%)"), { x: 7.35, y: 3.9, w: 2.75, h: 2.9, titleFontSize: 13, dataLabelFormatCode: "0.0", catAxisLabelFontSize: 13, valAxisMaxVal: 30, objectName: "Error chart" }));
    stat(s, 10.26, 3.95, 2.47, "0 of 143", "wrong on line A, so we built the key from it", false, 1.38);
    stat(s, 10.26, 5.42, 2.47, "26 of 125", "wrong on line B, so Eve was listening there", true, 1.38);
  }

  // 7 Lock 4
  {
    const s = add();
    panel(s, MX, 1.55, 5.3, 1.75);
    text(s, [
      { text: "Simon's problem", options: { bold: true, fontSize: 16, breakLine: true } },
      { text: "Input: ", options: { bold: true } }, { text: "a function f on 10-digit strings, hidden in the lock.", options: { breakLine: true } },
      { text: "Promise: ", options: { bold: true } }, { text: "f(x) = f(y) exactly when y = x or y = x ⊕ s.", options: { breakLine: true } },
      { text: "Output: ", options: { bold: true } }, { text: "the secret string s." },
    ], { x: MX + 0.2, y: 1.6, w: 4.9, h: 1.65, fontSize: 14, valign: "middle" });
    text(s, "Problem statement as taught by IBM Quantum Learning on the Qiskit YouTube channel.", { x: MX, y: 3.33, w: 5.3, h: 0.28, fontSize: 11, color: C.accent6, valign: "middle" });
    steps(s, MX, 3.78, 5.3, [
      ["The catch: there is no phase kickback", "The lock writes f(x) into 10 extra qubits, not into a sign. One run cannot show s."],
      ["Each run measures one clue y", "The inputs x and x ⊕ s interfere, so every clue fits the rule y · s = 0."],
      ["Ordinary algebra finishes the job", "Each clue halves the possibilities. About 10 clues leave only s."],
    ], 1.03);
    panel(s, 6.2, 1.55, 2.75, 5.25);
    text(s, "Six of our 37 clues y", { x: 6.4, y: 1.7, w: 2.35, h: 0.4, fontSize: 15, bold: true });
    ["0011000101", "0100110001", "0101110110", "0001011011", "1101000111", "0001100101"].forEach((y, i) =>
      text(s, y, { x: 6.4, y: 2.15 + i * 0.42, w: 2.35, h: 0.4, fontSize: 17, fontFace: "Courier New", valign: "middle" }));
    text(s, "Only one secret fits all of them:", { x: 6.4, y: 4.8, w: 2.35, h: 0.55, fontSize: 14 });
    text(s, "s = 1100011000", { x: 6.4, y: 5.4, w: 2.35, h: 0.45, fontSize: 17, bold: true, color: C.accent2, fontFace: "Courier New", valign: "middle" });
    text(s, "All 40 runs gave a clue that fits it.", { x: 6.4, y: 5.95, w: 2.35, h: 0.7, fontSize: 14 });
    s.addChart(pres.charts.LINE, [
      { name: "Normal computer", labels: ["10", "14", "18", "22"], values: [40, 160, 642, 2567] },
      { name: "Our circuit", labels: ["10", "14", "18", "22"], values: [11, 15, 19, 23] },
    ], Object.assign(chartLook("Tries needed as the secret gets longer"), { x: 9.2, y: 1.5, w: 3.53, h: 3.55, chartColors: [PINK, BLUE], showValue: false, showLegend: true, legendPos: "b", legendFontSize: 12, legendColor: NAVY, legendFontFace: "+mn-lt", lineSize: 3, lineDataSymbolSize: 8, showCatAxisTitle: true, catAxisTitle: "Digits in the secret", catAxisTitleFontSize: 12, catAxisTitleColor: NAVY, valAxisLabelFormatCode: "#,##0", objectName: "Simon chart" }));
    stat(s, 9.2, 5.2, 3.53, "40 → 11", "tries for a normal computer (the birthday paradox) against runs of our circuit", true, 1.6);
  }

  // 8 Locks 5 and 6
  {
    const s = add();
    await img(s, FIG + "t5_rounds.png", MX, 1.55, 6.5, 3.75, "Chance of finding the key against the number of Grover steps: it peaks at 25 steps and is back to zero at 50");
    steps(s, 7.5, 1.75, 5.23, [
      ["Start with every key equally likely", "Lock 5 has 1,024 possible keys."],
      ["Each step boosts the right key", "The lock marks the right key, and the circuit moves a little more chance onto it."],
      ["Stop at the right moment", "After 25 steps the key is certain. More steps make it worse again."],
    ], 1.2);
    stat(s, MX, 5.45, 3.9, "25 vs 512", "Grover steps against the average number of tries on a normal computer", false, 1.35);
    stat(s, MX + 4.1, 5.45, 3.9, "64 → 1", "Lock 6: 64 keys pass the first test, and a quick check keeps the real one", true, 1.35);
    stat(s, MX + 8.2, 5.45, 3.93, "12 steps", "are enough for lock 6, because more matching keys are easier to hit", false, 1.35);
  }

  // 9 Lock 7
  {
    const s = add();
    await img(s, SUB + "/tier07/diagram_iterative_qpe.png", MX, 1.55, 6.6, 3.2, "Two of the 14 small circuits: one helper qubit, one qubit that holds the angle, and one measurement");
    text(s, "The 14 digits, in the order we read them", { x: MX, y: 4.9, w: 6.6, h: 0.35, fontSize: 15, bold: true });
    [1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1].forEach((b, i) => {
      const x = MX + i * 0.47;
      s.addShape(pres.ShapeType.roundRect, { x, y: 5.35, w: 0.42, h: 0.55, rectRadius: 0.05, fill: { color: b ? C.accent1 : C.background2 }, line: { color: b ? C.accent1 : C.accent3, width: 0.5 }, objectName: nm("Bit") });
      text(s, String(b), { x, y: 5.35, w: 0.42, h: 0.55, fontSize: 18, bold: true, align: "center", valign: "middle", color: b ? C.background1 : C.text1 });
    });
    text(s, "Read backwards, they are the key in binary: 13383", { x: MX, y: 6.1, w: 6.6, h: 0.45, fontSize: 18, bold: true, color: C.accent2 });
    steps(s, 7.6, 1.75, 5.13, [
      ["The key is an angle", "Think of a clock hand. The angle is a number with 14 binary digits."],
      ["One helper qubit reads one digit", "We read the last digit first, because it gives a clear 0 or 1."],
      ["Subtract what we know, then repeat", "The same helper qubit is used 14 times."],
    ], 1.1);
    stat(s, 7.6, 5.2, 2.47, "2 vs 15", "qubits: our circuit against the textbook", false, 1.6);
    stat(s, 10.26, 5.2, 2.47, "2 vs 230", "error-prone operations (two-qubit gates)", true, 1.6);
  }

  // 10 Locks 8, 9 and 10
  {
    const s = add();
    text(s, "Keep doubling, and keep only the remainder after dividing by 35:", { x: MX, y: 1.55, w: W - 2 * MX, h: 0.4, fontSize: 17, bold: true });
    const seq = [1, 2, 4, 8, 16, 32, 29, 23, 11, 22, 9, 18, 1, 2, 4, 8];
    const cwid = 0.66, step = (W - 2 * MX - cwid) / (seq.length - 1);
    seq.forEach((v, i) => {
      const x = MX + i * step, again = i >= 12;
      s.addShape(pres.ShapeType.roundRect, { x, y: 2.1, w: cwid, h: 0.62, rectRadius: 0.06, fill: { color: again ? C.accent5 : C.accent1 }, line: { color: again ? C.accent2 : C.accent1, width: 1 }, objectName: nm("Number") });
      text(s, String(v), { x, y: 2.1, w: cwid, h: 0.62, fontSize: 18, bold: true, align: "center", valign: "middle", color: again ? C.accent2 : C.background1 });
    });
    text(s, "The pattern is 12 numbers long.", { x: MX, y: 2.85, w: 12 * step - 0.2, h: 0.4, fontSize: 15, color: C.accent1, bold: true });
    text(s, "Then it starts again.", { x: MX + 12 * step, y: 2.85, w: 4 * step, h: 0.4, fontSize: 15, color: C.accent2, bold: true });
    await img(s, FIG + "t8_hist.png", MX, 3.45, 5.9, 3.35, "Results of the lock 8 circuit: 12 evenly spaced peaks");
    steps(s, 6.9, 3.6, 5.83, [
      ["The circuit finds the length of the pattern", "Its results land on 12 evenly spaced peaks, and that reveals the 12."],
      ["The length gives the two hidden numbers", "Simple arithmetic turns 12 into 35\u00A0=\u00A05\u00A0×\u00A07. For lock 9 it is 77\u00A0=\u00A07\u00A0×\u00A011."],
      ["Lock 10 uses the same idea", "It uncovers a secret number shared by two people. The answer, 14, won 34 of 40 votes."],
    ], 1.08);
  }

  // 11 Hardware
  {
    const s = add();
    const strength = [95.7, 95.9, 94.7, 96.2, 94.8, 100.3, 93.0, 98.4, 100.5, 102.0, 96.2, 96.1, 92.4, 100.2];
    s.addChart(pres.charts.BAR, [{ name: "Signal strength", labels: strength.map((_, i) => String(i + 1)), values: strength }],
      Object.assign(chartLook("Signal strength for each of the 14 digits (%, 100 = perfect)"), { x: MX, y: 1.55, w: 8.4, h: 3.75, dataLabelFormatCode: "0", dataLabelFontSize: 11, valAxisMaxVal: 120, objectName: "Hardware chart" }));
    stat(s, 9.3, 1.55, 3.43, "14 of 14", "digits correct on ibm_kingston", false, 1.17);
    stat(s, 9.3, 2.84, 3.43, "97%", "average signal strength (lowest: 92%)", true, 1.17);
    stat(s, 9.3, 4.13, 3.43, "1 job", "28 small circuits, 1,024 runs each", false, 1.17);
    panel(s, MX, 5.5, W - 2 * MX, 1.3);
    text(s, [{ text: "What we changed for the real machine. ", options: { bold: true } }, { text: "In the simulator, each digit is fed into the next circuit, which would mean 14 separate trips through the queue. On the real machine we measured every digit in two ways and did the subtraction afterwards in software, so everything ran as one job. The quantum part is the same. Job dbr1upujjaos73ai5tl0, 12 Nov 2026." }], { x: MX + 0.2, y: 5.55, w: W - 2 * MX - 0.4, h: 1.2, fontSize: 14, valign: "middle" });
  }

  // 12 Normal computer against quantum
  {
    const s = add();
    table(s, MX, 1.6, 7.4, [1.1, 3.3, 3.0], ["Lock", "Normal computer", "Quantum circuit"], [
      ["1", "24 questions", "1 question"],
      ["3", "up to 33 questions per box", "1 question per box"],
      ["4", "about 40 tries", "about 11 runs"],
      ["5", "512 tries on average", "25 steps"],
      ["7", "16,384 keys to try", "14 small circuits"],
      ["8 to 10", "easy at this size, hopeless for real keys", "grows slowly with the key length"],
    ].map((r) => [{ text: r[0], options: { bold: true, color: C.accent1 } }, r[1], r[2]]), { rowH: [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.72] });
    panel(s, MX, 5.5, 7.4, 1.3, C.accent5);
    text(s, [{ text: "Two honest limits. ", options: { bold: true } }, { text: "A laptop opens lock 5 in 10 milliseconds, and simulating our circuit takes 2.5 seconds. Our Shor circuits also use a shortcut that works only for small numbers." }], { x: MX + 0.2, y: 5.55, w: 7.0, h: 1.2, fontSize: 15, valign: "middle" });
    await img(s, FIG + "scaling_grover.png", 8.3, 1.55, 4.43, 3.3, "Tries needed against key length: the normal computer's line rises twice as steeply as Grover's");
    text(s, "Every extra bit doubles the work for a normal computer. For Grover, the work doubles only after two extra bits.", { x: 8.3, y: 5.0, w: 4.43, h: 1.8, fontSize: 15 });
  }

  // 13 Noise
  {
    const s = add();
    s.addChart(pres.charts.BAR, [{ name: "Runs that find the key", labels: ["Lock 7 (2)", "Lock 1 (143)", "Lock 7, textbook (230)", "Lock 6 (2,064)", "Lock 5 (4,750)"], values: [100, 86, 84, 14, 5] }],
      Object.assign(chartLook("Runs that still find the key when 1 in 1,000 operations goes wrong (%). In brackets: operations in the circuit"), { x: MX, y: 1.55, w: 7.6, h: 5.25, dataLabelFormatCode: "0", valAxisMaxVal: 110, objectName: "Noise chart" }));
    steps(s, 8.6, 1.75, 4.13, [
      ["Every operation can fail", "We simulated 1 failure in every 1,000 two-qubit operations, roughly the level of today's machines."],
      ["Short circuits survive", "Lock 7 always works. Lock 1 works 86 times in 100."],
      ["Long circuits do not", "Our circuit for 77 has 24,000 operations, so about 24 go wrong in every run. It needs error correction."],
    ], 1.5);
    text(s, "A simple noise model on a simulator. We did not use error-mitigation techniques.", { x: 8.6, y: 6.25, w: 4.13, h: 0.55, fontSize: 12 });
  }

  // 14 What difference does this make
  {
    const s = add();
    const cw = (W - 2 * MX - 0.8) / 3;
    const cards = [
      ["10 of 10", "The attacks are real", "We ran every one of these algorithms from start to finish on small keys. Every key came out of a quantum circuit, and one came out of a real machine.", false],
      ["2, not 15", "Small circuits work today", "Lock 7 needs 2 qubits instead of 15, and lock 9 needs 10 instead of 21. That is why lock 7 survived a real, noisy machine.", true],
      ["20 M → 1 M", "The clock is ticking for RSA", "Estimated qubits needed to break real RSA: 20 million in 2019, under 1 million in 2025. Quantum-safe encryption standards were published in 2024.", false],
    ];
    cards.forEach((c, i) => {
      const x = MX + i * (cw + 0.4);
      panel(s, x, 1.6, cw, 3.75, c[3] ? C.accent5 : C.background2);
      text(s, c[0], { x: x + 0.25, y: 1.75, w: cw - 0.5, h: 0.8, fontSize: 36, bold: true, color: c[3] ? C.accent2 : C.accent1, fontFace: THEME.headFontFace, valign: "middle" });
      text(s, c[1], { x: x + 0.25, y: 2.65, w: cw - 0.5, h: 0.4, fontSize: 18, bold: true });
      text(s, c[2], { x: x + 0.25, y: 3.2, w: cw - 0.5, h: 2.0, fontSize: 16 });
    });
    panel(s, MX, 5.65, W - 2 * MX, 1.15, C.accent6);
    text(s, "All ten locks are open. The algorithms are ready. The machines are not ready yet, but they are coming.", { x: MX + 0.3, y: 5.65, w: W - 2 * MX - 0.6, h: 1.15, fontSize: 20, bold: true, color: C.background1, valign: "middle" });
  }

  // 15 Thank you
  {
    const s = add("TITLE");
    s.addText([
      { text: "We are happy to take your questions.", options: { breakLine: true } },
      { text: " ", options: { fontSize: 12, breakLine: true } },
      { text: "Team Cryptographers", options: { bold: true, color: C.accent4, breakLine: true } },
      { text: "Avaneesh  ·  Logan  ·  Zach  ·  Bryce" },
    ], { placeholder: "body" });
    text(s, "Qiskit Fall Fest 2026 at The Ohio State University  ·  Challenge 2: Quantum Cryptography", { x: MX, y: 6.55, w: 6.9, h: 0.6, fontSize: 14, color: C.accent3 });
    const cx = 8.6, cw = W - cx - MX;
    text(s, "Credits", { x: cx, y: 1.5, w: cw, h: 0.5, fontSize: 24, bold: true, color: C.accent1, fontFace: THEME.headFontFace });
    const credits = [
      ["Qiskit YouTube channel and IBM Quantum Learning. ", "We learned these algorithms from their lessons. The BB84 table and example, the H-gate formula and the statement of Simon's problem follow them."],
      ["IBM Quantum. ", "Lock 7 ran on the ibm_kingston quantum computer."],
      ["Qiskit Fall Fest organisers at Ohio State. ", "They built the challenge and its checker."],
      ["Bob the Builder ", "is a character owned by Mattel. The picture is used only as a friendly illustration."],
    ];
    const ch = [1.55, 0.8, 0.8, 0.95];
    let cy = 2.15;
    credits.forEach((c, i) => {
      text(s, [{ text: c[0], options: { bold: true } }, { text: c[1] }], { x: cx, y: cy, w: cw, h: ch[i], fontSize: 15 });
      cy += ch[i] + 0.12;
    });
  }

  // ================= BACKUP =================
  pres.addSection({ title: "Backup" });
  const addBackup = (title) => { const s = pres.addSlide({ masterName: "BACKUP", sectionTitle: "Backup" }); s.addText(title, { placeholder: "title" }); return s; };

  // The numbers the official checker records for every lock.
  {
    const s = addBackup("Backup: what each circuit costs, from the official checker");
    const rows = [
      ["1", "Bernstein-Vazirani", "25", "143", "44", "16 runs, 1 question each"],
      ["2", "BB84 key exchange", "1", "0", "3", "2,048 circuits, 1 run each"],
      ["3", "Deutsch-Jozsa", "7", "7,808", "8,771", "24 circuits, 1 question each"],
      ["4", "Simon", "20", "179", "195", "40 runs, about 11 needed"],
      ["5", "Grover", "19", "4,750", "4,960", "256 runs, 25 steps"],
      ["6", "Grover, then a classical check", "16", "2,064", "2,826", "4,096 runs, 12 steps"],
      ["7", "Phase estimation, one digit at a time", "2", "2", "11", "14 circuits, 64 runs each"],
      ["8", "Shor, N = 35", "9", "5,053", "10,406", "24 runs"],
      ["9", "Shor, N = 77", "10", "23,968", "45,696", "24 runs"],
      ["10", "Shor for a shared secret, p = 83", "10", "13,157", "26,112", "40 runs"],
    ];
    table(s, MX, 1.6, W - 2 * MX, [0.8, 4.2, 1.2, 1.7, 1.2, 3.033], ["Lock", "Algorithm", "Qubits", "Two-qubit gates", "Depth", "Runs"], rows, { rowH: 0.415 });
    text(s, "Depth is the number of layers in the circuit. In locks 1, 3 and 4, almost every gate belongs to the lock that the organisers provided, not to our own part of the circuit.", { x: MX, y: 6.25, w: W - 2 * MX, h: 0.6, fontSize: 14 });
  }

  const backups = [
    { t: "Backup, lock 1: the Parity Vault (Bernstein-Vazirani)", d: SUB + "/tier01/diagram_bernstein_vazirani.png", f: FIG + "t1_hist.png", rows: [
      ["Hidden", "A 24-digit code s"], ["Runs", "1 circuit, 16 runs, 1 question per run"], ["Outcome", "110001111100110101001001 in 16 of 16 runs"],
      ["Circuit cost", "25 qubits, 143 two-qubit gates, depth 44"], ["After the circuit", "The code is the 3-byte key that unscrambles the file"], ["Normal computer", "24 questions, one for each digit"]] },
    { t: "Backup, lock 2: Two Links (BB84)", d: SUB + "/tier02/diagram_bb84.png", f: FIG + "bloch_bb84.png", rows: [
      ["Hidden", "A 280-bit key, sent as 1,024 qubits on each line"], ["Runs", "2,048 one-qubit circuits, 1 run each"], ["Outcome", "Line A: 0 of 143 test bits wrong. Line B: 26 of 125 wrong"],
      ["Circuit cost", "1 qubit, no two-qubit gates, depth 3"], ["After the circuit", "Keep the matching positions, count errors, rebuild the key"], ["Normal computer", "An ordinary line cannot reveal that a spy copied the key"]] },
    { t: "Backup, lock 3: Twenty-Four Seals (Deutsch-Jozsa)", d: SUB + "/tier03/diagram_deutsch_jozsa.png", f: FIG + "t3_hist.png", rows: [
      ["Hidden", "24 key digits: always-the-same box = 0, half-and-half box = 1"], ["Runs", "24 circuits, 16 runs each, 1 question per run"], ["Outcome", "Key 110010110010100010000000"],
      ["Circuit cost", "7 qubits, 7,808 two-qubit gates, nearly all inside the provided lock"], ["Our own gates", "1 X gate and 13 H gates"], ["Normal computer", "Up to 33 questions per box to be certain"]] },
    { t: "Backup, lock 4: the Echo (Simon)", d: SUB + "/tier04/diagram_simon.png", f: FIG + "t4_hist.png", rows: [
      ["Hidden", "A 10-digit pattern s, where inputs x and x ⊕ s give the same output"], ["Runs", "1 circuit, 40 runs, 1 question per run"], ["Outcome", "37 different clues, all with y · s = 0, so s = 1100011000"],
      ["Circuit cost", "20 qubits, 179 two-qubit gates, depth 195"], ["After the circuit", "Solve the clues as equations with 0s and 1s"], ["Normal computer", "About 40 tries to find two inputs with the same output"]] },
    { t: "Backup, lock 5: the Small Safe (Grover)", d: SUB + "/tier05/diagram_grover.png", f: FIG + "t5_hist.png", rows: [
      ["Hidden", "A 10-bit key of a small cipher; the text starts with QC"], ["Runs", "1 circuit, 256 runs, 25 steps"], ["Outcome", "Key 263 in 256 of 256 runs"],
      ["Circuit cost", "19 qubits, 4,750 two-qubit gates, depth 4,960"], ["How the lock marks the key", "It checks that the first two letters decrypt to Q and C"], ["Normal computer", "512 tries on average, 10 milliseconds"]] },
    { t: "Backup, lock 6: the Bigger Safe (Grover with 64 matching keys)", d: SUB + "/tier06/diagram_grover.png", f: FIG + "t6_hist.png", rows: [
      ["Hidden", "A 14-bit key; 64 keys pass the test on the first letter"], ["Runs", "1 circuit, 4,096 runs, 12 steps"], ["Outcome", "64 candidate keys; a classical check keeps key 5401"],
      ["Circuit cost", "16 qubits, 2,064 two-qubit gates, depth 2,826"], ["Why 12 steps", "More matching keys need fewer steps; the wrong count ruins the result"], ["Normal computer", "8,192 tries on average, 0.11 seconds"]] },
    { t: "Backup, lock 7: the Hidden Angle (phase estimation, one digit at a time)", d: SUB + "/tier07/diagram_iterative_qpe.png", f: SUB + "/tier07/diagram_hardware.png", rows: [
      ["Hidden", "An angle k / 2¹⁴ stored inside a one-qubit gate"], ["Runs", "14 circuits, one after another, 64 runs each"], ["Outcome", "k = 13383, which is 11010001000111 in binary"],
      ["Circuit cost", "2 qubits, 2 two-qubit gates, depth 11"], ["Checker note", "It flags circuits under 8 qubits; reusing one qubit is allowed"], ["Normal computer", "Try all 16,384 keys"]] },
    { t: "Backup, lock 8: the Wrapped Key, N = 35 (Shor)", d: SUB + "/tier08/diagram_shor.png", f: FIG + "t8_hist.png", rows: [
      ["Hidden", "The two numbers that multiply to 35; they unwrap the key"], ["Runs", "1 circuit, 24 runs, doubling as the pattern"], ["Outcome", "Pattern length 12, so 35 = 5 × 7"],
      ["Circuit cost", "9 qubits, 5,053 two-qubit gates, depth 10,406"], ["After the circuit", "Turn each result into a fraction, then simple arithmetic"], ["Textbook version", "18 qubits instead of 9"]] },
    { t: "Backup, lock 9: the Wrapped Key, N = 77 (Shor)", d: SUB + "/tier09/diagram_shor.png", f: FIG + "t9_hist.png", rows: [
      ["Hidden", "The two numbers that multiply to 77"], ["Runs", "1 circuit, 24 runs, doubling as the pattern"], ["Outcome", "Pattern length 30, so 77 = 7 × 11, and the key is 31"],
      ["Circuit cost", "10 qubits, 23,968 two-qubit gates, depth 45,696"], ["Honest limit", "The multiplication step is a list of all answers; it does not scale"], ["Textbook version", "21 qubits instead of 10"]] },
    { t: "Backup, lock 10: the Handshake (Shor for a shared secret)", d: SUB + "/tier10/diagram_shor.png", f: FIG + "t10_hist.png", rows: [
      ["Hidden", "The secret number a with 3^a = 11 (remainders after dividing by 83)"], ["Runs", "1 circuit, 40 runs"], ["Outcome", "a = 14, with 34 of 40 votes"],
      ["Circuit cost", "10 qubits, 13,157 two-qubit gates, depth 26,112"], ["After the circuit", "Each run votes for a value of a; one check confirms the winner"], ["Why it is the hardest", "Two patterns are measured at once instead of one"]] },
  ];
  for (const b of backups) {
    const s = addBackup(b.t);
    await img(s, b.d, MX, 1.55, 6.0, 2.55, "Circuit diagram for " + b.t);
    await img(s, b.f, MX, 4.2, 6.0, 2.6, "Measured result for " + b.t);
    table(s, 6.9, 1.6, W - MX - 6.9, [1.85, W - MX - 6.9 - 1.85], ["Item", "Our result"], b.rows.map((r) => [{ text: r[0], options: { bold: true } }, r[1]]), { rowH: 0.7 });
  }

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);

  // ---------- speaker notes file ----------
  const count = (t) => t.split(/\s+/).length;
  const total = TALK.reduce((a, t) => a + count(t.say), 0);
  let md = "# Speaker notes: Cryptographers, 10 minutes\n\n";
  md += "This is the same text as the notes under each slide in `Cryptographers.pptx`. It is written to be spoken aloud, in full sentences. Read it out loud a few times, then change any sentence that does not sound like you.\n\n";
  md += `Total: ${total} words. That is about ${(total / 130).toFixed(1)} minutes at a calm 130 words per minute, and about ${(total / 145).toFixed(1)} minutes at a normal 145.\n\n`;
  md += "If time runs short, slides 12 and 13 can each be cut to their first three sentences.\n";
  TALK.forEach((t, i) => {
    const w = count(t.say);
    md += `\n## Slide ${i + 1}: ${t.title}\n\n_${w} words, about ${Math.round(w / 130 * 60)} seconds_\n\n${t.say}\n`;
    for (const [q, a] of t.ask || []) md += `\n**If a judge asks, "${q}"** ${a}\n`;
  });
  md += "\n## Backup slides\n\nSlide 16 is the table of circuit costs from the official checker. Slides 17 to 26 hold one page for each lock, with its circuit, its measured result and its numbers. Jump to them if a judge asks about one lock in detail.\n";
  fs.writeFileSync(NOTES_OUT, md);
  console.log("wrote", NOTES_OUT, total, "words");
}
main().catch((e) => { console.error(e); process.exit(1); });
