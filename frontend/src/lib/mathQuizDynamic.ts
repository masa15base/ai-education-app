/** backend/app/math_dynamic.py と同じルール（オフライン用サンプル問題） */

export function fourNumericOptions(answer: number): string[] {
  const seen = new Set<number>();
  const out: number[] = [];
  for (const delta of [0, 1, -1, 2, 3, -2, 4, 5, -3]) {
    const x = answer + delta;
    if (x < 0 || seen.has(x)) continue;
    seen.add(x);
    out.push(x);
    if (out.length >= 4) break;
  }
  return out.slice(0, 4).map(String);
}

/** API/DB が3択のまま返したときも算数は4択に揃える */
export function ensureMathFourOptions<T extends { id: string; correct_answer: string; options: string[] }>(
  q: T,
): T {
  if (q.options.length >= 4) return q;
  const ans = parseInt(q.correct_answer, 10);
  if (!Number.isNaN(ans)) {
    return { ...q, options: fourNumericOptions(ans) };
  }
  const m = /^math-(\d+)-(\d+)$/i.exec(q.id);
  if (m) {
    const parts = mathQuestionParts(Number(m[1]), Number(m[2]));
    return { ...q, options: parts.options, correct_answer: parts.correct_answer };
  }
  return q;
}

export function mathQuestionParts(level: number, idx: number): {
  question_text: string;
  correct_answer: string;
  options: string[];
  hint: string;
} {
  const lv = Math.max(1, Math.floor(Number(level)));
  const j = Math.max(1, Math.floor(Number(idx)));
  const j0 = j - 1;
  const v = (lv + j - 1) % 6;

  if (v === 0 || v === 3) {
    const left = lv * 2 + j0;
    const right = j;
    const ans = left + right;
    return {
      question_text: `${left} + ${right} は？`,
      correct_answer: String(ans),
      options: fourNumericOptions(ans),
      hint: '数を並べて足し算してみよう',
    };
  }
  if (v === 1 || v === 4) {
    const left = lv * 3 + j + 5;
    let right = Math.min(lv + j, left - 1);
    right = Math.max(1, right);
    const ans = left - right;
    return {
      question_text: `${left} - ${right} は？`,
      correct_answer: String(ans),
      options: fourNumericOptions(ans),
      hint: '大きい方から小さい方を引いてみよう',
    };
  }
  if (v === 2) {
    const x = Math.min(9, Math.max(2, lv + j0));
    const y = Math.min(9, Math.max(2, j + 1));
    const ans = x * y;
    return {
      question_text: `${x} × ${y} は？`,
      correct_answer: String(ans),
      options: fourNumericOptions(ans),
      hint: '九九の表や、ばらして足す考え方でもよいよ',
    };
  }
  const divisor = Math.min(9, Math.max(2, j + 1));
  const quotient = Math.min(12, Math.max(2, lv + j0));
  const dividend = quotient * divisor;
  const ans = quotient;
  return {
    question_text: `${dividend} ÷ ${divisor} は？`,
    correct_answer: String(ans),
    options: fourNumericOptions(ans),
    hint: 'かけ算の逆だよ。何をかけたら上の数になる？',
  };
}
