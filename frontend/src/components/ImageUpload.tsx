import React, { useState } from 'react';
import { getAuth } from 'firebase/auth';
import { Button } from '@/components/ui/button';
import { getApiBase, getApiOriginForStaticPath } from '@/lib/apiBase';

const ImageUpload = () => {
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [generatedImage, setGeneratedImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      console.log("📸 Image selected:", e.target.files[0]);
      setImageFile(e.target.files[0]);
    }
  };

  const handleGenerate = async () => {
    console.log("⚙️ handleGenerate called");

    if (!imageFile) {
      console.warn("🛑 No image file selected");
      return;
    }

    const reader = new FileReader();
    reader.onloadend = async () => {
      const base64Image = reader.result?.toString().split(',')[1];

      if (!base64Image) {
        console.warn("🛑 Failed to convert image to base64");
        return;
      }

      try {
        const u = getAuth().currentUser;
        if (!u) {
          console.warn('Not signed in');
          return;
        }
        setLoading(true);
        console.log("🚀 Sending POST request to API...");

        const token = await u.getIdToken();

        const apiBase = getApiBase();
        const response = await fetch(`${apiBase}/generate-character`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            imageBase64: base64Image,
            prompt: "a cute anime-style character based on a child’s drawing",
          }),
        });

        if (!response.ok) {
          const text = await response.text();
          throw new Error(text || response.statusText);
        }

        const data = (await response.json()) as { image: string };
        console.log("✅ API response received:", data);

        const raw = data.image as string;
        const originPrefix = getApiOriginForStaticPath();
        const imageUrl = raw.startsWith('http')
          ? raw
          : raw.startsWith('/') && originPrefix
            ? `${originPrefix}${raw}`
            : raw;

        setGeneratedImage(imageUrl);
      } catch (error) {
        console.error("❌ API error:", error);
      } finally {
        setLoading(false);
      }
    };

    reader.readAsDataURL(imageFile);
  };

  return (
    <div className="p-4 max-w-xl mx-auto text-center">
      <h2 className="text-2xl font-bold mb-4">キャラ画像をアップロード</h2>
      <input
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        className="mb-4"
      />
      <Button onClick={handleGenerate} disabled={loading || !imageFile}>
        {loading ? '生成中...' : 'AIでキャラを生成する'}
      </Button>

      {generatedImage && (
        <div className="mt-6">
          <h3 className="text-xl font-bold mb-2">生成されたキャラクター</h3>
          <img
            src={generatedImage}
            alt="Generated Character"
            className="mx-auto max-w-full rounded-lg border"
          />
        </div>
      )}
    </div>
  );
};

export default ImageUpload;