"""
feedback_vector.py — хранение векторного фидбека.

Вместо текстового анализа и бинарных оценок — два 3D-вектора:
  request_vector    (x=energy, y=joy, z=complexity) — что хотел пользователь
  perception_vector (x=energy, y=joy, z=complexity) — как он услышал результат
  distance          — евклидово расстояние между векторами (0=идеально)

Чем меньше distance, тем точнее система попала в ожидание.
"""
import os
import json
from pydantic import BaseModel
from typing import Optional

FEEDBACK_FILE = os.path.join(os.path.dirname(__file__), "feedback_vector.json")


class VectorFeedbackItem(BaseModel):
    key:               str
    mode:              str
    request_vector:    dict   # {x, y, z}
    perception_vector: dict   # {x, y, z}
    distance:          float


def save_vector_feedback(item: VectorFeedbackItem) -> dict:
    entry = {
        "key":                item.key,
        "mode":               item.mode,
        "request_vector":     item.request_vector,
        "perception_vector":  item.perception_vector,
        "distance":           item.distance,
    }

    data = {"history": []}
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass

    data["history"].append(entry)

    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    n = len(data["history"])
    print(f"[VectorFeedback] #{n} saved — dist={item.distance:.1f} key={item.key} {item.mode}")
    return entry
