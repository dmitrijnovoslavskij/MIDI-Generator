import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.music_engine import generate_music_plan
from app.midi_gen import create_midi
from app.feedback import FeedbackItem, save_feedback

app = FastAPI()

# Отдаём GUI
GUI_PATH = os.path.join(os.path.dirname(__file__), "gui.html")

@app.get("/", response_class=HTMLResponse)
def index():
    with open(GUI_PATH, "r", encoding="utf-8") as f:
        return f.read()

# Хранит последний промпт для передачи в фидбек
last_prompt = {"value": ""}

class GenerateRequest(BaseModel):
    vibe: str = "any"
    mode: str = "auto"   # minor / major / auto
    bpm: int = 120
    bars: int = 8

class FeedbackRequest(BaseModel):
    key: str
    mode: str
    text: str
    vibe_mismatch: bool = False

@app.post("/generate")
def generate(req: GenerateRequest):
    last_prompt["value"] = req.vibe
    music = generate_music_plan(vibe=req.vibe, mode_hint=req.mode, bpm=req.bpm, bars=req.bars)
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
            "prompt":  music["prompt"],
            "key":     music["key"],
            "mode":    music["mode"],
            "degrees": music["degrees"],
            "bpm":     music["bpm"],
        }
    }


@app.get("/download")
def download_midi(path: str):
    """Отдаёт MIDI файл по абсолютному пути для drag-and-drop и скачивания."""
    import os
    # Безопасность: разрешаем только файлы из midi_output
    abs_path = os.path.abspath(path)
    output_dir = os.path.abspath("midi_output")
    if not abs_path.startswith(output_dir):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.path.exists(abs_path):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="File not found")
    filename = os.path.basename(abs_path)
    return FileResponse(
        abs_path,
        media_type="audio/midi",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.post("/feedback")
def feedback(fb: FeedbackRequest):
    entry = save_feedback(FeedbackItem(
        key=fb.key, mode=fb.mode,
        text=fb.text, prompt=last_prompt["value"],
        vibe_mismatch=fb.vibe_mismatch
    ))

    parts = []
    if entry.get("vibe_mismatch"):
        parts.append("сменю вайб 🎭")
    if entry.get("liked"):
        parts.append("понравилось ✅")
    else:
        parts.append("не понравилось ❌")
    if entry.get("bpm_delta"):
        parts.append(f"темп {'↑' if entry['bpm_delta'] > 0 else '↓'} {abs(entry['bpm_delta'])} BPM")
    if entry.get("preferred_mode"):
        parts.append(f"лад → {entry['preferred_mode']}")
    if entry.get("melody_density"):
        parts.append(f"мелодия → {'реже' if entry['melody_density'] == 'sparse' else 'плотнее'}")
    if entry.get("melody_variety"):
        parts.append(f"разнообразие → {'больше' if entry['melody_variety'] == 'more' else 'меньше'}")
    if entry.get("bass_activity"):
        parts.append(f"бас → {'меньше' if entry['bass_activity'] == 'less' else 'больше'}")
    if entry.get("chord_density"):
        parts.append(f"аккорды → {'реже' if entry['chord_density'] == 'less' else 'чаще'}")
    if entry.get("chord_min_interval"):
        parts.append(f"мин. интервал в аккорде → {entry['chord_min_interval']} полутона")

    summary = ", ".join(parts) if parts else "записано"
    return {"status": "ok", "understood": summary}