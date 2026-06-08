import random
import os
import json

NOTE_MAP = {
    "C": 60, "C#": 61, "D": 62, "D#": 63,
    "E": 64, "F": 65, "F#": 66, "G": 67,
    "G#": 68, "A": 69, "A#": 70, "B": 71,
    "Bb": 70
}

SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10]
}

TPB = 480

WHOLE     = TPB * 4
HALF      = TPB * 2
QUARTER   = TPB
EIGHTH    = TPB // 2
SIXTEENTH = TPB // 4
DOTTED_Q  = int(TPB * 1.5)
DOTTED_E  = int(TPB * 0.75)

# ─── Functional harmony tables ────────────────────────────────────────────────
DEGREE_FUNCTION = {
    "minor": {0: "T", 1: "S", 2: "T", 3: "S", 4: "D", 5: "T", 6: "D"},
    "major": {0: "T", 1: "S", 2: "T", 3: "S", 4: "D", 5: "S", 6: "D"},
}

FUNCTION_GRAPH = {
    "T": ["T", "S", "D"],
    "S": ["S", "D", "T"],
    "D": ["T", "D"],
}

def _degrees_by_function(mode):
    return {
        fn: [d for d, f in DEGREE_FUNCTION[mode].items() if f == fn]
        for fn in ("T", "S", "D")
    }

def generate_progression(mode: str, length: int = 4) -> list:
    by_fn = _degrees_by_function(mode)
    deg_fn = DEGREE_FUNCTION[mode]
    result = [0]
    current_fn = "T"
    for _ in range(length - 2):
        next_fns = FUNCTION_GRAPH[current_fn]
        fn_weights = []
        for fn in next_fns:
            if fn == current_fn:
                fn_weights.append(0.5)
            elif next_fns.index(fn) > 0:
                fn_weights.append(2.0)
            else:
                fn_weights.append(1.0)
        next_fn = random.choices(next_fns, weights=fn_weights, k=1)[0]
        candidates = by_fn[next_fn]
        candidates = [d for d in candidates if d != result[-1]] or candidates
        result.append(random.choice(candidates))
        current_fn = next_fn
    result.append(random.choices([0, 2], weights=[4, 1], k=1)[0])
    return result

# ─── Rhythm atoms ──────────────────────────────────────────────────────────────
_RHYTHM_ATOMS_DENSE = [
    (SIXTEENTH, 0.10), (EIGHTH, 0.15), (DOTTED_E, 0.20), (QUARTER, 0.25),
]
_RHYTHM_ATOMS_SPARSE = [
    (QUARTER, 0.10), (DOTTED_Q, 0.15), (HALF, 0.20), (WHOLE, 0.30),
]
_RHYTHM_ATOMS_NORMAL = _RHYTHM_ATOMS_DENSE + _RHYTHM_ATOMS_SPARSE

def _generate_bar_rhythm(density: str, bar_ticks: int = TPB * 4) -> list:
    if density == "dense":
        atoms, rest_bias, synco_prob = _RHYTHM_ATOMS_DENSE, 0.18, 0.30
    elif density == "sparse":
        atoms, rest_bias, synco_prob = _RHYTHM_ATOMS_SPARSE, 0.40, 0.10
    else:
        atoms, rest_bias, synco_prob = _RHYTHM_ATOMS_NORMAL, 0.25, 0.20

    durations = [d for d, _ in atoms]
    weights   = [w for _, w in atoms]
    result = []
    remaining = bar_ticks

    while remaining > 0:
        valid = [(d, w) for d, w in zip(durations, weights) if d <= remaining]
        if not valid:
            result.append((remaining, True))
            break
        vd, vw = zip(*valid)
        dur = random.choices(vd, weights=vw, k=1)[0]
        is_beat = (bar_ticks - remaining) % QUARTER == 0
        if is_beat and random.random() < synco_prob and dur >= EIGHTH * 2:
            half = dur // 2
            result.append((half, True))
            result.append((half, False))
        else:
            result.append((dur, random.random() < rest_bias))
        remaining -= dur

    if result and result[0][1]:   result[0] = (result[0][0], False)
    if result and result[-1][1]:  result[-1] = (result[-1][0], False)
    return result

