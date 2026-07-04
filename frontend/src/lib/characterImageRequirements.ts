/** backend/app/character_image_spec.py と同期（オフライン表示・accept 属性用） */

export const CHARACTER_INPUT_MIME_TYPES = [
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/gif',
  'image/bmp',
] as const;

export const CHARACTER_INPUT_EXTENSIONS = [
  '.jpg',
  '.jpeg',
  '.png',
  '.webp',
  '.gif',
  '.bmp',
] as const;

export const CHARACTER_INPUT_ACCEPT = [
  ...CHARACTER_INPUT_MIME_TYPES,
  ...CHARACTER_INPUT_EXTENSIONS,
].join(',');

export const CHARACTER_PREPROCESS_OUTPUT = 'PNG（image/png）';
export const CHARACTER_OUTPUT = 'PNG（image/png・data URL）';

export const CHARACTER_INPUT_FORMAT_LABEL =
  'JPEG / PNG / WebP / GIF / BMP（HEIC・PDF・動画は不可）';

export const CHARACTER_MAX_UPLOAD_MB = 8;

export type CharacterImageRequirements = {
  workflow?: string[];
  input?: {
    mime_types?: string[];
    extensions?: string[];
    max_bytes?: number;
    max_bytes_human?: string;
    unsupported?: string[];
    notes?: string[];
  };
  preprocess_output?: { mime?: string; format?: string };
  character_output?: { mime?: string; format?: string; encoding?: string };
};

export function isAllowedCharacterInputFile(file: File): boolean {
  const mime = (file.type || '').toLowerCase();
  if (mime && CHARACTER_INPUT_MIME_TYPES.includes(mime as (typeof CHARACTER_INPUT_MIME_TYPES)[number])) {
    return true;
  }
  const name = file.name.toLowerCase();
  return CHARACTER_INPUT_EXTENSIONS.some((ext) => name.endsWith(ext));
}

export function formatRequirementsSummary(req?: CharacterImageRequirements | null): string {
  const exts = req?.input?.extensions ?? [...CHARACTER_INPUT_EXTENSIONS];
  const maxHuman =
    req?.input?.max_bytes_human ??
    (req?.input?.max_bytes
      ? `${Math.round(req.input.max_bytes / (1024 * 1024))}MB`
      : `${CHARACTER_MAX_UPLOAD_MB}MB`);
  return `アップロード: ${exts.join(', ')}（最大 ${maxHuman}）→ 生成結果: PNG`;
}
