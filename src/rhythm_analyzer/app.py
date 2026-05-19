from __future__ import annotations

import hashlib
import json
import math
import os
import queue
import random
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext
from typing import Any

import imageio_ffmpeg
import numpy as np
from librosa.beat import beat_track
from librosa.core import frames_to_time, get_duration, load
from librosa.feature import tempo as estimate_tempo
from librosa.onset import onset_strength

APP_NAME = "Rhythm Analyzer"
APP_ID = "DiscoRhythmAnalyzer"
WINDOW_WIDTH = 680
WINDOW_HEIGHT = 600
TARGET_SAMPLE_RATE = 22_050
MAX_ANALYSIS_SECONDS = 15 * 60
MAX_FILE_SIZE_MB = 250
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a"}
HOP_LENGTH = 512
LOCAL_TEMPO_WINDOW_SECONDS = 8.0
TEMPO_MAP_STEP_SECONDS = 4.0
TEMPO_CHANGE_THRESHOLD_BPM = 5.0
MIN_TEMPO_SEGMENT_SECONDS = 8.0
IMPORT_SONGS_PATH_ENV_VAR = "IMPORT_SONGS_PATH"
OGG_AUDIO_FILENAME = "audio.ogg"
META_FILENAME = "Meta.JSON"
FOLDER_NAME_MAX_LENGTH = 120

BG_COLOR = "#070710"
PANEL_COLOR = "#101022"
PANEL_BORDER = "#38fff3"
TEXT_COLOR = "#ffffff"
MUTED_TEXT = "#c6d3ff"
BTN_BG = "#17172f"
BTN_FG = "#38fff3"
BTN_ACTIVE = "#ff4fd8"
PINK = "#ff4fd8"
GOLD = "#ffd166"
LIME = "#a7ff4f"
VIOLET = "#8b5cf6"
CYAN = "#38fff3"


LANGUAGES: dict[str, dict[str, Any]] = {
    "ru": {
        "title": "DISCO RHYTHM ANALYZER",
        "btn": "ВЫБРАТЬ ТРЕК",
        "placeholder": "Выбери аудиофайл для анализа",
        "loading": "Анализирую...",
        "error": "Ошибка",
        "error_load": "Не удалось проанализировать файл:\n",
        "unsupported": "Поддерживаются только: {extensions}",
        "too_large": "Файл больше лимита {max_mb} MB.",
        "empty": "Файл пустой.",
        "no_audio": "Не удалось найти аудиоданные.",
        "file": "Файл",
        "size": "Размер",
        "tempo": "Темп",
        "pattern": "Паттерн",
        "confidence": "Уверен.",
        "stability": "Стабильность",
        "duration": "Анализ",
        "duration_note": "первые {duration}",
        "samplerate": "Частота",
        "overall_bpm": "Основной BPM",
        "tempo_map": "Изменения BPM",
        "no_changes": "существенных изменений не найдено",
        "change_count": "Точек изменения",
        "copy_json": "КОПИРОВАТЬ JSON",
        "json_copied": "JSON скопирован",
        "json_unavailable": "Сначала проанализируй трек.",
        "set_import_folder": "УСТАНОВИТЬ ПАПКУ",
        "save_import": "СОХРАНИТЬ ИМПОРТ",
        "import_folder_not_set": "Папка импорта не задана",
        "import_folder_selected": "Папка импорта: {path}",
        "import_success": "Импорт сохранен в:\n{path}",
        "import_error": "Не удалось сохранить импорт:\n{error}",
        "patterns": {
            "slow": "медленный балладный",
            "medium": "средний поп/рок",
            "fast": "быстрый джаз/рок",
            "unknown": "нет четкого ритма",
        },
        "stability_levels": {
            "very_stable": "очень стабильный",
            "stable": "стабильный",
            "moderate": "умеренно нестабильный",
            "unstable": "нестабильный",
            "no_data": "недостаточно данных",
        },
    },
    "en": {
        "title": "DISCO RHYTHM ANALYZER",
        "btn": "CHOOSE TRACK",
        "placeholder": "Choose an audio file to analyze",
        "loading": "Analyzing...",
        "error": "Error",
        "error_load": "Failed to analyze file:\n",
        "unsupported": "Supported formats only: {extensions}",
        "too_large": "File is larger than the {max_mb} MB limit.",
        "empty": "The selected file is empty.",
        "no_audio": "No audio samples could be decoded.",
        "file": "File",
        "size": "Size",
        "tempo": "Tempo",
        "pattern": "Pattern",
        "confidence": "Confidence",
        "stability": "Stability",
        "duration": "Analyzed",
        "duration_note": "first {duration}",
        "samplerate": "Sample rate",
        "overall_bpm": "Primary BPM",
        "tempo_map": "BPM changes",
        "no_changes": "no significant changes found",
        "change_count": "Change points",
        "copy_json": "COPY JSON",
        "json_copied": "JSON copied",
        "json_unavailable": "Analyze a track first.",
        "set_import_folder": "SET IMPORT FOLDER",
        "save_import": "EXPORT IMPORT",
        "import_folder_not_set": "Import folder not configured",
        "import_folder_selected": "Import folder: {path}",
        "import_success": "Saved imported song to:\n{path}",
        "import_error": "Failed to save imported song:\n{error}",
        "patterns": {
            "slow": "slow ballad",
            "medium": "mid pop/rock",
            "fast": "fast jazz/rock",
            "unknown": "no clear rhythm",
        },
        "stability_levels": {
            "very_stable": "very stable",
            "stable": "stable",
            "moderate": "moderately unstable",
            "unstable": "unstable",
            "no_data": "insufficient data",
        },
    },
}


