# キャラクター画像生成の要件

手書きの絵写真からドット絵風キャラを作る機能の入出力仕様です。実装の単一ソースは `backend/app/character_image_spec.py` です。

## 処理の流れ

1. **アップロード** … 手書きの写真・画像ファイルを選択
2. **前処理** … `POST /api/preprocess-image` で線画を抽出（PNG）
3. **生成** … `POST /api/generate-character` でカラー化（PNG data URL）
4. **確認** … アプリ上でプレビュー → OK でホームに反映

## 入力画像（アップロード）

| 項目 | 内容 |
|------|------|
| **推奨形式** | **JPEG**（`.jpg` / `.jpeg`）、**PNG**（`.png`） |
| **その他対応** | WebP（`.webp`）、GIF（`.gif`）、BMP（`.bmp`） |
| **MIME タイプ** | `image/jpeg`, `image/png`, `image/webp`, `image/gif`, `image/bmp` |
| **最大サイズ** | **8MB**（環境変数 `MAX_PREPROCESS_IMAGE_BYTES` で変更可） |
| **非対応** | HEIC / HEIF（iPhone 標準の「効率」形式）、PDF、動画 |

スマホで HEIC のまま撮影している場合は、写真アプリの設定で **「互換性優先」＝ JPEG** にするか、共有前に JPEG / PNG に変換してください。

## 前処理アルゴリズム（`binary_scribble_v3_famicom`）

| ステップ | 内容 |
|----------|------|
| 1 | 入力の長辺を最大 1600px に正規化 |
| 2 | グレースケール + オートコントラスト + メディアン + ガンマ補正 |
| 3 | **Otsu 法 + 平均輝度** のブレンドで二値化（影・白紙に強い） |
| 4 | 形態学的クリーンアップ（孤立ノイズ除去 + 線のわずかな太化） |
| 5 | 余白トリム → 正方形キャンバス |
| 6 | 絵の占有率に応じた **ピクセルグリッド**（40〜128）へ BOX 縮小 → 再二値化 |
| 7 | **NEAREST** で 512px まで拡大（ジャギーなドット絵） |

カラー化（`character_local_gen`）では 1px アウトライン + 塗りでコントラストを付けます。

## 中間出力（前処理）

| 項目 | 内容 |
|------|------|
| **形式** | **PNG** |
| **MIME** | `image/png` |
| **エンコーディング** | Base64（JSON の `imageBase64`） |
| **解像度** | 最大辺 512px（正方形、`max_edge`） |

## 最終出力（キャラ生成）

| 項目 | 内容 |
|------|------|
| **形式** | **PNG** |
| **MIME** | `image/png` |
| **エンコーディング** | Data URL（`data:image/png;base64,...`） |
| **生成方式** | `pixel_character_generator`（32/48/64px スプライト → 512px NEAREST） |
| **保存先** | `backend/static/generated/`（API 実行時に自動保存） |

### stage 別スプライト

| stage | 解像度 | 色数 | 装飾 |
|-------|--------|------|------|
| baby | 32×32 | 3 | なし・丸体 |
| child | 48×48 | 4 | 手足・明るい表情 |
| student | 64×64 | 5 | 帽子・本など |
| adult | 64×64 | 6 | マント・星バッジなど |

`learning_level` または `stage` を `POST /api/generate-character` に渡すと反映されます。

## API で要件を取得

```http
GET /api/preprocess-image/info
```

レスポンスの `requirements` に、上記の MIME・拡張子・上限・ワークフローが含まれます。

## 撮影のコツ（品質）

- 白い紙に濃いペンで描く
- 影が入らない明るい場所で撮る
- 絵全体が切れないように写す

## 関連ファイル

- `backend/app/character_image_spec.py` … 要件定数
- `backend/app/routes/image_preprocess.py` … 前処理 API
- `backend/app/routes/generate_character.py` … 生成 API
- `frontend/src/pages/Upload.tsx` … アップロード UI
- `frontend/src/lib/characterImageRequirements.ts` … フロント用定数