# ─── Chord / bass rhythms ──────────────────────────────────────────────────────
CHORD_RHYTHMS_LESS = [
    [(WHOLE, False)],
    [(DOTTED_Q, False), (DOTTED_Q, True), (HALF, True)],
    [(HALF, False), (HALF, True)],
]
CHORD_RHYTHMS_MORE = [
    [(HALF, False), (HALF, False)],
    [(DOTTED_Q, False), (EIGHTH, True), (HALF, False)],
    [(HALF, False), (QUARTER, False), (QUARTER, True)],
]
CHORD_RHYTHMS_NORMAL = CHORD_RHYTHMS_LESS + CHORD_RHYTHMS_MORE

BASS_PATTERNS = [
    [{"note": "root",  "duration": QUARTER,  "velocity": 90},
     {"note": "rest",  "duration": EIGHTH,   "velocity": 0},
     {"note": "root",  "duration": EIGHTH,   "velocity": 75},
     {"note": "fifth", "duration": QUARTER,  "velocity": 80},
     {"note": "rest",  "duration": QUARTER,  "velocity": 0}],
    [{"note": "root",  "duration": HALF,     "velocity": 85},
     {"note": "root",  "duration": QUARTER,  "velocity": 85},
     {"note": "root",  "duration": QUARTER,  "velocity": 75}],
    [{"note": "root",  "duration": DOTTED_Q, "velocity": 95},
     {"note": "fifth", "duration": EIGHTH,   "velocity": 80},
     {"note": "rest",  "duration": QUARTER,  "velocity": 0},
     {"note": "root",  "duration": QUARTER,  "velocity": 85}],
    [{"note": "root",  "duration": WHOLE,    "velocity": 90}],
    [{"note": "rest",  "duration": EIGHTH,   "velocity": 0},
     {"note": "root",  "duration": DOTTED_Q, "velocity": 92},
     {"note": "fifth", "duration": EIGHTH,   "velocity": 78},
     {"note": "root",  "duration": QUARTER,  "velocity": 85},
     {"note": "rest",  "duration": EIGHTH,   "velocity": 0}],
    [{"note": "root",  "duration": QUARTER,  "velocity": 88},
     {"note": "rest",  "duration": QUARTER,  "velocity": 0},
     {"note": "root",  "duration": QUARTER,  "velocity": 82},
     {"note": "rest",  "duration": QUARTER,  "velocity": 0}],
    [{"note": "root",  "duration": HALF,     "velocity": 90},
     {"note": "third", "duration": QUARTER,  "velocity": 75},
     {"note": "fifth", "duration": QUARTER,  "velocity": 80}],
    [{"note": "root",  "duration": HALF,     "velocity": 92},
     {"note": "fifth", "duration": HALF,     "velocity": 82}],
]

# ─── Scale / chord helpers ──────────────────────────────────────────────────────
def build_scale_full(root="C", mode="minor", octaves=3, base_octave=4):
    root_midi = NOTE_MAP[root] + (base_octave - 4) * 12
    intervals = SCALES[mode]
    notes = []
    for oct in range(octaves):
        for interval in intervals:
            notes.append(root_midi + oct * 12 + interval)
    return notes