@dataclass(frozen=True)
class Particle:
    x: float
    y: float
    radius: float
    speed: float
    angle: float
    color: str

    @classmethod
    def create(cls, width: int, height: int) -> Particle:
        return cls(
            x=random.uniform(0, width),
            y=random.uniform(0, height),
            radius=random.uniform(1.0, 3.6),
            speed=random.uniform(0.35, 1.15),
            angle=random.uniform(0, 2 * math.pi),
            color=random.choice([PINK, GOLD, LIME, VIOLET, CYAN]),
        )

    def move(self, width: int, height: int) -> Particle:
        x = self.x + math.cos(self.angle) * self.speed
        y = self.y + math.sin(self.angle) * self.speed
        if x < -8 or x > width + 8 or y < -8 or y > height + 8:
            return Particle.create(width, height)
        return Particle(x, y, self.radius, self.speed, self.angle, self.color)


@dataclass(frozen=True)
class AnalysisMessage:
    job_id: int
    lang: str
    ok: bool
    payload: str
    game_json: str = ""


@dataclass(frozen=True)
class TempoSegment:
    start_seconds: float
    end_seconds: float
    bpm: float


@dataclass(frozen=True)
class AnalysisResult:
    summary: str
    game_json: str


def resource_path(relative_path: str) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base_path / relative_path


def setup_ffmpeg_path() -> None:
    ffmpeg_exe = Path(imageio_ffmpeg.get_ffmpeg_exe())
    ffmpeg_dir = str(ffmpeg_exe.parent)
    path_parts = os.environ.get("PATH", "").split(os.pathsep)

    if ffmpeg_dir not in path_parts:
        os.environ["PATH"] = os.pathsep.join(part for part in [*path_parts, ffmpeg_dir] if part)


def set_windows_app_id() -> None:
    if os.name != "nt":
        return

    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        return


def clean_display_name(name: str, max_length: int = 74) -> str:
    cleaned = "".join(char if char.isprintable() else "?" for char in name)
    if len(cleaned) <= max_length:
        return cleaned
    return f"{cleaned[: max_length - 3]}..."


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def get_default_import_root() -> Path | None:
    env_value = os.environ.get(IMPORT_SONGS_PATH_ENV_VAR, "")
    if not env_value:
        return None

    path = Path(env_value).expanduser()
    return path if path.is_dir() else None


def sanitize_folder_name(name: str, max_length: int = FOLDER_NAME_MAX_LENGTH) -> str:
    invalid_chars = '<>:"/\\|?*'
    cleaned = "".join(
        "_" if char in invalid_chars or ord(char) < 32 else char
        for char in name
    ).strip()
    cleaned = cleaned.rstrip(". ")
    if not cleaned:
        cleaned = "song"
    return cleaned[:max_length]


def unique_import_folder(root: Path, base_name: str) -> Path:
    candidate = root / sanitize_folder_name(base_name)
    if not candidate.exists():
        return candidate

    for index in range(2, 1000):
        candidate = root / f"{sanitize_folder_name(base_name)} ({index})"
        if not candidate.exists():
            return candidate

    raise RuntimeError("Unable to generate a unique import folder name.")


