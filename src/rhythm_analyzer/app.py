from __future__ import annotations

import math
import os
import queue
import random
import sys
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import imageio_ffmpeg
import numpy as np
from librosa.beat import beat_track
from librosa.core import frames_to_time, get_duration, load

APP_NAME = "Rhythm Analyzer"
APP_ID = "DiscoRhythmAnalyzer"
WINDOW_WIDTH = 560
WINDOW_HEIGHT = 460
TARGET_SAMPLE_RATE = 22_050
MAX_ANALYSIS_SECONDS = 180
MAX_FILE_SIZE_MB = 250
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a"}

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
        "duration_note": "первые {seconds} сек.",
        "samplerate": "Частота",
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
        "duration_note": "first {seconds} sec.",
        "samplerate": "Sample rate",
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


def calc_rhythm_stability(beat_frames: np.ndarray, sr: int, lang: str) -> tuple[float, str]:
    beat_times = frames_to_time(beat_frames, sr=sr)
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


def analyze_audio_file(file_path: str, lang: str) -> str:
    t = LANGUAGES[lang]
    path = Path(file_path)
    size_bytes = validate_audio_file(path, lang)

    y, sr = load(
        str(path),
        sr=TARGET_SAMPLE_RATE,
        mono=True,
        duration=MAX_ANALYSIS_SECONDS,
    )

    if y.size == 0:
        raise ValueError(t["no_audio"])

    tempo_raw, beat_frames = beat_track(y=y, sr=sr)
    tempo = scalar_float(tempo_raw)
    cv, stability = calc_rhythm_stability(np.asarray(beat_frames), sr, lang)
    pattern, confidence = classify_tempo(tempo, len(beat_frames), lang)
    duration = get_duration(y=y, sr=sr)
    duration_text = f"{duration:.1f} sec"

    if duration >= MAX_ANALYSIS_SECONDS - 0.25:
        duration_text += f" ({t['duration_note'].format(seconds=MAX_ANALYSIS_SECONDS)})"

    return (
        f"{t['file']}:        {clean_display_name(path.name)}\n"
        f"{t['size']}:        {format_file_size(size_bytes)}\n"
        f"{t['tempo']}:       {tempo:.1f} BPM\n"
        f"{t['pattern']}:     {pattern}\n"
        f"{t['confidence']}:  {confidence * 100:.1f}%\n"
        f"{t['stability']}:   {stability} (+/-{cv} ms)\n"
        f"{t['duration']}:    {duration_text}\n"
        f"{t['samplerate']}:  {sr} Hz"
    )


def build_ui(root: tk.Tk) -> None:
    state = {"lang": "en", "busy": False, "job_id": 0}
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
    result_var = tk.StringVar(value=LANGUAGES[state["lang"]]["placeholder"])

    def t() -> dict[str, Any]:
        return LANGUAGES[state["lang"]]

    def sync_text() -> None:
        lang_var.set("EN" if state["lang"] == "en" else "RU")
        title_label.config(text=f"♪ {t()['title']}")
        choose_btn.config(text=t()["loading"] if state["busy"] else t()["btn"])
        if not state["busy"] and not result_var.get().strip():
            result_var.set(t()["placeholder"])

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
            result_var.set(message.payload)
            return

        error_text = LANGUAGES[message.lang]["error_load"] + message.payload
        result_var.set(LANGUAGES[message.lang]["placeholder"])
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
            payload = analyze_audio_file(file_path, lang)
            analysis_queue.put(AnalysisMessage(job_id, lang, True, payload))
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
        result_var.set(t()["loading"])
        choose_btn.config(state="disabled", text=t()["loading"])

        thread = threading.Thread(
            target=run_analysis,
            args=(state["job_id"], file_path, state["lang"]),
            daemon=True,
        )
        thread.start()

    def toggle_lang() -> None:
        state["lang"] = "ru" if state["lang"] == "en" else "en"
        if not state["busy"]:
            result_var.set(t()["placeholder"])
        sync_text()

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
        text="BPM • GROOVE • STABILITY",
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
    choose_btn.place(relx=0.5, y=170, anchor="n")

    panel_shadow = tk.Canvas(
        root,
        width=WINDOW_WIDTH - 68,
        height=222,
        bg=PINK,
        highlightthickness=0,
    )
    panel_shadow.place(relx=0.5, y=230, anchor="n")

    panel = tk.Canvas(
        root,
        width=WINDOW_WIDTH - 78,
        height=212,
        bg=PANEL_COLOR,
        highlightthickness=2,
        highlightbackground=PANEL_BORDER,
    )
    panel.place(relx=0.5, y=225, anchor="n")

    result_frame = tk.Frame(root, bg=PANEL_COLOR)
    result_frame.place(
        relx=0.5,
        y=228,
        anchor="n",
        width=WINDOW_WIDTH - 86,
        height=204,
    )

    tk.Label(
        result_frame,
        textvariable=result_var,
        font=("Courier New", 10),
        fg=TEXT_COLOR,
        bg=PANEL_COLOR,
        justify="left",
        anchor="nw",
        padx=16,
        pady=16,
        wraplength=WINDOW_WIDTH - 128,
    ).pack(fill="both", expand=True)

    tk.Label(
        root,
        text=f"Limit: {MAX_FILE_SIZE_MB} MB • analyzes first {MAX_ANALYSIS_SECONDS} seconds",
        font=("Courier New", 8),
        fg=MUTED_TEXT,
        bg=BG_COLOR,
    ).place(relx=0.5, y=438, anchor="center")

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
