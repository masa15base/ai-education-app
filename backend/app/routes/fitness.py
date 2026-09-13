"""Google Fit 連携（歩数自動取り込み）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from ..deps import get_current_uid
from ..schemas import FitnessConnectUrlOut, FitnessStatusOut, FitnessSyncOut
from ..services import google_fit_service as gf

router = APIRouter(tags=["fitness"])


@router.get("/status", response_model=FitnessStatusOut)
def fitness_status(uid: str = Depends(get_current_uid)):
    return FitnessStatusOut(**gf.fitness_status(uid))


@router.get("/connect-url", response_model=FitnessConnectUrlOut)
def fitness_connect_url(uid: str = Depends(get_current_uid)):
    if not gf.is_google_fit_configured():
        raise HTTPException(status_code=503, detail="google_fit_not_configured")
    return FitnessConnectUrlOut(url=gf.build_connect_url(uid))


@router.get("/oauth/callback")
def fitness_oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
):
    front = gf._frontend_url()
    if error or not code or not state:
        return RedirectResponse(f"{front}/?fitness=error", status_code=302)
    uid = gf.verify_oauth_state(state)
    if not uid:
        return RedirectResponse(f"{front}/?fitness=invalid_state", status_code=302)
    try:
        tokens = gf.exchange_auth_code(code)
        refresh = str(tokens.get("refresh_token") or "")
        if not refresh:
            return RedirectResponse(f"{front}/?fitness=no_refresh_token", status_code=302)
        gf._save_connection(uid, refresh)
    except Exception as exc:
        return RedirectResponse(
            f"{front}/?fitness=exchange_failed&detail={str(exc)[:80]}",
            status_code=302,
        )
    return RedirectResponse(f"{front}/?fitness=connected", status_code=302)


@router.post("/sync", response_model=FitnessSyncOut)
def fitness_sync(uid: str = Depends(get_current_uid)):
    if not gf.is_google_fit_configured():
        raise HTTPException(status_code=503, detail="google_fit_not_configured")
    try:
        result = gf.sync_google_fit_for_user(uid)
    except ValueError as exc:
        if str(exc) == "google_fit_not_connected":
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"google_fit_sync_failed: {exc}") from exc
    return FitnessSyncOut(**result)


@router.delete("/disconnect")
def fitness_disconnect(uid: str = Depends(get_current_uid)):
    gf.disconnect(uid)
    return {"ok": True}
