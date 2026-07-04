/** 進捗保存（lib/api と同じ契約） */
import { saveProgress as apiSaveProgress } from "../lib/api";

export async function save(subject: string, level: number, score: number) {
  return apiSaveProgress({ subject, level, score });
}
