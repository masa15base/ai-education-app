/** 教科キーを短い日本語ラベルに（UI 共通） */

export function subjectJa(subject: string): string {
  const s = subject.trim().toLowerCase();
  if (s === "math" || s === "算数") return "算数";
  if (s === "english" || s === "英語") return "英語";
  return subject || "教科";
}
