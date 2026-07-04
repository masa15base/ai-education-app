import { getAuth } from "firebase/auth";
import { getApiBase } from "./apiBase";
import { formatApiErrorMessage } from "./apiError";

/** multipart で画像を送り、PNG base64 を返す（/api/preprocess-image） */
export type PreprocessResult = {
  imageBase64: string;
  mime: string;
  algorithm?: string;
  meta?: {
    threshold?: number;
    inkRatio?: number;
    hasContent?: boolean;
    contentWidth?: number;
    contentHeight?: number;
  };
};

async function bearerHeaders(): Promise<Record<string, string>> {
  const u = getAuth().currentUser;
  if (!u) {
    throw new Error("LOGIN_REQUIRED");
  }
  const t = await u.getIdToken();
  return { Authorization: `Bearer ${t}` };
}

/** E2E / 開発用。本番では未設定のままにすること */
export function allowAnonymousMediaRequests(): boolean {
  const v = import.meta.env.VITE_ALLOW_ANONYMOUS_MEDIA;
  return v === "1" || v === "true";
}

async function preprocessAuthHeaders(): Promise<Record<string, string>> {
  try {
    return await bearerHeaders();
  } catch {
    if (allowAnonymousMediaRequests()) {
      return {};
    }
    throw new Error("LOGIN_REQUIRED");
  }
}

async function generateAuthHeaders(): Promise<Record<string, string>> {
  try {
    return await bearerHeaders();
  } catch {
    if (allowAnonymousMediaRequests()) {
      return {};
    }
    throw new Error("LOGIN_REQUIRED");
  }
}

/** 元画像ファイルを base64（data URL の payload 部分）にする */
export function readFileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result;
      if (typeof result !== "string") {
        reject(new Error("ファイルの読み込みに失敗しました"));
        return;
      }
      const b64 = result.includes(",") ? result.split(",")[1] : result;
      if (!b64) {
        reject(new Error("画像データが空です"));
        return;
      }
      resolve(b64);
    };
    reader.onerror = () => reject(reader.error ?? new Error("read failed"));
    reader.readAsDataURL(file);
  });
}

export async function preprocessImageToBase64(
  file: File,
): Promise<PreprocessResult> {
  let headers: Record<string, string>;
  headers = await preprocessAuthHeaders();
  const formData = new FormData();
  formData.append("image", file);
  const res = await fetch(`${getApiBase()}/preprocess-image`, {
    method: "POST",
    headers,
    body: formData,
  });
  const text = await res.text().catch(() => "");
  if (!res.ok) {
    throw new Error(
      formatApiErrorMessage(
        res.status,
        text,
        "手書き画像の前処理に失敗しました。ログイン状態と通信を確認してください。",
      ),
    );
  }
  let data: PreprocessResult;
  try {
    data = JSON.parse(text) as PreprocessResult;
  } catch {
    throw new Error("前処理の応答が不正です");
  }
  if (!data.imageBase64) {
    throw new Error("前処理の結果が空です。別の画像で試してください。");
  }
  return data;
}

/** ローカルロジックでキャラ画像 data URL を取得（/api/generate-character） */
export async function generateCharacterFromBase64(
  imageBase64: string,
  opts?: {
    prompt?: string;
    learning_level?: number;
    stage?: string;
    display_name?: string;
  },
): Promise<{
  image: string;
  current_stage_image?: string;
  next_stage_preview?: string | null;
  final_hero_preview?: string | null;
  next_stage?: string | null;
  sprite_design?: Record<string, unknown>;
  character_design_spec?: Record<string, unknown>;
  signature_features?: string[];
  signature_features_ja?: string[];
  debug_notes?: string[];
  understanding_source?: string;
  vision_api_status?: string;
  vision_api_error?: string;
  base_character_image_url?: string | null;
  vision_result?: Record<string, unknown>;
  character_dna?: Record<string, unknown>;
  stage_spec?: Record<string, unknown>;
  generation_prompt?: string;
  validation_result?: { passed?: boolean; issues?: string[]; retried?: boolean };
  generation_mode?: string;
}> {
  const headers = {
    "Content-Type": "application/json",
    ...(await generateAuthHeaders()),
  };
  const body: Record<string, unknown> = { imageBase64 };
  if (opts?.prompt) body.prompt = opts.prompt;
  if (opts?.learning_level != null) body.learning_level = opts.learning_level;
  if (opts?.stage) body.stage = opts.stage;
  if (opts?.display_name) body.display_name = opts.display_name;

  const res = await fetch(`${getApiBase()}/generate-character`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  const text = await res.text().catch(() => "");
  if (!res.ok) {
    throw new Error(
      formatApiErrorMessage(
        res.status,
        text,
        "キャラ画像の作成に失敗しました。",
      ),
    );
  }
  try {
    return JSON.parse(text) as {
      image: string;
      current_stage_image?: string;
      next_stage_preview?: string | null;
      final_hero_preview?: string | null;
      next_stage?: string | null;
      sprite_design?: Record<string, unknown>;
    };
  } catch {
    throw new Error("キャラ画像の応答が不正です");
  }
}
