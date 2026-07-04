/** バックエンド未更新時も Replicate なしでキャラ画像を作る（Python character_local_gen と同等の簡易版） */

export function buildCharacterDataUrlFromBase64(imageBase64: string): Promise<string> {
  const src = imageBase64.trim().startsWith("data:")
    ? imageBase64.trim()
    : `data:image/png;base64,${imageBase64.trim()}`;

  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      const w = img.naturalWidth || img.width || 64;
      const h = img.naturalHeight || img.height || 64;
      const canvas = document.createElement("canvas");
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        reject(new Error("canvas not supported"));
        return;
      }
      ctx.fillStyle = "#e8f8ff";
      ctx.fillRect(0, 0, w, h);
      ctx.drawImage(img, 0, 0, w, h);
      const id = ctx.getImageData(0, 0, w, h);
      const d = id.data;
      let lumSum = 0;
      for (let i = 0; i < d.length; i += 4) {
        lumSum += 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
      }
      const meanLum = lumSum / (d.length / 4);
      const invert = meanLum < 128;
      for (let i = 0; i < d.length; i += 4) {
        let lum = 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
        if (invert) lum = 255 - lum;
        if (lum < 200) {
          d[i] = 45;
          d[i + 1] = 55;
          d[i + 2] = 90;
          d[i + 3] = 255;
        } else {
          d[i] = 255;
          d[i + 1] = 255;
          d[i + 2] = 255;
          d[i + 3] = 255;
        }
      }
      ctx.putImageData(id, 0, 0);
      resolve(canvas.toDataURL("image/png"));
    };
    img.onerror = () => reject(new Error("画像の読み込みに失敗しました"));
    img.src = src;
  });
}

export function isReplicateNotConfiguredError(status: number, bodyText: string): boolean {
  if (status !== 503) return false;
  const t = bodyText.toLowerCase();
  return t.includes("replicate") && t.includes("not configured");
}
