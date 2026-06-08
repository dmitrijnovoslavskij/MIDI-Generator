import os
import json
import base64
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from app.music_engine import generate_music_plan
from app.midi_gen import create_midi
from app.feedback_vector import VectorFeedbackItem, save_vector_feedback

app = FastAPI()

GUI_PATH = os.path.join(os.path.dirname(__file__), "gui.html")

@app.get("/", response_class=HTMLResponse)
def index():
    with open(GUI_PATH, "r", encoding="utf-8") as f:
        return f.read()

# ─── Generate ──────────────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    energy:     int = 0      # -100..+100
    joy:        int = 0      # -100..+100
    complexity: int = 0      # -100..+100
    bpm:        Optional[int] = None   # user-overridden BPM (optional)
    bars:       int = 8

@app.post("/generate")
def generate(req: GenerateRequest):
    music = generate_music_plan(
        energy=req.energy,
        joy=req.joy,
        complexity=req.complexity,
        bpm=req.bpm,
        bars=req.bars,
    )
    path = create_midi(
        melody=music["melody"],
        chord_track=music["chord_track"],
        bass=music["bass"],
        tpb=music["tpb"],
        bpm=music["bpm"],
    )
    return {
        "file": path,
        "music": {
            "key":        music["key"],
            "mode":       music["mode"],
            "bpm":        music["bpm"],
            "degrees":    music["degrees"],
            "energy":     music["energy"],
            "joy":        music["joy"],
            "complexity": music["complexity"],
        }
    }

# ─── Download ──────────────────────────────────────────────────────────────────
@app.get("/download")
def download_midi(path: str):
    abs_path = os.path.abspath(path)
    output_dir = os.path.abspath("midi_output")
    if not abs_path.startswith(output_dir):
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="File not found")
    filename = os.path.basename(abs_path)
    return FileResponse(
        abs_path,
        media_type="audio/midi",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

# ─── Vector Feedback ───────────────────────────────────────────────────────────
class VectorFeedbackRequest(BaseModel):
    key:               str
    mode:              str
    request_vector:    dict   # {x, y, z}
    perception_vector: dict   # {x, y, z}
    distance:          float

@app.post("/feedback_vector")
def feedback_vector(fb: VectorFeedbackRequest):
    entry = save_vector_feedback(VectorFeedbackItem(
        key=fb.key,
        mode=fb.mode,
        request_vector=fb.request_vector,
        perception_vector=fb.perception_vector,
        distance=fb.distance,
    ))
    # Try to auto-sync to GitHub after each feedback
    try:
        _github_sync_internal()
    except Exception:
        pass

    dist = fb.distance
    if dist < 50:
        verdict = "🎯 Отлично — почти точное попадание"
    elif dist < 120:
        verdict = f"↗ Небольшое расхождение ({int(dist):.0f})"
    else:
        verdict = f"↗↗ Большое расхождение ({int(dist):.0f}) — учту"

    return {"status": "ok", "understood": verdict, "distance": dist}

# ─── GitHub Profile Sync ───────────────────────────────────────────────────────
GITHUB_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "github_config.json")
FEEDBACK_VECTOR_FILE = os.path.join(os.path.dirname(__file__), "feedback_vector.json")

def _load_github_config():
    if os.path.exists(GITHUB_CONFIG_FILE):
        try:
            with open(GITHUB_CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_github_config(cfg: dict):
    with open(GITHUB_CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

class GitHubConnectRequest(BaseModel):
    url:   str
    token: str

@app.post("/github/connect")
def github_connect(req: GitHubConnectRequest):
    import re, requests as rq
    # Parse owner/repo from URL
    m = re.search(r'github\.com/([^/]+)/([^/]+?)(?:\.git)?$', req.url.rstrip('/'))
    if not m:
        return {"ok": False, "error": "Неверный URL репозитория"}
    owner, repo = m.group(1), m.group(2)
    # Verify token via GitHub API
    try:
        r = rq.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers={"Authorization": f"token {req.token}", "Accept": "application/vnd.github.v3+json"},
            timeout=10
        )
        if r.status_code == 200:
            cfg = {"url": req.url, "token": req.token, "owner": owner, "repo": repo}
            _save_github_config(cfg)
            return {"ok": True, "message": f"Подключено: {owner}/{repo}"}
        elif r.status_code == 401:
            return {"ok": False, "error": "Неверный токен"}
        elif r.status_code == 404:
            return {"ok": False, "error": "Репозиторий не найден"}
        else:
            return {"ok": False, "error": f"GitHub ответил {r.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/github/status")
def github_status():
    cfg = _load_github_config()
    if not cfg.get("owner"):
        return {"connected": False}
    return {"connected": True, "message": f"{cfg['owner']}/{cfg['repo']}"}

def _github_sync_internal():
    """Upload feedback_vector.json to GitHub repo as midi-gen-profile/feedback.json"""
    import requests as rq
    cfg = _load_github_config()
    if not cfg.get("token") or not cfg.get("owner"):
        raise RuntimeError("GitHub not configured")
    if not os.path.exists(FEEDBACK_VECTOR_FILE):
        raise RuntimeError("No feedback file yet")

    with open(FEEDBACK_VECTOR_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    encoded = base64.b64encode(content.encode()).decode()

    owner, repo, token = cfg["owner"], cfg["repo"], cfg["token"]
    path = "midi-gen-profile/feedback.json"
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

    # Check if file exists (need SHA to update)
    r = rq.get(api_url, headers=headers, timeout=10)
    sha = r.json().get("sha") if r.status_code == 200 else None

    payload = {
        "message": "Update MIDI Gen preference profile",
        "content": encoded,
    }
    if sha:
        payload["sha"] = sha

    r2 = rq.put(api_url, headers=headers, json=payload, timeout=15)
    if r2.status_code not in (200, 201):
        raise RuntimeError(f"GitHub API error {r2.status_code}: {r2.text[:200]}")

def _github_pull_internal():
    """Download feedback_vector.json from GitHub"""
    import requests as rq
    cfg = _load_github_config()
    if not cfg.get("token") or not cfg.get("owner"):
        raise RuntimeError("GitHub not configured")

    owner, repo, token = cfg["owner"], cfg["repo"], cfg["token"]
    path = "midi-gen-profile/feedback.json"
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

    r = rq.get(api_url, headers=headers, timeout=10)
    if r.status_code == 404:
        raise RuntimeError("Профиль не найден в репозитории — нечего загружать")
    r.raise_for_status()
    content = base64.b64decode(r.json()["content"]).decode()
    with open(FEEDBACK_VECTOR_FILE, "w", encoding="utf-8") as f:
        f.write(content)

@app.post("/github/sync")
def github_sync():
    try:
        # Push local → GitHub, then pull GitHub → local (to merge if multiple devices)
        _github_sync_internal()
        return {"ok": True, "message": "Профиль синхронизирован ↑ GitHub"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/github/pull")
def github_pull():
    try:
        _github_pull_internal()
        return {"ok": True, "message": "Профиль загружен из GitHub"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