def build_chord(root_midi, mode, degree, min_interval=0):
    intervals = SCALES[mode]
    n = len(intervals)
    def scale_note(deg):
        return root_midi + intervals[deg % n] + (deg // n) * 12
    notes = [scale_note(degree), scale_note(degree + 2), scale_note(degree + 4)]
    if min_interval > 0:
        for i in range(1, len(notes)):
            while notes[i] - notes[i-1] < min_interval:
                notes[i] += 12
    return notes

def get_progression(root="C", mode="minor", min_interval=0):
    root_midi = NOTE_MAP[root] + (3 - 4) * 12
    length = random.choices([3, 4, 4, 4, 6], weights=[1, 4, 4, 4, 1], k=1)[0]
    degrees = generate_progression(mode, length=length)
    chords = [build_chord(root_midi, mode, d, min_interval=min_interval) for d in degrees]
    return chords, degrees

def smooth_step(current, scale_notes, max_jump=3):
    if current not in scale_notes:
        current = min(scale_notes, key=lambda x: abs(x - current))
    idx = scale_notes.index(current)
    candidates, weights = [], []
    for i, note in enumerate(scale_notes):
        dist = abs(i - idx)
        if dist == 0 or dist > max_jump:
            continue
        candidates.append(note)
        weights.append(max_jump - dist + 1)
    return random.choices(candidates, weights=weights, k=1)[0] if candidates else current

def chord_tone_or_passing(current, chord, scale_notes, chord_prob=0.55):
    lo, hi = scale_notes[0], scale_notes[-1]
    def clamp(n):
        while n < lo: n += 12
        while n > hi: n -= 12
        return n
    if random.random() < chord_prob:
        clamped = [clamp(n) for n in chord]
        nearby = [n for n in clamped if abs(n - current) <= 12] or clamped
        dists = [1 / (abs(n - current) + 1) for n in nearby]
        return random.choices(nearby, weights=dists, k=1)[0]
    else:
        return smooth_step(current, scale_notes)

# ─── Track generators ───────────────────────────────────────────────────────────
def generate_melody(scale_notes, chords, bars=8, density="normal", variety="normal"):
    melody = []
    melody_scale = [n for n in scale_notes if 60 <= n <= 84] or scale_notes
    root_candidates = [melody_scale[0], melody_scale[2]] if len(melody_scale) > 2 else [melody_scale[0]]
    current = random.choice(root_candidates)
    recent_notes = []
    max_jump_base = 5 if variety == "more" else (2 if variety == "less" else 3)
    chord_prob_base = 0.40 if variety == "more" else (0.70 if variety == "less" else 0.55)
    leap_prob = 0.20 if variety == "more" else (0.04 if variety == "less" else 0.12)
    motif_notes = []
    motif_captured = False
    motif_replay_prob = 0.30

    for bar in range(bars):
        chord = chords[bar % len(chords)]
        rhythm = _generate_bar_rhythm(density)
        replay_motif = (motif_captured and bar > 0 and random.random() < motif_replay_prob)
        motif_pos = 0

        for slot_idx, (duration, is_rest) in enumerate(rhythm):
            if is_rest:
                melody.append({"note": 0, "duration": duration, "velocity": 0})
                continue
            if replay_motif and motif_pos < len(motif_notes):
                original_root = chords[0][0]
                current_root  = chord[0]
                transposed = motif_notes[motif_pos] + (current_root - original_root)
                lo, hi = melody_scale[0], melody_scale[-1]
                while transposed < lo: transposed += 12
                while transposed > hi: transposed -= 12
                note = transposed
                motif_pos += 1
                current = note
            else:
                if len(recent_notes) >= 3 and len(set(recent_notes[-3:])) == 1:
                    note = smooth_step(current, melody_scale, max_jump=max_jump_base + 1)
                else:
                    note = chord_tone_or_passing(current, chord, melody_scale, chord_prob=chord_prob_base)
                if random.random() < leap_prob and len(melody_scale) > 5:
                    leap = random.choice(melody_scale)
                    if abs(leap - current) in (5, 7, 12):
                        note = leap
                current = note
            if bar == 0 and not motif_captured:
                motif_notes.append(note)
                if len(motif_notes) >= random.randint(2, 3):
                    motif_captured = True
            recent_notes.append(note)
            if len(recent_notes) > 8: recent_notes.pop(0)
            base_vel = 82
            vel = base_vel + random.randint(-10, 12)
            melody.append({"note": note, "duration": duration, "velocity": max(60, min(100, vel))})

    return melody

def generate_chords_track(chords, bars=8, density="normal"):
    chord_track = []
    if density == "less":
        rhythms, weights = CHORD_RHYTHMS_LESS, None
    elif density == "more":
        rhythms, weights = CHORD_RHYTHMS_MORE, None
    else:
        rhythms = CHORD_RHYTHMS_NORMAL
        weights = [3, 3, 2, 2, 2, 1, 1][:len(rhythms)]
    for bar in range(bars):
        chord = chords[bar % len(chords)]
        rhythm = random.choices(rhythms, weights=weights, k=1)[0] if weights else random.choice(rhythms)
        for duration, is_rest in rhythm:
            if is_rest:
                chord_track.append({"notes": [], "duration": duration, "velocity": 0})
            else:
                chord_track.append({"notes": chord, "duration": duration, "velocity": random.randint(50, 65)})
    return chord_track

def generate_bass(chords, bars=8, activity="normal"):
    bass = []
    last_idx = None
    if activity == "less":   pool = [3, 5]
    elif activity == "more": pool = [0, 2, 4, 6, 7]
    else:                    pool = list(range(len(BASS_PATTERNS)))
    for bar in range(bars):
        chord = chords[bar % len(chords)]
        root  = chord[0] - 12
        fifth = chord[2] - 12 if len(chord) > 2 else root + 7
        third = chord[1] - 12 if len(chord) > 1 else root + 4
        available = [i for i in pool if i != last_idx] or pool
        idx = random.choice(available)
        last_idx = idx
        for step in BASS_PATTERNS[idx]:
            n = {"root": root, "fifth": fifth, "third": third}.get(step["note"], 0)
            bass.append({"note": n, "duration": step["duration"], "velocity": step["velocity"]})
    return bass

# ─── Vector → music parameters ────────────────────────────────────────────────
def vector_to_music_params(energy: int, joy: int, complexity: int) -> dict:
    """
    Convert 3D intent vector (-100..+100 each) to generative music parameters.

    energy    → BPM, velocity, bass activity
    joy       → mode (minor=-100, major=+100), chord colour
    complexity → melody density/variety, chord density, rhythm intricacy
    """
    # Normalize to -1..+1
    e = energy / 100.0
    j = joy / 100.0
    c = complexity / 100.0

    # BPM: energy maps 60-170
    bpm_base = int(115 + e * 55)  # -100→60, 0→115, +100→170
    bpm_base = max(60, min(170, bpm_base))

    # Mode: joy < -0.2 → minor, joy > 0.2 → major, else coin flip weighted
    if j < -0.2:
        mode = "minor"
    elif j > 0.2:
        mode = "major"
    else:
        mode = random.choices(["minor", "major"], weights=[0.5 - j * 0.25, 0.5 + j * 0.25], k=1)[0]

    # Melody density: high complexity → dense; low complexity → sparse
    if c > 0.35:
        melody_density = "dense"
    elif c < -0.35:
        melody_density = "sparse"
    else:
        melody_density = "normal"

    # Melody variety: high complexity → more variety; very low → less variety
    if c > 0.50:
        melody_variety = "more"
    elif c < -0.50:
        melody_variety = "less"
    else:
        melody_variety = "normal"

    # Bass activity: high energy → more bass
    if e > 0.45:
        bass_activity = "more"
    elif e < -0.45:
        bass_activity = "less"
    else:
        bass_activity = "normal"

    # Chord density: complexity → chord frequency
    if c > 0.40:
        chord_density = "more"
    elif c < -0.40:
        chord_density = "less"
    else:
        chord_density = "normal"

    # Chord min interval: very low joy → darker, tighter voicings
    chord_min_interval = 0 if j > -0.5 else 2

    return {
        "bpm":                bpm_base,
        "mode":               mode,
        "melody_density":     melody_density,
        "melody_variety":     melody_variety,
        "bass_activity":      bass_activity,
        "chord_density":      chord_density,
        "chord_min_interval": chord_min_interval,
    }

# ─── Feedback-trained correction layer ────────────────────────────────────────
_DEFAULTS = {
    "keys": ["C", "D", "E", "F", "G", "A", "Bb"],
    "k_weights": None,
    "bpm_offset": 0,
    "chord_min_interval": 0,
}

def get_trained_corrections():
    """
    Read feedback_vector.json and compute correction deltas.
    Returns dict of corrections to overlay on vector-derived params.
    """
    fb_path = os.path.join(os.path.dirname(__file__), "feedback_vector.json")
    if not os.path.exists(fb_path):
        return dict(_DEFAULTS)
    try:
        with open(fb_path, "r", encoding="utf-8") as f:
            history = json.load(f).get("history", [])
    except Exception:
        return dict(_DEFAULTS)
    if not history:
        return dict(_DEFAULTS)

    n = len(history)
    DECAY = 0.85
    weights_by_pos = [DECAY ** (n - 1 - i) for i in range(n)]

    keys_pool = _DEFAULTS["keys"]
    key_scores = {k: 0.0 for k in keys_pool}
    bpm_weighted_sum = 0.0
    bpm_weight_total = 0.0
    # Accumulate error vectors (request - perception): if error is large, adjust
    energy_errors = []
    joy_errors = []
    complexity_errors = []

    for i, item in enumerate(history):
        w = weights_by_pos[i]
        req = item.get("request_vector", {})
        perc = item.get("perception_vector", {})
        dist = item.get("distance", 0)

        # Error = what user wanted minus what they heard
        # If energy was requested at +80 but heard at +40, we need to increase energy
        ex = req.get("x", 0) - perc.get("x", 0)
        ey = req.get("y", 0) - perc.get("y", 0)
        ez = req.get("z", 0) - perc.get("z", 0)
        energy_errors.append((ex * w, w))
        joy_errors.append((ey * w, w))
        complexity_errors.append((ez * w, w))

        k = item.get("key")
        # Reward keys from small-distance sessions
        if k in key_scores:
            liked = dist < 80  # small distance = user perceived what they wanted
            key_scores[k] += w * (2.0 if liked else -0.5)

    # BPM offset from energy error
    if energy_errors:
        total_w = sum(w for _, w in energy_errors)
        avg_energy_err = sum(v for v, _ in energy_errors) / total_w if total_w > 0 else 0
        # Energy error of +10 → ~3 BPM increase
        bpm_offset = int(avg_energy_err * 0.3)
        bpm_offset = max(-20, min(20, bpm_offset))
    else:
        bpm_offset = 0

    min_ks = min(key_scores.values())
    adj_ks = {k: v - min_ks + 0.1 for k, v in key_scores.items()}

    print(f"[Train-Vector] n={n} bpm_offset={bpm_offset:+d}")
    return {
        "keys":      list(adj_ks.keys()),
        "k_weights": list(adj_ks.values()),
        "bpm_offset": bpm_offset,
        "chord_min_interval": 0,
    }

# ─── Main entry point ──────────────────────────────────────────────────────────
def generate_music_plan(energy: int = 0, joy: int = 0, complexity: int = 0,
                        bpm: int = None, bars: int = 8):
    """
    Generate music from a 3D intent vector.
    energy, joy, complexity: -100..+100
    bpm: override BPM (if None, derived from energy)
    """
    # Step 1: vector → base params
    vparams = vector_to_music_params(energy, joy, complexity)

    # Step 2: feedback corrections
    corrections = get_trained_corrections()

    # Step 3: merge
    key = random.choices(corrections["keys"], weights=corrections["k_weights"], k=1)[0]
    mode = vparams["mode"]

    # BPM: vector-derived, possibly user-overridden, plus feedback offset
    final_bpm = bpm if bpm is not None else vparams["bpm"]
    final_bpm = max(55, min(180, final_bpm + corrections["bpm_offset"]))

    chord_min_interval = max(vparams["chord_min_interval"], corrections["chord_min_interval"])

    scale_notes = build_scale_full(key, mode, octaves=3, base_octave=3)
    chords, degrees = get_progression(key, mode, min_interval=chord_min_interval)

    return {
        "energy":      energy,
        "joy":         joy,
        "complexity":  complexity,
        "key":         key,
        "mode":        mode,
        "bpm":         final_bpm,
        "scale":       scale_notes,
        "chords":      chords,
        "degrees":     degrees,
        "melody":      generate_melody(scale_notes, chords, bars=bars,
                                       density=vparams["melody_density"],
                                       variety=vparams["melody_variety"]),
        "chord_track": generate_chords_track(chords, bars=bars,
                                             density=vparams["chord_density"]),
        "bass":        generate_bass(chords, bars=bars,
                                     activity=vparams["bass_activity"]),
        "tpb":         TPB,
    }
