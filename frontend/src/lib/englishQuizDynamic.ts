import englishVocabRows from './english_vocab.dynamic.json';

export type EnglishVocabRow = [string, string, string[], string];

/** backend/app/english_vocab.py の ENGLISH_VOCAB と同一（オフライン用フォールバック） */
export const ENGLISH_VOCAB = englishVocabRows as EnglishVocabRow[];

export function englishVocabRowIndex(level: number, idx: number): number {
  const lv = Math.max(1, Math.floor(Number(level)));
  const j = Math.max(1, Math.floor(Number(idx)));
  return ((lv - 1) * 5 + (j - 1)) % ENGLISH_VOCAB.length;
}

function extraJapaneseDistractors(jpCorrect: string, skipRow: number): string[] {
  const out: string[] = [];
  for (let i = 0; i < ENGLISH_VOCAB.length; i++) {
    if (i === skipRow) continue;
    const jp = ENGLISH_VOCAB[i][1];
    if (jp !== jpCorrect && !out.includes(jp)) out.push(jp);
    if (out.length >= 8) break;
  }
  return out;
}

/** backend english_vocab.four_string_options と同一ルール */
export function englishFourOptions(
  level: number,
  idx: number,
  jpCorrect: string,
  threeOpts: string[],
): string[] {
  const pos = englishVocabRowIndex(level, idx);
  const seed = `english-${level}-${idx}`;
  const seen = new Set<string>();
  const pool: string[] = [];
  for (const o of [jpCorrect, ...threeOpts, ...extraJapaneseDistractors(jpCorrect, pos)]) {
    const t = o.trim();
    if (!t || seen.has(t)) continue;
    seen.add(t);
    pool.push(t);
    if (pool.length >= 4) break;
  }
  while (pool.length < 4) {
    const pad = `（選択肢${pool.length + 1}）`;
    if (!seen.has(pad)) {
      seen.add(pad);
      pool.push(pad);
    } else break;
  }
  const orderKey = (s: string) => {
    let h = 0;
    const str = `${seed}|${s}`;
    for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
    return h.toString(16).padStart(8, '0');
  };
  return pool.slice(0, 4).sort((a, b) => orderKey(a).localeCompare(orderKey(b)));
}
