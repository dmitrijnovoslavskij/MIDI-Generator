"""
CLAP (Contrastive Language-Audio Pretraining) engine.
Используется для семантического поиска похожих треков по промпту.
Модель: laion/clap-htsat-unfused (~600MB, грузится один раз)
"""
import os
import json
import numpy as np

_model = None
_processor = None
_device = None

CLAP_MODEL = "laion/clap-htsat-unfused"

def _load():
    global _model, _processor, _device
    if _model is not None:
        return

    import torch
    from transformers import ClapTextModelWithProjection, AutoTokenizer

    if torch.backends.mps.is_available():
        _device = "mps"
    elif torch.cuda.is_available():
        _device = "cuda"
    else:
        _device = "cpu"

    print(f"[CLAP] Загружаем модель на {_device}...")
    _processor = AutoTokenizer.from_pretrained(CLAP_MODEL)
    _model = ClapTextModelWithProjection.from_pretrained(CLAP_MODEL).to(_device)
    _model.eval()
    print("[CLAP] Модель готова ✅")


def get_embedding(text: str) -> list:
    """Возвращает CLAP-эмбеддинг текста как список float."""
    try:
        import torch
        _load()
        inputs = _processor(text=text, return_tensors="pt", padding=True, truncation=True, max_length=77)
        inputs = {k: v.to(_device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = _model(**inputs)
        emb = outputs.text_embeds[0].cpu().numpy()
        # L2-нормализация
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
        return emb.tolist()
    except Exception as e:
        print(f"[CLAP] Ошибка эмбеддинга: {e}")
        return []


def cosine_similarity(a: list, b: list) -> float:
    a, b = np.array(a), np.array(b)
    if a.shape != b.shape or np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def find_similar_tracks(prompt_embedding: list, history: list, top_k: int = 3) -> list:
    """
    Ищет top_k похожих треков из истории фидбека по косинусному сходству.
    Возвращает список dict с полями: similarity, liked, key, mode, bpm_delta, ...
    """
    if not prompt_embedding or not history:
        return []

    scored = []
    for item in history:
        emb = item.get("prompt_embedding")
        if not emb:
            continue
        sim = cosine_similarity(prompt_embedding, emb)
        scored.append((sim, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"similarity": s, **item} for s, item in scored[:top_k]]