def convert_audio_to_ogg(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".ogg":
        shutil.copy2(source, target)
        return

    ffmpeg_exe = Path(imageio_ffmpeg.get_ffmpeg_exe())
    command = [
        str(ffmpeg_exe),
        "-y",
        "-i",
        str(source),
        "-vn",
        "-c:a",
        "libvorbis",
        "-ar",
        str(TARGET_SAMPLE_RATE),
        "-ac",
        "2",
        str(target),
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg failed to convert audio.")


def create_import_package(import_root: Path, source_file: Path, game_json: str) -> Path:
    import_root.mkdir(parents=True, exist_ok=True)
    song_folder = unique_import_folder(import_root, source_file.stem)
    audio_target = song_folder / OGG_AUDIO_FILENAME
    meta_target = song_folder / META_FILENAME

    song_folder.mkdir(parents=True, exist_ok=False)
    try:
        convert_audio_to_ogg(source_file, audio_target)
        meta = json.loads(game_json)
        meta["audioFileName"] = OGG_AUDIO_FILENAME
        meta["originalAudioFilePath"] = source_file.resolve().as_posix()
        meta_target.write_text(json.dumps(meta, indent=4), encoding="utf-8")
        return song_folder
    except Exception:
        shutil.rmtree(song_folder, ignore_errors=True)
        raise


def file_md5(file_path: Path) -> str:
    digest = hashlib.md5()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def uint32_from_digest(hex_digest: str, offset: int) -> int:
    raw = bytes.fromhex(hex_digest)
    return int.from_bytes(raw[offset : offset + 4], byteorder="little", signed=False)


def format_timestamp(seconds: float) -> str:
    total_seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def format_duration_limit(seconds: int, lang: str) -> str:
    if seconds % 60 == 0:
        minutes = seconds // 60
        return f"{minutes} мин." if lang == "ru" else f"{minutes} min"

    return f"{seconds} сек." if lang == "ru" else f"{seconds} sec"


def validate_audio_file(file_path: Path, lang: str) -> int:
    t = LANGUAGES[lang]

    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        extensions = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(t["unsupported"].format(extensions=extensions))

    size_bytes = file_path.stat().st_size
    if size_bytes == 0:
        raise ValueError(t["empty"])
    if size_bytes > MAX_FILE_SIZE_BYTES:
        raise ValueError(t["too_large"].format(max_mb=MAX_FILE_SIZE_MB))

    return size_bytes


def scalar_float(value: object) -> float:
    values = np.asarray(value, dtype=float).reshape(-1)
    if values.size == 0 or not np.isfinite(values[0]):
        return 0.0
    return float(values[0])


def normalize_bpm_to_reference(local_bpm: np.ndarray, reference_bpm: float) -> np.ndarray:
    local_bpm = np.where(np.isfinite(local_bpm) & (local_bpm > 0), local_bpm, reference_bpm)
    if reference_bpm <= 0:
        return local_bpm

    candidates = np.vstack((local_bpm / 2, local_bpm, local_bpm * 2))
    distances = np.abs(candidates - reference_bpm)
    best = np.nanargmin(distances, axis=0)
    return candidates[best, np.arange(local_bpm.size)]


def median_bpm(segment: dict[str, Any]) -> float:
    return float(np.median(segment["bpms"]))


def merge_segments(target: dict[str, Any], source: dict[str, Any]) -> None:
    target["start"] = min(target["start"], source["start"])
    target["end"] = max(target["end"], source["end"])
    target["bpms"].extend(source["bpms"])


def merge_similar_tempo_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not segments:
        return segments

    merged = [segments[0]]
    for segment in segments[1:]:
        if abs(median_bpm(segment) - median_bpm(merged[-1])) < TEMPO_CHANGE_THRESHOLD_BPM:
            merge_segments(merged[-1], segment)
        else:
            merged.append(segment)

    return merged


def merge_short_tempo_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index = 0
    while len(segments) > 1 and index < len(segments):
        segment = segments[index]
        if segment["end"] - segment["start"] >= MIN_TEMPO_SEGMENT_SECONDS:
            index += 1
            continue

        if index == 0:
            merge_segments(segments[1], segment)
            del segments[0]
            continue

        if index == len(segments) - 1:
            merge_segments(segments[index - 1], segment)
            del segments[index]
            continue

        previous_delta = abs(median_bpm(segment) - median_bpm(segments[index - 1]))
        next_delta = abs(median_bpm(segment) - median_bpm(segments[index + 1]))

        if previous_delta <= next_delta:
            merge_segments(segments[index - 1], segment)
            del segments[index]
        else:
            merge_segments(segments[index + 1], segment)
            del segments[index]

    return merge_similar_tempo_segments(segments)


def build_tempo_segments(
    local_bpm: np.ndarray,
    global_bpm: float,
    sr: int,
    duration_seconds: float,
) -> tuple[TempoSegment, ...]:
    bpm_curve = np.asarray(local_bpm, dtype=float).reshape(-1)
    finite_mask = np.isfinite(bpm_curve) & (bpm_curve > 0)
    if not np.any(finite_mask):
        return ()

    bpm_curve = normalize_bpm_to_reference(bpm_curve, global_bpm)
    frame_seconds = HOP_LENGTH / sr
    frames_per_window = max(1, int(round(TEMPO_MAP_STEP_SECONDS / frame_seconds)))
    raw_segments: list[dict[str, Any]] = []

    for start_frame in range(0, bpm_curve.size, frames_per_window):
        end_frame = min(bpm_curve.size, start_frame + frames_per_window)
        values = bpm_curve[start_frame:end_frame]
        values = values[np.isfinite(values) & (values > 0)]
        if values.size == 0:
            continue

        start = start_frame * frame_seconds
        end = min(end_frame * frame_seconds, duration_seconds)
        window_bpm = float(np.median(values))

        if (
            raw_segments
            and abs(window_bpm - median_bpm(raw_segments[-1])) < TEMPO_CHANGE_THRESHOLD_BPM
        ):
            raw_segments[-1]["end"] = end
            raw_segments[-1]["bpms"].append(window_bpm)
        else:
            raw_segments.append({"start": start, "end": end, "bpms": [window_bpm]})

    raw_segments = merge_short_tempo_segments(raw_segments)

    return tuple(
        TempoSegment(
            start_seconds=float(segment["start"]),
            end_seconds=float(segment["end"]),
            bpm=round(median_bpm(segment), 1),
        )
        for segment in raw_segments
    )


def calc_tempo_map(y: np.ndarray, sr: int, global_bpm: float) -> tuple[TempoSegment, ...]:
    onset_env = onset_strength(y=y, sr=sr, hop_length=HOP_LENGTH)
    if onset_env.size < 2 or float(np.max(onset_env)) <= 1e-6:
        return ()

    local_bpm = estimate_tempo(
        onset_envelope=onset_env,
        sr=sr,
        hop_length=HOP_LENGTH,
        aggregate=None,
        ac_size=LOCAL_TEMPO_WINDOW_SECONDS,
        max_tempo=260,
    )
    duration = get_duration(y=y, sr=sr)
    return build_tempo_segments(local_bpm, global_bpm, sr, duration)


def format_tempo_changes(segments: tuple[TempoSegment, ...], lang: str) -> list[str]:
    t = LANGUAGES[lang]
    if not segments:
        return [f"{t['tempo_map']}: {t['no_changes']}"]

    lines = [f"{t['tempo_map']}:"]
    for segment in segments:
        lines.append(f"  {format_timestamp(segment.start_seconds)} -> {segment.bpm:.1f} BPM")

    change_count = max(0, len(segments) - 1)
    lines.append(f"{t['change_count']}: {change_count}")
    return lines


def primary_bpm(segments: tuple[TempoSegment, ...], fallback_bpm: float) -> float:
    if not segments:
        return fallback_bpm

    dominant = max(segments, key=lambda segment: segment.end_seconds - segment.start_seconds)
    return dominant.bpm


def make_game_json(
    file_path: Path,
    file_hash: str,
    primary_tempo: float,
    tempo_segments: tuple[TempoSegment, ...],
    beat_frames: np.ndarray,
    sr: int,
    analyzed_duration: float,
    source_duration: float,
) -> str:
    beat_times = frames_to_time(beat_frames, sr=sr, hop_length=HOP_LENGTH)
    first_beat = float(beat_times[0]) if beat_times.size else 0.0
    last_beat = float(beat_times[-1]) if beat_times.size else analyzed_duration
    end_offset = max(0.0, source_duration - last_beat)

    game_data = {
        "version": 1,
        "uniqueId": uint32_from_digest(file_hash, 0),
        "songName": file_path.stem,
        "performedBy": [],
        "writtenBy": [],
        "seed": uint32_from_digest(file_hash, 4),
        "tempo": int(round(primary_tempo)),
        "customTempoSections": [
            {
                "tempo": int(round(segment.bpm)),
                "startAbsoluteTime": float(segment.start_seconds),
            }
            for segment in tempo_segments[1:]
        ],
        "beatOffset": int(round(first_beat * 1000)),
        "startSongOffset": first_beat,
        "endSongOffset": end_offset,
        "uEAssetName": file_path.stem,
        "originalAudioFileHash": file_hash,
        "originalAudioFilePath": file_path.resolve().as_posix(),
    }

    return json.dumps(game_data, indent=4)


def calc_rhythm_stability(beat_frames: np.ndarray, sr: int, lang: str) -> tuple[float, str]:
    beat_times = frames_to_time(beat_frames, sr=sr, hop_length=HOP_LENGTH)
    levels = LANGUAGES[lang]["stability_levels"]

    if len(beat_times) < 2:
        return 0.0, levels["no_data"]

    intervals_ms = np.diff(beat_times) * 1000
    std = float(np.std(intervals_ms))

    if std < 10:
        label = levels["very_stable"]
    elif std < 30:
        label = levels["stable"]
    elif std < 60:
        label = levels["moderate"]
    else:
        label = levels["unstable"]

    return round(std, 1), label


def classify_tempo(tempo: float, beat_count: int, lang: str) -> tuple[str, float]:
    patterns = LANGUAGES[lang]["patterns"]

    if tempo <= 0 or beat_count < 2:
        return patterns["unknown"], 0.0

    if tempo < 80:
        confidence = 0.55 + min(0.45, (80 - tempo) / 80 * 0.45)
        return patterns["slow"], confidence
    if tempo < 120:
        confidence = 0.55 + (1 - abs(tempo - 100) / 20) * 0.45
        return patterns["medium"], max(0.55, min(1.0, confidence))

    confidence = 0.55 + min(0.45, (tempo - 120) / 80 * 0.45)
    return patterns["fast"], confidence


def analyze_audio_result(file_path: str, lang: str) -> AnalysisResult:
    t = LANGUAGES[lang]
    path = Path(file_path)
    size_bytes = validate_audio_file(path, lang)
    original_hash = file_md5(path)

    y, sr = load(
        str(path),
        sr=TARGET_SAMPLE_RATE,
        mono=True,
        duration=MAX_ANALYSIS_SECONDS,
    )

    if y.size == 0:
        raise ValueError(t["no_audio"])

    tempo_raw, beat_frames = beat_track(y=y, sr=sr, hop_length=HOP_LENGTH)
    tempo = scalar_float(tempo_raw)
    beat_frames = np.asarray(beat_frames)
    cv, stability = calc_rhythm_stability(beat_frames, sr, lang)
    tempo_segments = calc_tempo_map(y, sr, tempo)
    headline_bpm = primary_bpm(tempo_segments, tempo)
    duration = get_duration(y=y, sr=sr)
    duration_text = f"{duration:.1f} sec"

    try:
        source_duration = get_duration(path=str(path))
    except Exception:
        source_duration = duration

    if source_duration > duration + 0.25:
        limit = format_duration_limit(MAX_ANALYSIS_SECONDS, lang)
        duration_text += f" ({t['duration_note'].format(duration=limit)})"

    summary_lines = [
        f"{t['file']}:        {clean_display_name(path.name)}",
        f"{t['size']}:        {format_file_size(size_bytes)}",
        f"{t['overall_bpm']}: {headline_bpm:.1f} BPM",
        f"{t['stability']}:   {stability} (+/-{cv} ms)",
        f"{t['beatOffset']}:    {format_timestamp(float(beat_frames[0] * HOP_LENGTH / sr))}",
        f"{t['duration']}:    {duration_text}",
        f"{t['samplerate']}:  {sr} Hz",
        "",
        *format_tempo_changes(tempo_segments, lang),
    ]

    game_json = make_game_json(
        file_path=path,
        file_hash=original_hash,
        primary_tempo=headline_bpm,
        tempo_segments=tempo_segments,
        beat_frames=beat_frames,
        sr=sr,
        analyzed_duration=duration,
        source_duration=source_duration,
    )

    return AnalysisResult(summary="\n".join(summary_lines), game_json=game_json)


def analyze_audio_file(file_path: str, lang: str) -> str:
    return analyze_audio_result(file_path, lang).summary


def build_ui(root: tk.Tk) -> None:
    state = {
        "lang": "en",
        "busy": False,
        "job_id": 0,
        "game_json": "",
        "import_root": get_default_import_root(),
        "last_file_path": "",
    }
    analysis_queue: queue.Queue[AnalysisMessage] = queue.Queue()
    particles = [Particle.create(WINDOW_WIDTH, WINDOW_HEIGHT) for _ in range(95)]

    canvas = tk.Canvas(
        root,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        bg=BG_COLOR,
        highlightthickness=0,
    )
    canvas.place(x=0, y=0)

    lang_var = tk.StringVar(value="EN")
    limit_var = tk.StringVar()
    import_path_var = tk.StringVar()
    initial_result = LANGUAGES[state["lang"]]["placeholder"]

    def t() -> dict[str, Any]:
        return LANGUAGES[state["lang"]]

    def update_import_path_text() -> None:
        root_path = state.get("import_root")
        if root_path and root_path.exists():
            import_path_var.set(t()["import_folder_selected"].format(path=str(root_path)))
        else:
            import_path_var.set(t()["import_folder_not_set"])

    def refresh_import_button_state() -> None:
        save_import_btn.config(
            state=("normal" if state.get("game_json") and state.get("import_root") else "disabled")
        )

    def select_import_folder() -> None:
        selected = filedialog.askdirectory(title=t()["set_import_folder"])
        if not selected:
            return

        state["import_root"] = Path(selected)
        update_import_path_text()
        refresh_import_button_state()

    def save_imported_song() -> None:
        if state["busy"]:
            return

        if not state.get("game_json"):
            messagebox.showinfo(APP_NAME, t()["json_unavailable"])
            return

        import_root = state.get("import_root")
        last_file = state.get("last_file_path")
        if not import_root or not last_file:
            messagebox.showerror(APP_NAME, t()["import_error"].format(error="No import folder or source file selected."))
            return

        try:
            folder = create_import_package(import_root, Path(last_file), state["game_json"])
            messagebox.showinfo(APP_NAME, t()["import_success"].format(path=str(folder)))
        except Exception as exc:
            messagebox.showerror(APP_NAME, t()["import_error"].format(error=str(exc)))

    def limit_status_text() -> str:
        return (
            f"Limit: {MAX_FILE_SIZE_MB} MB • analyzes first "
            f"{format_duration_limit(MAX_ANALYSIS_SECONDS, state['lang'])}"
        )

    def sync_text() -> None:
        lang_var.set("EN" if state["lang"] == "en" else "RU")
        title_label.config(text=f"♪ {t()['title']}")
        choose_btn.config(text=t()["loading"] if state["busy"] else t()["btn"])
        copy_json_btn.config(text=t()["copy_json"])
        set_import_folder_btn.config(text=t()["set_import_folder"])
        save_import_btn.config(text=t()["save_import"])
        update_import_path_text()
        limit_var.set(limit_status_text())
        if not state["busy"]:
            set_result(t()["placeholder"])

    def draw_mirror_ball(cx: int, cy: int, radius: int, phase: float) -> None:
        canvas.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            fill="#d7f9ff",
            outline=CYAN,
            width=2,
            tags="fx",
        )
        for offset in range(-radius + 8, radius, 12):
            color = "#ffffff" if (offset // 12 + int(phase)) % 2 == 0 else "#8dfcff"
            canvas.create_line(
                cx - radius + 7,
                cy + offset,
                cx + radius - 7,
                cy + offset,
                fill=color,
                width=1,
                tags="fx",
            )
            canvas.create_line(
                cx + offset,
                cy - radius + 7,
                cx + offset,
                cy + radius - 7,
                fill="#b99cff",
                width=1,
                tags="fx",
            )
        sparkle_x = cx + math.cos(phase / 6) * radius * 0.45
        sparkle_y = cy + math.sin(phase / 7) * radius * 0.35
        canvas.create_oval(
            sparkle_x - 5,
            sparkle_y - 5,
            sparkle_x + 5,
            sparkle_y + 5,
            fill="#ffffff",
            outline="",
            tags="fx",
        )

    def animate(phase: float = 0.0) -> None:
        canvas.delete("fx")
        beam_colors = [PINK, CYAN, GOLD, VIOLET]
        for index, color in enumerate(beam_colors):
            angle = phase / 40 + index * math.pi / 2
            end_x = WINDOW_WIDTH / 2 + math.cos(angle) * WINDOW_WIDTH
            end_y = WINDOW_HEIGHT / 2 + math.sin(angle) * WINDOW_HEIGHT
            canvas.create_polygon(
                WINDOW_WIDTH / 2,
                70,
                end_x - 90,
                end_y,
                end_x + 90,
                end_y,
                fill=color,
                outline="",
                stipple="gray75",
                tags="fx",
            )

        draw_mirror_ball(WINDOW_WIDTH // 2, 62, 31, phase)

        for idx, particle in enumerate(list(particles)):
            particle = particle.move(WINDOW_WIDTH, WINDOW_HEIGHT)
            particles[idx] = particle
            canvas.create_oval(
                particle.x - particle.radius,
                particle.y - particle.radius,
                particle.x + particle.radius,
                particle.y + particle.radius,
                fill=particle.color,
                outline="",
                tags="fx",
            )

        canvas.tag_lower("fx")
        root.after(30, lambda: animate(phase + 1.0))

    def finish_analysis(message: AnalysisMessage) -> None:
        if message.job_id != state["job_id"]:
            return

        state["busy"] = False
        choose_btn.config(state="normal", text=t()["btn"])

        if message.ok:
            state["game_json"] = message.game_json
            copy_json_btn.config(state="normal")
            set_result(message.payload)
            refresh_import_button_state()
            return

        state["game_json"] = ""
        copy_json_btn.config(state="disabled")
        error_text = LANGUAGES[message.lang]["error_load"] + message.payload
        set_result(LANGUAGES[message.lang]["placeholder"])
        messagebox.showerror(LANGUAGES[message.lang]["error"], error_text)

    def poll_analysis_queue() -> None:
        while True:
            try:
                finish_analysis(analysis_queue.get_nowait())
            except queue.Empty:
                break
        root.after(100, poll_analysis_queue)

    def run_analysis(job_id: int, file_path: str, lang: str) -> None:
        try:
            result = analyze_audio_result(file_path, lang)
            analysis_queue.put(
                AnalysisMessage(job_id, lang, True, result.summary, result.game_json)
            )
        except Exception as exc:
            analysis_queue.put(AnalysisMessage(job_id, lang, False, str(exc)))

    def open_file() -> None:
        if state["busy"]:
            return

        file_path = filedialog.askopenfilename(
            title=t()["placeholder"],
            filetypes=[
                ("Audio files", "*.mp3 *.wav *.flac *.ogg *.aac *.m4a"),
            ],
        )
        if not file_path:
            return

        state["job_id"] += 1
        state["busy"] = True
        state["game_json"] = ""
        state["last_file_path"] = file_path
        set_result(t()["loading"])
        choose_btn.config(state="disabled", text=t()["loading"])
        copy_json_btn.config(state="disabled", text=t()["copy_json"])

        thread = threading.Thread(
            target=run_analysis,
            args=(state["job_id"], file_path, state["lang"]),
            daemon=True,
        )
        thread.start()

    def toggle_lang() -> None:
        state["lang"] = "ru" if state["lang"] == "en" else "en"
        if not state["busy"]:
            set_result(t()["placeholder"])
        sync_text()

    def copy_game_json() -> None:
        game_json = str(state.get("game_json") or "")
        if not game_json:
            messagebox.showinfo(APP_NAME, t()["json_unavailable"])
            return

        root.clipboard_clear()
        root.clipboard_append(game_json)
        root.update()
        copy_json_btn.config(text=t()["json_copied"])
        root.after(1400, lambda: copy_json_btn.config(text=t()["copy_json"]))

    lang_btn = tk.Button(
        root,
        textvariable=lang_var,
        font=("Courier New", 9, "bold"),
        fg=GOLD,
        bg=BTN_BG,
        activeforeground=TEXT_COLOR,
        activebackground=BTN_ACTIVE,
        relief="flat",
        bd=0,
        padx=10,
        pady=5,
        cursor="hand2",
        command=toggle_lang,
    )
    lang_btn.place(x=WINDOW_WIDTH - 64, y=18)

    title_label = tk.Label(
        root,
        text=f"♪ {t()['title']}",
        font=("Courier New", 18, "bold"),
        fg=GOLD,
        bg=BG_COLOR,
    )
    title_label.place(relx=0.5, y=105, anchor="n")

    tk.Label(
        root,
        text="BPM • CHANGES • TIMESTAMPS",
        font=("Courier New", 9, "bold"),
        fg=CYAN,
        bg=BG_COLOR,
    ).place(relx=0.5, y=137, anchor="n")

    choose_btn = tk.Button(
        root,
        text=t()["btn"],
        font=("Courier New", 12, "bold"),
        fg=BTN_FG,
        bg=BTN_BG,
        activeforeground=TEXT_COLOR,
        activebackground=BTN_ACTIVE,
        relief="flat",
        bd=0,
        padx=26,
        pady=10,
        cursor="hand2",
        command=open_file,
    )
    choose_btn.place(relx=0.38, y=170, anchor="n")

    copy_json_btn = tk.Button(
        root,
        text=t()["copy_json"],
        font=("Courier New", 11, "bold"),
        fg=GOLD,
        bg=BTN_BG,
        activeforeground=TEXT_COLOR,
        activebackground=BTN_ACTIVE,
        relief="flat",
        bd=0,
        padx=20,
        pady=10,
        cursor="hand2",
        command=copy_game_json,
        state="disabled",
    )
    copy_json_btn.place(relx=0.64, y=170, anchor="n")

    import_path_label = tk.Label(
        root,
        textvariable=import_path_var,
        font=("Courier New", 8),
        fg=MUTED_TEXT,
        bg=BG_COLOR,
    )
    import_path_label.place(relx=0.5, y=205, anchor="n")

    set_import_folder_btn = tk.Button(
        root,
        text=t()["set_import_folder"],
        font=("Courier New", 9, "bold"),
        fg=BTN_FG,
        bg=BTN_BG,
        activeforeground=TEXT_COLOR,
        activebackground=BTN_ACTIVE,
        relief="flat",
        bd=0,
        padx=16,
        pady=8,
        cursor="hand2",
        command=select_import_folder,
    )
    set_import_folder_btn.place(relx=0.38, y=235, anchor="n")

    save_import_btn = tk.Button(
        root,
        text=t()["save_import"],
        font=("Courier New", 9, "bold"),
        fg=GOLD,
        bg=BTN_BG,
        activeforeground=TEXT_COLOR,
        activebackground=BTN_ACTIVE,
        relief="flat",
        bd=0,
        padx=16,
        pady=8,
        cursor="hand2",
        command=save_imported_song,
        state="disabled",
    )
    save_import_btn.place(relx=0.64, y=235, anchor="n")

    update_import_path_text()
    refresh_import_button_state()

    panel_shadow = tk.Canvas(
        root,
        width=WINDOW_WIDTH - 68,
        height=302,
        bg=PINK,
        highlightthickness=0,
    )
    panel_shadow.place(relx=0.5, y=255, anchor="n")

    panel = tk.Canvas(
        root,
        width=WINDOW_WIDTH - 78,
        height=292,
        bg=PANEL_COLOR,
        highlightthickness=2,
        highlightbackground=PANEL_BORDER,
    )
    panel.place(relx=0.5, y=250, anchor="n")

    result_frame = tk.Frame(root, bg=PANEL_COLOR)
    result_frame.place(
        relx=0.5,
        y=252,
        anchor="n",
        width=WINDOW_WIDTH - 86,
        height=284,
    )

    result_text = scrolledtext.ScrolledText(
        result_frame,
        font=("Courier New", 10),
        fg=TEXT_COLOR,
        bg=PANEL_COLOR,
        insertbackground=TEXT_COLOR,
        relief="flat",
        bd=0,
        padx=14,
        pady=14,
        wrap="word",
        state="disabled",
    )
    result_text.pack(fill="both", expand=True)

    def set_result(text: str) -> None:
        result_text.config(state="normal")
        result_text.delete("1.0", tk.END)
        result_text.insert("1.0", text)
        result_text.config(state="disabled")

    set_result(initial_result)

    tk.Label(
        root,
        textvariable=limit_var,
        font=("Courier New", 8),
        fg=MUTED_TEXT,
        bg=BG_COLOR,
    ).place(relx=0.5, y=578, anchor="center")
    limit_var.set(limit_status_text())

    animate()
    poll_analysis_queue()


def main() -> None:
    setup_ffmpeg_path()
    set_windows_app_id()

    root = tk.Tk()
    root.title(APP_NAME)
    root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
    root.resizable(False, False)
    root.configure(bg=BG_COLOR)

    root.update_idletasks()
    x = (root.winfo_screenwidth() - WINDOW_WIDTH) // 2
    y = (root.winfo_screenheight() - WINDOW_HEIGHT) // 2
    root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")

    icon_path = resource_path("assets/discoball.ico")
    fallback_icon_path = resource_path("assets/icon.ico")
    if not icon_path.exists():
        icon_path = fallback_icon_path

    if icon_path.exists():
        try:
            root.iconbitmap(icon_path)
        except tk.TclError as exc:
            print(f"Could not load icon: {exc}", file=sys.stderr)

    build_ui(root)
    root.mainloop()


if __name__ == "__main__":
    main()

