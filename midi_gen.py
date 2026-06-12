from mido import Message, MidiFile, MidiTrack, MetaMessage
import os
import time

OUTPUT_DIR = os.path.abspath("midi_output")

PROGRAM_PIANO     = 0
PROGRAM_STRINGS   = 48
PROGRAM_BASS      = 33
PROGRAM_SYNTH     = 81  # Lead 2 (Sawtooth) для Арпеджио

def make_track(name: str, program: int, channel: int, events: list, tpb: int) -> MidiTrack:
    track = MidiTrack()
    track.append(MetaMessage("track_name", name=name, time=0))
    track.append(Message("program_change", channel=channel, program=program, time=0))

    for event in events:
        if "notes" in event:
            notes   = event["notes"]
            dur     = int(event["duration"])
            vel     = int(event["velocity"])

            if not notes or vel == 0:
                track.append(Message("note_off", channel=channel, note=0, velocity=0, time=dur))
                continue

            for i, n in enumerate(notes):
                track.append(Message("note_on", channel=channel, note=int(n), velocity=vel, time=0))

            for i, n in enumerate(notes):
                t = dur if i == 0 else 0
                track.append(Message("note_off", channel=channel, note=int(n), velocity=vel, time=t))
        else:
            note = int(event["note"])
            dur  = int(event["duration"])
            vel  = int(event["velocity"])

            if note == 0 or vel == 0:
                track.append(Message("note_off", channel=channel, note=0, velocity=0, time=dur))
                continue

            track.append(Message("note_on",  channel=channel, note=note, velocity=vel, time=0))
            track.append(Message("note_off", channel=channel, note=note, velocity=vel, time=dur))

    return track

def create_midi(melody, chord_track=None, bass=None, arp=None, tpb=480, bpm=85, filename=None):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    mid = MidiFile(ticks_per_beat=tpb)

    tempo_track = MidiTrack()
    tempo_track.append(MetaMessage("set_tempo", tempo=int(60_000_000 / bpm), time=0))
    tempo_track.append(MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    mid.tracks.append(tempo_track)

    mid.tracks.append(make_track("Melody", PROGRAM_PIANO, channel=0, events=melody, tpb=tpb))

    if chord_track:
        mid.tracks.append(make_track("Chords", PROGRAM_STRINGS, channel=1, events=chord_track, tpb=tpb))

    if bass:
        mid.tracks.append(make_track("Bass", PROGRAM_BASS, channel=2, events=bass, tpb=tpb))

    if arp:
        mid.tracks.append(make_track("Arpeggio", PROGRAM_SYNTH, channel=3, events=arp, tpb=tpb))

    if filename is None:
        filename = f"track_{int(time.time())}.mid"

    path = os.path.join(OUTPUT_DIR, filename)
    mid.save(path)
    return path