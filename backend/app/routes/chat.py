from __future__ import annotations

import os
import random
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field

from ..rate_limit import require_chat_rate_limit

router = APIRouter(tags=["chat"])

_CHAT_SYSTEM = """\
あなたは「まなとも」という学習アプリの、小学低学年むけのゆうきなおともだちキャラクターです。

【ことば】
- 「だよ」「だね」「みて」「しよっ」など、やさしい口ぐせで、文は短め（せいぜいこころえて4文くらい）。
- むずかしい漢字や用語はなるべくやめて、ひらがなでもいいくらいわかりやすく。
- しかりすぎない。まちがいも「ちょっとなかまちがい」くらいに受けとめて、いっしょにまなぶきもち。
- からだやあんぜんホケンなど、ひとりで決められないことをきかれたときは、「おとなにきいてね」とすすめる。

【ねらい】
- さんすう・えいご・からだをうごかすことに、きょうみをもてるようにする。
- がんばったところには、すぐにたたえを入れる。
"""


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    message: str = Field(..., min_length=1, max_length=2000)
    character_display_name: str | None = Field(default=None, max_length=40)


class ChatResponse(BaseModel):
    reply: str


class ChatCapabilities(BaseModel):
    openai_configured: bool
    reply_mode: Literal["openai", "simple"]


_FALLBACK_LINES = (
    "うんうん、そのはなしおもしろいね。またきかせて〜。",
    "がんばってるね。きょうはすこしやすんでもいいよ〜。",
    "すごいね。ホームからクイズにもちょうせんしてみて。",
    "{name}もはなせてうれしいな。またあそぼうね。",
    "だいじょうぶ〜。すこしずつでいいよ。",
)


def _fallback_reply(message: str, character_name: str = "みーちゃん") -> str:
    """OPENAI が無効な環境向け・語尾をそろえた簡易応答。"""
    t = (message or "").strip()
    name = (character_name or "みーちゃん").strip() or "みーちゃん"

    def has(*words: str) -> bool:
        return any(w in t for w in words)

    if has("クイズ", "問題"):
        return (
            "クイズやりたいんだね。ホームの「きょうのクイズ」から、さんすうかえいごをえらべるよ。"
            "ちゃれんじしたらけいけんちがふえるよ。"
        )
    if has("おはよう", "こんにちは", "ばんわ", "ハロー"):
        return (
            "こんにちは〜。きょうもいっしょにがんばろうね。なにかあった？"
        )
    if has("歩", "運動", "はしる"):
        return (
            "うごくってたいせつだね。さんぽやあそびだけでも、すごくいいことだよ。すこしずつね〜。"
        )
    if has("むずか", "わからない", "わかんない", "こまっ"):
        return (
            "そっか〜、ちょっとむずかしかったんだね。クイズはやさしいれべるからゆっくりでいいよ。"
        )
    if has("ゲーム", "あそび", "遊"):
        return (
            "あそびもまなびのいっぽだね。すこしやすんだらホームにもどってみて〜。"
        )

    line = random.choice(_FALLBACK_LINES)
    return line.format(name=name)


@router.get("/capabilities", response_model=ChatCapabilities)
def chat_capabilities() -> ChatCapabilities:
    ok = bool(os.getenv("OPENAI_API_KEY", "").strip())
    return ChatCapabilities(
        openai_configured=ok,
        reply_mode="openai" if ok else "simple",
    )


def _nickname_hint(name: str | None) -> str:
    nick = (name or "").strip()[:40]
    if not nick:
        return ""
    return (
        f"\n\n画面の名前は「{nick}」。ときどきそっと名前をまぜてよい。"
        "よびかけは「きみ」を中心に。"
    )


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    _uid: str = Depends(require_chat_rate_limit),
):
    api_key_raw = os.getenv("OPENAI_API_KEY", "").strip()
    raw_name = (request.character_display_name or "").strip()[:40]
    nick = raw_name or "みーちゃん"
    if not api_key_raw:
        return ChatResponse(
            reply=_fallback_reply(request.message, character_name=nick),
        )
    client = AsyncOpenAI(api_key=api_key_raw)
    try:
        system = _CHAT_SYSTEM + _nickname_hint(request.character_display_name)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": request.message},
            ],
            max_tokens=200,
            temperature=0.75,
        )
        reply = response.choices[0].message.content.strip()
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))