const pptxgen = require("pptxgenjs");
const sharp = require("sharp");
const path = require("path");
const SKILL = "/home/avopti/.claude/skills/synced/a2ad65a7-7655-4bae-a49d-422dfad1841b_6001c603-3df1-4a5c-b446-eca2626d28bb/pptx";
const { applyTheme } = require(SKILL + "/scripts/apply_theme.js");

const SUB = "/home/avopti/Documents/QiskitFallFest2026/Submission";
const FIG = SUB + "/slides/figures/";
const OUT = SUB + "/slides/Cryptographers.pptx";

const THEME = {
  name: "Cryptographers",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1F2933", lt1: "FFFFFF", dk2: "060D18", lt2: "F1F3F5",
    accent1: "BA0C2F", accent2: "5B6770", accent3: "9AA5B1", accent4: "C9A227",
    accent5: "2A6F97", accent6: "3D4852", hlink: "BA0C2F", folHlink: "5B6770",
  },
};
const W = 13.333, H = 7.5, MX = 0.6;

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.title = "Cryptographers: Ten Locks, One Message";
  pres.author = "Cryptographers";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;
  const FOOT = "Cryptographers  ·  Qiskit Fall Fest 2026  ·  Challenge 2: Ten Locks, One Message";

  pres.defineSlideMaster({
    title: "TITLE", background: { color: "FFFFFF" },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: MX, y: 2.0, w: 6.9, h: 1.9, fontSize: 44, bold: true, color: C.text1, valign: "top", align: "left", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: MX, y: 4.1, w: 6.9, h: 1.2, fontSize: 20, color: C.text1, valign: "top", margin: 0 }, text: "" } },
    ],
  });
  for (const [name] of [["CONTENT", ""], ["BACKUP", "Backup  ·  "]]) {
    pres.defineSlideMaster({
      title: name, background: { color: "FFFFFF" },
      objects: [
        { placeholder: { options: { name: "title", type: "title", x: MX, y: 0.35, w: W - 2 * MX, h: 1.05, fontSize: name === "CONTENT" ? 32 : 28, bold: true, color: C.text1, valign: "middle", align: "left", margin: 0 }, text: "" } },
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
  const panel = (slide, x, y, w, h) => slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.08, fill: { color: C.background2 }, line: { color: C.background2, width: 0 }, objectName: nm("Panel") });
  function stat(slide, x, y, w, big, label, color) {
    panel(slide, x, y, w, 1.45);
    text(slide, big, { x: x + 0.2, y: y + 0.12, w: w - 0.4, h: 0.75, fontSize: 36, bold: true, color: color || C.accent1, fontFace: THEME.headFontFace, valign: "middle" });
    text(slide, label, { x: x + 0.2, y: y + 0.88, w: w - 0.4, h: 0.5, fontSize: 14, color: C.text1 });
  }
  function steps(slide, x, y, w, items, gap) {
    gap = gap || 1.0;
    items.forEach((it, i) => {
      const yy = y + i * gap;
      slide.addShape(pres.ShapeType.ellipse, { x, y: yy, w: 0.46, h: 0.46, fill: { color: C.accent1 }, line: { color: C.accent1, width: 0 }, objectName: nm("Step dot") });
      text(slide, String(i + 1), { x, y: yy, w: 0.46, h: 0.46, fontSize: 16, bold: true, color: C.background1, align: "center", valign: "middle" });
      text(slide, [{ text: it[0], options: { bold: true, breakLine: true } }, { text: it[1], options: { color: C.text1 } }],
        { x: x + 0.62, y: yy - 0.04, w: w - 0.62, h: gap - 0.08, fontSize: 16 });
    });
  }
  const cell = (t, o) => ({ text: t, options: Object.assign({ fontSize: 14, color: C.text1, valign: "middle", margin: [0.03, 0.08, 0.03, 0.08] }, o || {}) });
  const head = (t, o) => cell(t, Object.assign({ bold: true, color: C.background1, fill: { color: C.accent6 } }, o || {}));
  function table(slide, x, y, w, colW, header, rows, opts) {
    const fs = (opts && opts.fontSize) || 14;
    const data = [header.map((h) => head(h, { fontSize: fs }))].concat(rows.map((r, i) => r.map((v, j) => {
      const o = { fontSize: fs, fill: { color: i % 2 ? C.background2 : C.background1 } };
      if (typeof v === "object") return cell(v.text, Object.assign(o, v.options));
      return cell(v, o);
    })));
    slide.addTable(data, { x, y, w, colW, rowH: (opts && opts.rowH) || 0.42, border: { type: "solid", pt: 0.5, color: "E1E5EA" }, objectName: nm("Table") });
  }
  const add = (section, layout) => pres.addSlide({ masterName: layout || "CONTENT", sectionTitle: section });

  // ================= MAIN TALK =================
  pres.addSection({ title: "Talk" });

  // 1 Title
  {
    const s = add("Talk", "TITLE");
    s.addText("Ten locks, one message", { placeholder: "title" });
    s.addText([{ text: "Team Cryptographers", options: { bold: true, color: C.accent1, breakLine: true } }, { text: "Avaneesh  ·  Logan  ·  Zach" }], { placeholder: "body" });
    text(s, "Qiskit Fall Fest 2026 at The Ohio State University  ·  Challenge 2: Quantum Cryptography", { x: MX, y: 6.55, w: 6.9, h: 0.6, fontSize: 14, color: C.text1 });
    await img(s, FIG + "model.png", 8.2, 0.4, W - 8.8, 6.7, "3D model of a quantum computer cryostat, built by our team");
    s.addNotes("Good evening. We are team Cryptographers. Ten files were locked. Each lock opens with a different quantum algorithm. In the next ten minutes I will show you how we opened all ten, what each circuit costs, and what happens at real key sizes. The model on the right is a quantum computer I built in 3D for my own website.");
  }

  // 2 The message
  {
    const s = add("Talk");
    s.addText("We opened all ten locks, and each one ran a quantum circuit", { placeholder: "title" });
    const lines = [
      "Meet at the Oval when the clock reads 6:47", "bring 3 buckeyes, a blue pen", "Mirror Lake hides a brass key by the northeast rock",
      "Brutus will whistle Carmen Ohio slightly off-key", "count the lamps on the Long Walk: there are nineteen", "the Thompson Library elevator stops twice on floor 8",
      "ask the night librarian for Folio 1870-Q, not 1870-R", "inside is a map of old tunnels under Ohio Stadium", "follow it south past Gate 17 to a door painted scarlet",
      "knock four times, shout O-H, and wait for the I-O",
    ];
    panel(s, MX, 1.6, 8.3, 5.15);
    lines.forEach((l, i) => {
      const y = 1.78 + i * 0.48;
      text(s, String(i + 1).padStart(2, "0"), { x: MX + 0.3, y, w: 0.6, h: 0.42, fontSize: 16, bold: true, color: C.accent1, valign: "middle" });
      text(s, l, { x: MX + 0.95, y, w: 7.2, h: 0.42, fontSize: 16, valign: "middle" });
    });
    stat(s, 9.3, 1.6, 3.43, "10 / 10", "tiers: hash matches and a circuit ran in solve()");
    stat(s, 9.3, 3.45, 3.43, "40 / 40", "tier points in the official checker");
    stat(s, 9.3, 5.3, 3.43, "1 real device", "tier 7 also ran on ibm_kingston", C.text1);
    s.addNotes("Here is the message. Ten lines, one from each file. Every line matches the official hash, and every tier ran a quantum circuit inside solve. That is all forty tier points in the checker. We also ran one tier on a real IBM quantum computer. I will come back to that.");
  }

  // 3 Results table
  {
    const s = add("Talk");
    s.addText("Six ideas open ten locks: what each scored circuit costs", { placeholder: "title" });
    const rows = [
      ["1", "Bernstein-Vazirani", "25", "143", "44", "16 shots, 1 oracle call"],
      ["2", "BB84 key exchange", "1", "0", "3", "2,048 circuits, 1 shot each"],
      ["3", "Deutsch-Jozsa", "7", "7,808", "8,771", "24 circuits, 1 oracle call each"],
      ["4", "Simon", "20", "179", "195", "40 shots, about 11 needed"],
      ["5", "Grover", "19", "4,750", "4,960", "256 shots, 25 rounds"],
      ["6", "Grover + checksum filter", "16", "2,064", "2,826", "4,096 shots, 12 rounds"],
      ["7", "Iterative phase estimation", "2", "2", "11", "14 rounds, 64 shots each"],
      ["8", "Shor, N = 35", "9", "5,053", "10,406", "24 shots"],
      ["9", "Shor, N = 77", "10", "23,968", "45,696", "24 shots"],
      ["10", "Shor for discrete log, p = 83", "10", "13,157", "26,112", "40 shots"],
    ];
    table(s, MX, 1.6, W - 2 * MX, [0.8, 3.9, 1.3, 1.7, 1.3, 3.133], ["Tier", "Algorithm", "Qubits", "2-qubit gates", "Depth", "Runs"], rows, { rowH: 0.415 });
    text(s, "Numbers from tools/check_submission.py after transpiling to rz, sx, x, cx. In tiers 1, 3 and 4 almost every gate belongs to the provided oracle.", { x: MX, y: 6.3, w: W - 2 * MX, h: 0.5, fontSize: 14, color: C.text1 });
    s.addNotes("This table is every tier on one slide. The numbers come from the official checker. Ten tiers, but only six ideas. Tiers one and three are the same trick. Five and six are both Grover. Eight, nine and ten are all Shor. So I will explain six ideas. Look at tier seven: two qubits and two two-qubit gates. Remember that one.");
  }

  // 4 Tiers 1 and 3
  {
    const s = add("Talk");
    s.addText("Tiers 1 and 3: one question answers what classical needs 24 or 33 for", { placeholder: "title" });
    steps(s, MX, 1.7, 4.6, [
      ["Target qubit in |−⟩", "The oracle's answer becomes a + or − sign on the input. This is phase kickback."],
      ["Ask about all inputs at once", "Hadamards put every input in the question. One oracle call signs them all."],
      ["Let the signs interfere", "Hadamards again. Tier 1: the hidden string appears. Tier 3: 000000 means constant."],
    ], 1.25);
    await img(s, FIG + "bloch_minus.png", MX + 0.6, 5.3, 2.2, 1.55, "Bloch sphere of the target qubit in the minus state");
    text(s, "Without |−⟩ the method fails: 50% in our test.", { x: MX + 2.9, y: 5.6, w: 2.3, h: 1.0, fontSize: 14, color: C.text1 });
    await img(s, SUB + "/tier01/diagram_bernstein_vazirani.png", 5.6, 1.6, 7.13, 2.5, "Bernstein-Vazirani circuit: X and H on the target, H on 24 inputs, oracle, H, measure");
    await img(s, FIG + "t3_hist.png", 5.6, 4.2, 7.13, 2.6, "Histograms: a constant oracle gives 000000 in all 16 shots, a balanced oracle never does");
    s.addNotes("Tiers one and three use the same trick. First, we put the target qubit in the minus state. Now the oracle does not flip a bit. It puts a plus or minus sign on the input. That is phase kickback. Second, Hadamard gates put all inputs into one question. One oracle call signs all of them. Third, Hadamards again, and the signs add up or cancel. In tier one the hidden twenty-four bit string appears directly. All sixteen shots agree. In tier three, a constant function always gives all zeros, and a balanced function never does. You see both cases in the histograms. Classically, tier one needs twenty-four questions and tier three needs up to thirty-three. We need one.");
  }

  // 5 Tier 2
  {
    const s = add("Talk");
    s.addText("Tier 2: the eavesdropper leaves 21% errors, the clean link leaves none", { placeholder: "title" });
    await img(s, FIG + "bloch_bb84.png", MX, 1.55, 7.2, 2.3, "Bloch spheres of the four BB84 states: 0, 1, plus and minus");
    steps(s, MX, 4.1, 7.0, [
      ["Measure every qubit in a random basis", "Z: measure. X: one H, then measure. Keep only where our basis matched Alice's."],
      ["Compare with Alice's public check bits", "Eve guesses the wrong basis half the time, and half of those flip: 25% expected."],
      ["Build the key from the clean link only", "383 kept bits solve for the 280-bit key. The tapped link gives garbage."],
    ], 0.92);
    s.addChart(pres.charts.BAR, [{ name: "Errors on check bits", labels: ["link_A (clean)", "link_B (tapped)"], values: [0, 20.8] }], {
      x: 8.1, y: 1.6, w: 4.63, h: 3.6, barDir: "col", chartColors: ["BA0C2F"], showLegend: false,
      showTitle: true, title: "Errors on the public check bits (%)", titleFontSize: 14, titleColor: "1F2933", titleFontFace: "+mn-lt",
      showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0", dataLabelFontSize: 14, dataLabelColor: "1F2933", dataLabelFontFace: "+mn-lt",
      catAxisLabelColor: "1F2933", valAxisLabelColor: "1F2933", catAxisLabelFontSize: 13, valAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
      valAxisMaxVal: 30, valAxisMinVal: 0, valGridLine: { color: "E1E5EA", size: 0.5 }, catGridLine: { style: "none" }, objectName: "QBER chart",
    });
    stat(s, 8.1, 5.35, 4.63, "0 gates or 1", "per measurement circuit: nothing smaller exists", C.text1);
    s.addNotes("Tier two is BB84. Alice sends qubits in four possible states. You see them on the Bloch spheres. We measure each qubit in a random basis. Later Alice tells us her bases, and we keep only the matching ones. Now the important part. Eve measured one link. She had to guess the basis. Half the time she guessed wrong, and then half of our results flip. So we expect twenty-five percent errors. We measured zero on link A and twenty-one percent on link B. So link B is tapped. We build the key from link A. The security comes from physics. Measuring an unknown qubit changes it.");
  }

  // 6 Tier 4
  {
    const s = add("Talk");
    s.addText("Tier 4: every run returns one equation about the secret", { placeholder: "title" });
    steps(s, MX, 1.7, 4.4, [
      ["f(x) = f(x ⊕ s)", "The function repeats with a hidden shift s. We want s, 10 bits."],
      ["Each run gives a y with y·s = 0", "The pair x and x ⊕ s interfere. Only those y survive."],
      ["Solve the equations classically", "About 9 independent y pin down s. Gaussian elimination, mod 2."],
    ], 1.3);
    panel(s, 5.3, 1.6, 3.5, 5.15);
    text(s, "Measured y (6 of 37)", { x: 5.5, y: 1.75, w: 3.1, h: 0.4, fontSize: 14, bold: true, color: C.text1 });
    ["0011000101", "0100110001", "0101110110", "0001011011", "1101000111", "0001100101"].forEach((y, i) =>
      text(s, y, { x: 5.5, y: 2.2 + i * 0.42, w: 3.1, h: 0.4, fontSize: 18, fontFace: "Courier New", valign: "middle" }));
    text(s, "every one has y·s = 0", { x: 5.5, y: 4.8, w: 3.1, h: 0.4, fontSize: 14, color: C.text1 });
    text(s, "s = 1100011000", { x: 5.5, y: 5.3, w: 3.1, h: 0.5, fontSize: 20, bold: true, color: C.accent1, fontFace: "Courier New", valign: "middle" });
    text(s, "the only non-zero solution", { x: 5.5, y: 5.85, w: 3.1, h: 0.4, fontSize: 14, color: C.text1 });
    await img(s, FIG + "t4_hist.png", 9.1, 1.6, 3.63, 2.9, "Histogram: all 37 measured strings satisfy y dot s equals 0");
    table(s, 9.1, 4.75, 3.63, [2.23, 1.4], ["Method", "Queries"], [["Classical, all inputs", "1,024"], ["Classical, collision search", "about 40"], [{ text: "Simon", options: { bold: true } }, { text: "about 11", options: { bold: true, color: C.accent1 } }]], { rowH: 0.48 });
    s.addNotes("Tier four is Simon's algorithm. The function repeats with a hidden shift s. We want s. Each run of the circuit gives a random string y. But not fully random. Every y satisfies y dot s equals zero. So each run is one equation about the secret. We took forty shots and got thirty-seven different strings. All of them satisfy the equation. Then ordinary linear algebra gives one answer for s. On average eleven runs are enough. A classical search needs about forty queries to find a collision, and this gap grows exponentially with the size.");
  }

  // 7 Tiers 5 and 6
  {
    const s = add("Talk");
    s.addText("Tiers 5 and 6: Grover finds the key in 25 rounds, and more rounds make it worse", { placeholder: "title" });
    await img(s, FIG + "t5_rounds.png", MX, 1.55, 6.3, 3.6, "Grover success probability against number of rounds: peak of 1.0 at 25 rounds, back to 0 at 50");
    await img(s, FIG + "t6_hist.png", 7.1, 1.55, 5.63, 3.6, "Tier 6 histogram: 4096 shots spread over the 64 keys that pass the first-byte test");
    stat(s, MX, 5.3, 2.9, "25 vs 512", "tier 5: Grover rounds vs average classical tries");
    stat(s, MX + 3.1, 5.3, 2.9, "−32% CX", "our oracle vs a plain Toffoli build", C.text1);
    stat(s, 7.1, 5.3, 2.72, "64 → 1", "tier 6: Grover returns 64 keys, a checksum keeps one");
    stat(s, 10.01, 5.3, 2.72, "12 rounds", "64 marked keys need fewer rounds", C.text1);
    s.addNotes("Tiers five and six are Grover search. The oracle marks the right key with a minus sign. Each round moves probability towards that key. Look at the left plot. The grey line is theory and the red dots are our measurements. At twenty-five rounds we find the key every time. But at fifty rounds the probability is back to zero. Grover is a rotation. If you rotate too far, you pass the answer. In tier six, sixty-four keys pass the test. So Grover needs only twelve rounds, and it returns all sixty-four. Then a classical checksum keeps one. We also made the oracle cheaper. Our version uses thirty-two percent fewer CNOT gates than a plain Toffoli build.");
  }

  // 8 Tier 7
  {
    const s = add("Talk");
    s.addText("Tier 7: we read a 14-bit angle with 2 qubits instead of 15", { placeholder: "title" });
    await img(s, SUB + "/tier07/diagram_iterative_qpe.png", MX, 1.55, 6.6, 3.2, "One round of iterative phase estimation: H, controlled power of U, phase correction, H, measure");
    steps(s, 7.6, 1.7, 5.13, [
      ["Kick the phase onto one control qubit", "Controlled U^(2^j) on the eigenstate. One round reads one bit."],
      ["Start from the lowest bit", "Its phase is exactly 0 or π, so the result is certain."],
      ["Remove what we already know", "A phase gate cancels the measured bits. Then read the next bit."],
    ], 1.05);
    text(s, "Bits as measured, lowest first", { x: MX, y: 4.95, w: 6, h: 0.35, fontSize: 14, bold: true, color: C.text1 });
    [1, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1].forEach((b, i) => {
      const x = MX + i * 0.47;
      s.addShape(pres.ShapeType.roundRect, { x, y: 5.35, w: 0.42, h: 0.55, rectRadius: 0.05, fill: { color: b ? C.accent1 : C.background2 }, line: { color: b ? C.accent1 : C.accent3, width: 0.5 }, objectName: nm("Bit") });
      text(s, String(b), { x, y: 5.35, w: 0.42, h: 0.55, fontSize: 18, bold: true, align: "center", valign: "middle", color: b ? C.background1 : C.text1 });
    });
    text(s, "k = 13383  →  angle = 13383 / 2¹⁴", { x: MX, y: 6.05, w: 6.6, h: 0.45, fontSize: 18, bold: true, color: C.text1 });
    stat(s, 7.6, 5.0, 2.47, "2 vs 230", "two-qubit gates: ours vs textbook");
    stat(s, 10.26, 5.0, 2.47, "14×", "one control qubit, reused for 14 rounds", C.text1);
    s.addNotes("Tier seven hides a fourteen-bit angle inside a gate. The textbook method is phase estimation with fourteen control qubits. We use one control qubit and repeat it fourteen times. Each round reads one bit. We start with the lowest bit, because its phase is exactly zero or pi. So the result is certain. Then a phase gate removes the bits we already know, and we read the next one. The result is two qubits, and two two-qubit gates per circuit, against two hundred and thirty for the textbook version. This is why the checker shows a flag for a small number of qubits. The scoring rules say this recycling technique is allowed, if we explain it.");
  }

  // 9 Tiers 8-10
  {
    const s = add("Talk");
    s.addText("Tiers 8, 9 and 10: breaking RSA means finding a period", { placeholder: "title" });
    await img(s, SUB + "/tier08/diagram_shor.png", MX, 1.5, W - 2 * MX, 2.55, "Shor order-finding circuit with one recycled control qubit and controlled modular multipliers");
    await img(s, FIG + "t8_hist.png", MX, 4.15, 5.9, 2.7, "Tier 8 histogram: evenly spaced peaks at multiples of 1024 divided by 12");
    steps(s, 6.9, 4.25, 5.83, [
      ["Powers of 2 mod 35 repeat every r = 12", "The circuit measures y near a multiple of 1024 / r."],
      ["The period gives the factors", "gcd(2⁶ − 1, 35) = 7 and gcd(2⁶ + 1, 35) = 5."],
      ["Same idea, bigger locks", "Tier 9: r = 30 gives 7 × 11. Tier 10: a = 14 wins 34 of 40 votes."],
    ], 0.88);
    s.addNotes("Tiers eight, nine and ten are Shor's algorithm. The key idea: factoring becomes finding a period. Take powers of two, modulo thirty-five. They repeat with period twelve. The circuit measures a number y, and y is always near a multiple of one thousand twenty-four divided by twelve. You see the evenly spaced peaks. From the period, two greatest common divisors give the factors, seven and five. Tier nine is the same with N equals seventy-seven and period thirty. Tier ten is Diffie-Hellman. There we measure two phases, and each shot votes for the secret exponent. Fourteen wins with thirty-four of forty votes. Like tier seven, we reuse one control qubit, so tier nine needs ten qubits, not twenty-one.");
  }

  // 10 Classical vs quantum
  {
    const s = add("Talk");
    s.addText("At these sizes classical wins, so the argument is about growth", { placeholder: "title" });
    table(s, MX, 1.6, 7.4, [1.1, 2.3, 1.9, 2.1], ["Tier", "Classical", "Quantum", "Growth, n bits"], [
      ["1", "24 questions", "1", "n vs 1"],
      ["3", "33 questions", "1", "2ⁿ⁻¹ + 1 vs 1"],
      ["4", "about 40", "about 11 runs", "2^(n/2) vs n"],
      ["5", "512 tries, 10 ms", "25 rounds, 2.5 s", "2ⁿ vs √2ⁿ"],
      ["7", "16,384 keys, 0.06 s", "14 rounds", "2ⁿ vs n rounds"],
      ["8–10", "instant", "5k–24k gates", "sub-exp vs n³"],
    ], { rowH: 0.52 });
    panel(s, MX, 5.45, 7.4, 1.3);
    text(s, [{ text: "Where our circuits are still toys. ", options: { bold: true } }, { text: "Our Shor multiplier is a lookup table of all N values: that is more classical work than factoring 77 by hand. A scalable version builds it from adders, about n² gates." }], { x: MX + 0.2, y: 5.55, w: 7.0, h: 1.1, fontSize: 14, valign: "middle" });
    await img(s, FIG + "scaling_grover.png", 8.3, 1.6, 4.43, 3.3, "Log plot: classical tries grow as 2 to the n, Grover rounds as the square root");
    text(s, "Grover is only a square-root gain: a 128-bit key still needs about 2⁶⁴ rounds. Doubling the key length is the defence.", { x: 8.3, y: 5.05, w: 4.43, h: 1.6, fontSize: 14, color: C.text1 });
    s.addNotes("Now the analysis. First, classical computers win at these sizes. A brute-force search of tier five takes ten milliseconds. Our simulated Grover takes two and a half seconds. So the argument is not speed today. It is growth. Double the key size, and classical work squares, while Grover's work only doubles. For Shor the gap is bigger: polynomial against sub-exponential. Second, some of our circuits are still toys. Our Shor multiplier is built from a table of all values. That table is more classical work than factoring seventy-seven by hand. A scalable version uses adder circuits. We say this clearly in our write-up.");
  }

  // 11 Hardware
  {
    const s = add("Talk");
    s.addText("It ran on a real quantum computer: 14 of 14 bits correct on ibm_kingston", { placeholder: "title" });
    await img(s, SUB + "/tier07/diagram_hardware.png", MX, 1.55, 8.6, 3.6, "Hardware result: 14 measured phase points close to the ideal circle, and contrast per bit between 0.92 and 1.0");
    stat(s, 9.5, 1.6, 3.23, "0.97", "average contrast (1 = perfect), lowest 0.92");
    stat(s, 9.5, 3.25, 3.23, "28 circuits", "one job, 1,024 shots each, 2 two-qubit gates each", C.text1);
    panel(s, MX, 5.35, W - 2 * MX, 1.4);
    text(s, [{ text: "What changed for hardware. ", options: { bold: true } }, { text: "The scored solution feeds each bit into the next circuit: 14 jobs in the queue. On the device we read every round in the X and Y basis and do the same correction in software, so it is one job. Same eigenstate, same controlled U, same phase kickback. Job dbr1upujjaos73ai5tl0, 12 Nov 2026." }], { x: MX + 0.2, y: 5.45, w: W - 2 * MX - 0.4, h: 1.2, fontSize: 14, valign: "middle" });
    s.addNotes("We ran tier seven on a real IBM quantum computer, ibm kingston. All fourteen bits came out correct, and the decrypted line matches the hash. On the left, each point is one key bit. The grey circle is the ideal result with no noise. Our points sit very close to it. The average contrast is zero point nine seven. One honest note. This is a variant of our scored circuit. The scored version feeds each bit into the next circuit, which means fourteen jobs in the queue. For hardware we read each round in two bases and do the correction in software. So it is one job. The quantum part is the same.");
  }

  // 12 Noise
  {
    const s = add("Talk");
    s.addText("Noise decides what survives: the gate count is the whole story", { placeholder: "title" });
    s.addChart(pres.charts.BAR, [{ name: "Success at 0.1% error per two-qubit gate", labels: ["Tier 7 (2 gates)", "Tier 1 (143)", "Textbook QPE (230)", "Tier 6 (2,064)", "Tier 5 (4,750)"], values: [100, 86, 84, 14, 5] }], {
      x: MX, y: 1.55, w: 7.6, h: 5.2, barDir: "col", chartColors: ["BA0C2F"], showLegend: false,
      showTitle: true, title: "Runs that find the key at 0.1% error per two-qubit gate (%, simulated)", titleFontSize: 14, titleColor: "1F2933", titleFontFace: "+mn-lt",
      showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0", dataLabelFontSize: 14, dataLabelColor: "1F2933", dataLabelFontFace: "+mn-lt",
      catAxisLabelColor: "1F2933", valAxisLabelColor: "1F2933", catAxisLabelFontSize: 13, valAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
      valAxisMaxVal: 110, valAxisMinVal: 0, valGridLine: { color: "E1E5EA", size: 0.5 }, catGridLine: { style: "none" }, objectName: "Noise chart",
    });
    steps(s, 8.6, 1.75, 4.13, [
      ["Rule of thumb", "A circuit survives while error rate × gate count stays well below 1."],
      ["Small circuits can vote", "Tier 1 recovers the key at every tested rate with a majority vote of 101 shots."],
      ["Shor at N = 77 cannot", "24,000 gates at 0.1% is about 24 errors per run. It needs error correction."],
    ], 1.45);
    text(s, "Depolarizing noise on Aer. Tier 1 and textbook QPE are single-shot. We did not run error mitigation (ZNE, PEC).", { x: 8.6, y: 6.0, w: 4.13, h: 0.75, fontSize: 12, color: C.text1 });
    s.addNotes("What about noise on the bigger circuits? We simulated every tier with an error after each two-qubit gate. At zero point one percent error, which is close to today's hardware, tier seven with two gates always works. Tier one with one hundred forty-three gates still works eighty-six percent of the time. Tier five with almost five thousand gates finds the key in only five percent of runs. The rule is simple. A circuit survives while error rate times gate count stays well below one. Our Shor circuit for seventy-seven has twenty-four thousand gates. That is about twenty-four errors per run. It needs error correction. We did not run error mitigation, and we say so.");
  }

  // 13 Scaling
  {
    const s = add("Talk");
    s.addText("From toy locks to real keys: what would have to change", { placeholder: "title" });
    table(s, MX, 1.6, W - 2 * MX, [2.6, 4.3, 5.233], ["", "What we ran", "A real key"], [
      [{ text: "Factoring (RSA)", options: { bold: true } }, "N = 77: 10 qubits, 24,000 gates, lookup-table multiplier", "RSA-2048: thousands of error-corrected qubits, billions of gates. Estimates: 20 million noisy qubits for 8 hours (Gidney and Ekerå, 2019); under 1 million in under a week (Gidney, 2025)"],
      [{ text: "Key search (Grover)", options: { bold: true } }, "10-bit key: 25 rounds, 4,750 gates", "128-bit key: about 2⁶⁴ rounds of a far larger oracle. Double the key length and the gain is gone"],
      [{ text: "Key exchange (BB84)", options: { bold: true } }, "1,024 qubits per link, perfect devices", "Real links are noisy without Eve: error correction, privacy amplification, an error threshold near 11%"],
      [{ text: "Hardware today", options: { bold: true } }, "2 gates: 14 of 14 bits on ibm_kingston", "Thousands of gates: needs error correction, not better luck"],
    ], { rowH: [0.45, 1.05, 0.8, 0.8, 0.6] });
    panel(s, MX, 6.0, W - 2 * MX, 0.78);
    text(s, "All ten locks opened. The algorithms are ready; the machines that can run them at real size are not here yet.", { x: MX + 0.2, y: 6.0, w: W - 2 * MX - 0.4, h: 0.78, fontSize: 18, bold: true, color: C.accent1, valign: "middle" });
    s.addNotes("Last slide: what changes at real sizes. For RSA, we factored seventy-seven with ten qubits. RSA two thousand forty-eight needs thousands of error-corrected qubits and billions of gates. Published estimates went from twenty million noisy qubits in two thousand nineteen to under one million in two thousand twenty-five. For Grover, a one hundred twenty-eight bit key still needs two to the sixty-four rounds. Doubling the key length is enough defence. For BB84, real links have noise even without Eve, so they need error correction and a threshold. To close: we opened all ten locks. The algorithms are ready. The machines that can run them at real size are not here yet. Thank you. I am happy to take questions.");
  }

  // ================= BACKUP =================
  pres.addSection({ title: "Backup" });
  const backups = [
    { t: "Tier 1: The Parity Vault (Bernstein-Vazirani)", d: SUB + "/tier01/diagram_bernstein_vazirani.png", f: FIG + "t1_hist.png", rows: [
      ["Hidden", "24-bit string s; the oracle computes s·x"], ["Runs", "1 circuit, 16 shots, 1 oracle call per shot"], ["Outcome", "110001111100110101001001 in 16 of 16 shots"],
      ["Scored circuit", "143 two-qubit gates, depth 44, 290 gates, 25 qubits"], ["Classical work", "XOR the 3 key bytes with the ciphertext"], ["Classical cost", "24 questions, one per bit"]] },
    { t: "Tier 2: Two Links (BB84)", d: SUB + "/tier02/diagram_bb84.png", f: FIG + "bloch_bb84.png", rows: [
      ["Hidden", "280-bit key sent as 1,024 qubits per link"], ["Runs", "2,048 one-qubit circuits, 1 shot each"], ["Outcome", "link_A: 0 of 143 check bits wrong. link_B: 26 of 125 wrong"],
      ["Scored circuit", "0 two-qubit gates, depth 3, 3 gates, 1 qubit"], ["Classical work", "Sifting, error count, one GF(2) solve (reconcile)"], ["Classical cost", "A classical channel cannot detect a copy at all"]] },
    { t: "Tier 3: Twenty-Four Seals (Deutsch-Jozsa)", d: SUB + "/tier03/diagram_deutsch_jozsa.png", f: FIG + "t3_hist.png", rows: [
      ["Hidden", "24 key bits: constant = 0, balanced = 1"], ["Runs", "24 circuits, 16 shots, 1 oracle call each"], ["Outcome", "Key 110010110010100010000000"],
      ["Scored circuit", "7,808 two-qubit gates, depth 8,771, 7 qubits (oracle)"], ["Our own gates", "1 X and 13 H, no two-qubit gates"], ["Classical cost", "33 questions per seal to be certain"]] },
    { t: "Tier 4: The Echo (Simon)", d: SUB + "/tier04/diagram_simon.png", f: FIG + "t4_hist.png", rows: [
      ["Hidden", "10-bit s with f(x) = f(x ⊕ s)"], ["Runs", "1 circuit, 40 shots, 1 oracle call per shot"], ["Outcome", "37 different y, all with y·s = 0; s = 1100011000"],
      ["Scored circuit", "179 two-qubit gates, depth 195, 451 gates, 20 qubits"], ["Classical work", "Gaussian elimination mod 2"], ["Alternatives", "Grover also finds s, with 7,310 two-qubit gates"]] },
    { t: "Tier 5: The Small Safe (Grover)", d: SUB + "/tier05/diagram_grover.png", f: FIG + "t5_hist.png", rows: [
      ["Hidden", "10-bit key of a toy cipher; plaintext starts with QC"], ["Runs", "1 circuit, 256 shots, 25 rounds"], ["Outcome", "Key 263 in 256 of 256 shots"],
      ["Scored circuit", "4,750 two-qubit gates, depth 4,960, 19 qubits"], ["Oracle", "12 checks from 2 known bytes, relative-phase Toffolis"], ["Classical cost", "512 tries on average, 10 ms"]] },
    { t: "Tier 6: The Bigger Safe (Grover with 64 marked keys)", d: SUB + "/tier06/diagram_grover.png", f: FIG + "t6_hist.png", rows: [
      ["Hidden", "14-bit key; 64 keys pass the first-byte test"], ["Runs", "1 circuit, 4,096 shots, 12 rounds"], ["Outcome", "64 candidate keys; the checksum keeps 5401"],
      ["Scored circuit", "2,064 two-qubit gates, depth 2,826, 16 qubits"], ["If the count is wrong", "Assuming 1 or 1,024 marked keys drops success sharply"], ["Classical cost", "8,192 tries on average, 0.11 s"]] },
    { t: "Tier 7: The Hidden Angle (iterative phase estimation)", d: SUB + "/tier07/diagram_iterative_qpe.png", f: SUB + "/tier07/diagram_hardware.png", rows: [
      ["Hidden", "Angle k / 2¹⁴ in the eigenvalue of a one-qubit gate"], ["Runs", "14 circuits in series, 64 shots each"], ["Outcome", "k = 13383 = 11010001000111"],
      ["Scored circuit", "2 two-qubit gates, depth 11, 16 gates, 2 qubits"], ["Checker flag", "Under 8 active qubits: allowed, the control is recycled"], ["Powers of U", "Built from U's matrix by squaring, as the tier allows"]] },
    { t: "Tier 8: The Wrapped Key, N = 35 (Shor)", d: SUB + "/tier08/diagram_shor.png", f: FIG + "t8_hist.png", rows: [
      ["Hidden", "RSA modulus 35; the key is wrapped with it"], ["Runs", "1 circuit, 24 shots, base a = 2"], ["Outcome", "r = 12, so 35 = 5 × 7"],
      ["Scored circuit", "5,053 two-qubit gates, depth 10,406, 9 qubits"], ["Classical work", "Continued fractions, gcd, modular inverse"], ["Alternatives", "Textbook Shor 18 qubits; Grover factoring 1,776 CX"]] },
    { t: "Tier 9: The Wrapped Key, N = 77 (Shor)", d: SUB + "/tier09/diagram_shor.png", f: FIG + "t9_hist.png", rows: [
      ["Hidden", "RSA modulus 77, e = 7"], ["Runs", "1 circuit, 24 shots, base a = 2"], ["Outcome", "r = 30, so 77 = 7 × 11, d = 43, key 31"],
      ["Scored circuit", "23,968 two-qubit gates, depth 45,696, 10 qubits"], ["Multiplier", "Permutation of 1..76 as a chain of value swaps"], ["Alternatives", "Textbook Shor 21 qubits; Grover factoring 4,056 CX"]] },
    { t: "Tier 10: The Handshake (Shor for discrete log)", d: SUB + "/tier10/diagram_shor.png", f: FIG + "t10_hist.png", rows: [
      ["Hidden", "Exponent a with 3^a = 11 mod 83, subgroup order 41"], ["Runs", "1 circuit, 40 shots, 7 phase bits per register"], ["Outcome", "a = 14 with 34 of 40 votes; shared secret from B = 49"],
      ["Scored circuit", "13,157 two-qubit gates, depth 26,112, 10 qubits"], ["Classical work", "Rounding, modular inverse, one check of g^a"], ["Alternatives", "Grover search 49,698 CX; baby-step giant-step classically"]] },
  ];
  for (const b of backups) {
    const s = add("Backup", "BACKUP");
    s.addText(b.t, { placeholder: "title" });
    await img(s, b.d, MX, 1.55, 6.0, 2.55, "Circuit diagram for " + b.t);
    await img(s, b.f, MX, 4.2, 6.0, 2.6, "Measurement result for " + b.t);
    table(s, 6.9, 1.6, W - MX - 6.9, [1.75, W - MX - 6.9 - 1.75], ["Item", "Our result"], b.rows.map((r) => [{ text: r[0], options: { bold: true } }, r[1]]), { rowH: 0.7 });
  }

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
}
main().catch((e) => { console.error(e); process.exit(1); });
