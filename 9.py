"""
Interactive Metronome
---------------------
Архитектура:
    AudioEngine    — синтез кликов (wavetable + envelope), кэш Sound-объектов
    MetronomeEngine — высокоточный тактовый генератор в отдельном потоке
                     (drift-compensated: next_t += interval, а не sleep(interval))
    MetronomeApp   — Tk-интерфейс, обновляется через очередь из воркер-потока
"""

import tkinter as tk
import threading
import time
import math
import struct
import random
import queue

# ============================================================
#  AUDIO ENGINE
# ============================================================
try:
    import pygame
    pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=256)
    pygame.mixer.init()
    AUDIO = True
except Exception as _e:
    print(f"[audio] disabled: {_e}")
    AUDIO = False

SR = 44100  # sample rate


def _env(t, dur, attack, decay):
    """Attack + exponential decay envelope."""
    a = min(1.0, t / attack) if attack > 0 else 1.0
    return a * math.exp(-decay * t / dur)


def _render(sample_fn, dur, vol=0.7):
    """Рендер моно-сигнала в stereo 16-bit буфер pygame.Sound."""
    if not AUDIO:
        return None
    n = int(SR * dur)
    buf = bytearray(n * 4)
    for i in range(n):
        t = i / SR
        v = int(max(-1.0, min(1.0, sample_fn(t))) * vol * 30000)
        struct.pack_into('<hh', buf, i * 4, v, v)
    return pygame.mixer.Sound(buffer=bytes(buf))


# --- генераторы тембров (accent = первая доля такта) ---

def _click(accent):
    f = 2200 if accent else 1500
    def s(t):
        e = _env(t, 0.035, 0.0004, 16)
        return e * (math.sin(2 * math.pi * f * t) + 0.35 * random.uniform(-1, 1))
    return _render(s, 0.035, 0.55)


def _beep(accent):
    f = 1320 if accent else 880
    def s(t):
        return _env(t, 0.07, 0.002, 10) * math.sin(2 * math.pi * f * t)
    return _render(s, 0.07, 0.5)


def _wood(accent):
    f = 1600 if accent else 1050
    def s(t):
        e = _env(t, 0.06, 0.0005, 14)
        return e * (math.sin(2 * math.pi * f * t) + 0.5 * math.sin(2 * math.pi * f * 2.4 * t))
    return _render(s, 0.06, 0.6)


def _bell(accent):
    f = 990 if accent else 740
    def s(t):
        e = _env(t, 0.45, 0.002, 5)
        return e * (math.sin(2 * math.pi * f * t)
                    + 0.5 * math.sin(2 * math.pi * f * 2 * t)
                    + 0.25 * math.sin(2 * math.pi * f * 3.01 * t)
                    + 0.10 * math.sin(2 * math.pi * f * 4.2 * t))
    return _render(s, 0.45, 0.42)


SOUND_BUILDERS = {'Click': _click, 'Beep': _beep, 'Wood': _wood, 'Bell': _bell}


# ============================================================
#  METRONOME ENGINE (precise timing, thread-safe)
# ============================================================
class MetronomeEngine:
    """Точный генератор тактов. Компенсирует дрейф: цель считается от
    абсолютного времени, а не от предыдущего sleep."""

    def __init__(self, on_beat):
        self.on_beat = on_beat
        self._bpm = 100
        self._bpb = 4
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self.running = False

    # --- thread-safe параметры ---
    @property
    def bpm(self):
        with self._lock:
            return self._bpm

    @bpm.setter
    def bpm(self, v):
        with self._lock:
            self._bpm = max(20, min(400, int(v)))

    @property
    def beats_per_bar(self):
        with self._lock:
            return self._bpb

    @beats_per_bar.setter
    def beats_per_bar(self, v):
        with self._lock:
            self._bpb = max(1, int(v))

    # --- lifecycle ---
    def start(self):
        if self.running:
            return
        self.running = True
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name='metronome')
        self._thread.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        self._stop.set()

    def _loop(self):
        beat = 0
        next_t = time.perf_counter()
        while not self._stop.is_set():
            bpm = self.bpm
            bpb = self.beats_per_bar
            self.on_beat(beat % bpb, bpb)
            beat += 1

            next_t += 60.0 / max(1, bpm)
            now = time.perf_counter()
            if next_t < now - 0.15:      # отстали — ресинк
                next_t = now
            # sleep с возможностью прерывания
            while True:
                rem = next_t - time.perf_counter()
                if rem <= 0:
                    break
                if self._stop.wait(min(rem, 0.01)):
                    return


# ============================================================
#  APP
# ============================================================
class MetronomeApp:
    # --- палитра ---
    BG          = '#0a0f1e'
    PANEL       = '#151b30'
    PANEL_LIGHT = '#1d2542'
    FG          = '#e9eeff'
    MUTED       = '#7c8ab8'
    GOLD        = '#ffd166'   # акцентная доля
    MINT        = '#06d6a0'   # обычная доля
    PINK        = '#ef476f'
    CYAN        = '#4cc9f0'
    TXT_DARK    = '#07121f'

    # --- геометрия ---
    CANVAS_W, CANVAS_H = 720, 490
    CX, CY      = 360, 245
    RING_R      = 128
    DOT_R       = 13
    CENTER_R    = 76
    BPM_MIN, BPM_MAX = 40, 240

    def __init__(self, root):
        self.root = root
        root.title('Метроном')
        root.configure(bg=self.BG)
        root.resizable(False, False)

        # --- состояние ---
        self.bpm = 100
        self.beats_per_bar = 4
        self.sound_name = 'Click'
        self.active_beat = None
        self.pulse = 0.0
        self._taps = []
        self._last_frame = time.perf_counter()
        self._suppress = False

        # --- звуки ---
        self._sounds = {}
        for name, builder in SOUND_BUILDERS.items():
            for accent in (False, True):
                self._sounds[(name, accent)] = builder(accent)

        # --- очередь UI-событий из воркер-потока ---
        self.ui_queue = queue.Queue()

        # --- движок ---
        self.engine = MetronomeEngine(self._on_beat)
        self.engine.bpm = self.bpm
        self.engine.beats_per_bar = self.beats_per_bar

        # --- сборка UI ---
        self._build_canvas()
        self._build_controls()
        self._refresh_toggles()
        self._update_bpm_display()
        self._render_circle()

        # --- циклы и хоткеи ---
        self._poll_queue()
        self._animate()
        self._bind_keys()

        self._center_window()

    # =========================================================
    #  CANVAS
    # =========================================================
    def _build_canvas(self):
        self.canvas = tk.Canvas(self.root, width=self.CANVAS_W, height=self.CANVAS_H,
                                bg=self.BG, highlightthickness=0)
        self.canvas.pack()

        # заголовок
        self.canvas.create_text(self.CX, 32, text='МЕТРОНОМ',
                                fill=self.FG, font=('Segoe UI', 22, 'bold'))
        self.canvas.create_text(self.CX, 62, text='точный ритм · чистый звук',
                                fill=self.MUTED, font=('Segoe UI', 10))

        # мягкое свечение вокруг кольца
        self.glow_id = self.canvas.create_oval(0, 0, 0, 0, outline='', fill='')

        # кольцо-подложка
        self.canvas.create_oval(
            self.CX - self.RING_R, self.CY - self.RING_R,
            self.CX + self.RING_R, self.CY + self.RING_R,
            outline=self.PANEL_LIGHT, width=2, fill='')

        # центральный круг
        self.center_id = self.canvas.create_oval(
            self.CX - self.CENTER_R, self.CY - self.CENTER_R,
            self.CX + self.CENTER_R, self.CY + self.CENTER_R,
            fill=self.PANEL, outline=self.MUTED, width=3)

        # цифра доли + знаменатель
        self.beat_txt_id = self.canvas.create_text(
            self.CX, self.CY - 8, text='—',
            fill=self.FG, font=('Segoe UI', 44, 'bold'))
        self.beat_sub_id = self.canvas.create_text(
            self.CX, self.CY + 34, text='/ 4',
            fill=self.MUTED, font=('Segoe UI', 14))

        # точки долей
        self.dot_ids = []
        for _ in range(12):
            d = self.canvas.create_oval(0, 0, 0, 0, fill=self.PANEL,
                                        outline=self.MUTED, width=2, state='hidden')
            self.dot_ids.append(d)

        # BPM + темповая характеристика
        self.bpm_txt_id = self.canvas.create_text(
            self.CX, 428, text='100 BPM',
            fill=self.GOLD, font=('Segoe UI', 20, 'bold'))
        self.tempo_txt_id = self.canvas.create_text(
            self.CX, 458, text='Andante',
            fill=self.MUTED, font=('Segoe UI', 11))

    # =========================================================
    #  CONTROLS
    # =========================================================
    def _build_controls(self):
        panel = tk.Frame(self.root, bg=self.BG)
        panel.pack(fill='both', expand=True, padx=28, pady=(0, 20))

        # ---------- START ----------
        self.start_btn = tk.Button(
            panel, text='▶   СТАРТ', command=self._toggle,
            bg=self.MINT, fg=self.TXT_DARK,
            activebackground='#04b487', activeforeground=self.TXT_DARK,
            relief='flat', bd=0, cursor='hand2',
            font=('Segoe UI', 17, 'bold'), pady=10)
        self.start_btn.pack(fill='x', pady=(0, 16))

        # ---------- ТЕМП ----------
        row = tk.Frame(panel, bg=self.BG)
        row.pack(fill='x', pady=(0, 12))

        tk.Label(row, text='ТЕМП', bg=self.BG, fg=self.MUTED,
                 font=('Segoe UI', 10, 'bold'), width=8, anchor='w'
                 ).pack(side='left')

        self.bpm_value_lbl = tk.Label(row, text='100', bg=self.BG, fg=self.GOLD,
                                      font=('Segoe UI', 15, 'bold'), width=4)
        self.bpm_value_lbl.pack(side='left', padx=(0, 8))

        self._mk_btn(row, '−', lambda: self._nudge(-1)).pack(side='left')

        self.scale = tk.Scale(
            row, from_=self.BPM_MIN, to=self.BPM_MAX, orient='horizontal',
            showvalue=False, command=self._on_scale,
            bg=self.BG, fg=self.FG, troughcolor=self.PANEL,
            activebackground=self.CYAN, highlightthickness=0, bd=0,
            sliderlength=22, width=14, sliderrelief='flat')
        self.scale.set(self.bpm)
        self.scale.pack(side='left', fill='x', expand=True, padx=8)

        self._mk_btn(row, '+', lambda: self._nudge(+1)).pack(side='left')

        self.tap_btn = self._mk_btn(row, 'TAP', self._tap)
        self.tap_btn.pack(side='left', padx=(8, 0))

        # ---------- РАЗМЕР ----------
        row2 = tk.Frame(panel, bg=self.BG)
        row2.pack(fill='x', pady=(0, 10))
        tk.Label(row2, text='РАЗМЕР', bg=self.BG, fg=self.MUTED,
                 font=('Segoe UI', 10, 'bold'), width=8, anchor='w'
                 ).pack(side='left')
        self.size_btns = {}
        for n in (2, 3, 4, 6):
            b = self._mk_toggle(row2, f'{n}/4', lambda v=n: self._set_size(v))
            b.pack(side='left', padx=3)
            self.size_btns[n] = b

        # ---------- ЗВУК ----------
        row3 = tk.Frame(panel, bg=self.BG)
        row3.pack(fill='x')
        tk.Label(row3, text='ЗВУК', bg=self.BG, fg=self.MUTED,
                 font=('Segoe UI', 10, 'bold'), width=8, anchor='w'
                 ).pack(side='left')
        self.sound_btns = {}
        for name in SOUND_BUILDERS:
            b = self._mk_toggle(row3, name, lambda v=name: self._set_sound(v))
            b.pack(side='left', padx=3)
            self.sound_btns[name] = b

    # ---------- helpers для виджетов ----------
    def _mk_btn(self, parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd,
                         bg=self.PANEL_LIGHT, fg=self.FG,
                         activebackground=self.CYAN, activeforeground=self.TXT_DARK,
                         relief='flat', bd=0, cursor='hand2',
                         font=('Segoe UI', 12, 'bold'),
                         padx=12, pady=5, width=3)

    def _mk_toggle(self, parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd,
                         bg=self.PANEL, fg=self.MUTED,
                         activebackground=self.CYAN, activeforeground=self.TXT_DARK,
                         relief='flat', bd=0, cursor='hand2',
                         font=('Segoe UI', 11, 'bold'),
                         padx=16, pady=7)

    def _refresh_toggles(self):
        for n, b in self.size_btns.items():
            on = (n == self.beats_per_bar)
            b.configure(bg=self.CYAN if on else self.PANEL,
                        fg=self.TXT_DARK if on else self.MUTED)
        for name, b in self.sound_btns.items():
            on = (name == self.sound_name)
            b.configure(bg=self.GOLD if on else self.PANEL,
                        fg=self.TXT_DARK if on else self.MUTED)

    # =========================================================
    #  SETTERS
    # =========================================================
    def _set_bpm(self, v, from_scale=False):
        v = max(self.BPM_MIN, min(self.BPM_MAX, int(v)))
        if v == self.bpm:
            return
        self.bpm = v
        self.engine.bpm = v
        if not from_scale:
            self._suppress = True
            self.scale.set(v)
            self._suppress = False
        self._update_bpm_display()

    def _nudge(self, delta):
        self._set_bpm(self.bpm + delta)

    def _on_scale(self, value):
        if self._suppress:
            return
        self._set_bpm(int(float(value)), from_scale=True)

    def _set_size(self, n):
        self.beats_per_bar = n
        self.engine.beats_per_bar = n
        self.active_beat = None
        self._refresh_toggles()
        self._render_circle()

    def _set_sound(self, name):
        self.sound_name = name
        self._refresh_toggles()
        # превью нового тембра
        if AUDIO:
            s = self._sounds.get((name, True))
            if s:
                try:
                    s.play()
                except Exception:
                    pass

    def _tap(self):
        now = time.perf_counter()
        if self._taps and now - self._taps[-1] > 2.0:
            self._taps.clear()
        self._taps.append(now)
        if len(self._taps) > 6:
            self._taps.pop(0)
        # визуальный отклик
        self.tap_btn.configure(bg=self.CYAN, fg=self.TXT_DARK)
        self.root.after(120, lambda: self.tap_btn.configure(
            bg=self.PANEL_LIGHT, fg=self.FG))
        if len(self._taps) >= 2:
            intervals = [self._taps[i + 1] - self._taps[i]
                         for i in range(len(self._taps) - 1)]
            avg = sum(intervals) / len(intervals)
            self._set_bpm(round(60.0 / avg))

    # =========================================================
    #  UI updates (main thread)
    # =========================================================
    @staticmethod
    def _tempo_name(bpm):
        if bpm < 60:  return 'Largo'
        if bpm < 76:  return 'Adagio'
        if bpm < 108: return 'Andante'
        if bpm < 120: return 'Moderato'
        if bpm < 168: return 'Allegro'
        return 'Presto'

    def _update_bpm_display(self):
        self.bpm_value_lbl.configure(text=str(self.bpm))
        if hasattr(self, 'bpm_txt_id'):
            self.canvas.itemconfig(self.bpm_txt_id, text=f'{self.bpm} BPM')
            self.canvas.itemconfig(self.tempo_txt_id, text=self._tempo_name(self.bpm))

    # ---------- запросы из очереди (из воркер-потока) ----------
    def _poll_queue(self):
        try:
            while True:
                fn = self.ui_queue.get_nowait()
                try:
                    fn()
                except Exception as e:
                    print(f"[ui] callback error: {e}")
        except queue.Empty:
            pass
        self.root.after(12, self._poll_queue)

    # =========================================================
    #  BEAT CALLBACK (worker thread!)
    # =========================================================
    def _on_beat(self, beat, bpb):
        accent = (beat == 0)
        # звук можно играть прямо из воркер-потока — pygame.mixer потокобезопасен
        if AUDIO:
            s = self._sounds.get((self.sound_name, accent))
            if s:
                try:
                    s.play()
                except Exception:
                    pass
        # UI обновляем только через очередь
        self.ui_queue.put(lambda b=beat: self._on_beat_ui(b))

    def _on_beat_ui(self, beat):
        self.active_beat = beat
        self.pulse = 1.0
        self._render_circle()

    # =========================================================
    #  RENDERING
    # =========================================================
    @staticmethod
    def _mix(c1, c2, t):
        c1, c2 = c1.lstrip('#'), c2.lstrip('#')
        r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
        r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
        return (f'#{int(r1 + (r2 - r1) * t):02x}'
                f'{int(g1 + (g2 - g1) * t):02x}'
                f'{int(b1 + (b2 - b1) * t):02x}')

    def _render_circle(self):
        cx, cy, p = self.CX, self.CY, self.pulse

        # --- свечение ---
        glow_r = self.CENTER_R + 26 * p
        accent = (self.active_beat == 0)
        col = self.GOLD if accent else self.MINT
        if p > 0.02:
            self.canvas.itemconfig(self.glow_id, fill=self._mix(self.BG, col, 0.18 * p))
            self.canvas.coords(self.glow_id, cx - glow_r, cy - glow_r,
                               cx + glow_r, cy + glow_r)
        else:
            self.canvas.coords(self.glow_id, 0, 0, 0, 0)

        # --- центральный круг ---
        base_r = self.CENTER_R + 10 * p
        self.canvas.coords(self.center_id,
                           cx - base_r, cy - base_r, cx + base_r, cy + base_r)
        if p > 0.02:
            self.canvas.itemconfig(self.center_id,
                                   fill=self._mix(self.PANEL, col, 0.45 * p),
                                   outline=col, width=3)
        else:
            self.canvas.itemconfig(self.center_id,
                                   fill=self.PANEL, outline=self.MUTED, width=3)

        # --- точки долей ---
        bpb = self.beats_per_bar
        for i, d in enumerate(self.dot_ids):
            if i >= bpb:
                self.canvas.itemconfig(d, state='hidden')
                continue
            self.canvas.itemconfig(d, state='normal')
            ang = math.radians(-90 + i * 360.0 / bpb)
            x = cx + self.RING_R * math.cos(ang)
            y = cy + self.RING_R * math.sin(ang)
            is_acc = (i == 0)
            base_col = self.GOLD if is_acc else self.MUTED

            if i == self.active_beat and p > 0.02:
                active_col = self.GOLD if is_acc else self.MINT
                r = self.DOT_R + 5 * p
                self.canvas.coords(d, x - r, y - r, x + r, y + r)
                self.canvas.itemconfig(d, fill=active_col, outline=active_col,
                                       width=2)
            else:
                r = self.DOT_R + (2 if is_acc else 0)
                self.canvas.coords(d, x - r, y - r, x + r, y + r)
                self.canvas.itemconfig(d, fill=self.PANEL, outline=base_col,
                                       width=3 if is_acc else 2)

        # --- текст доли ---
        if self.active_beat is not None:
            self.canvas.itemconfig(self.beat_txt_id, text=str(self.active_beat + 1))
            self.canvas.itemconfig(self.beat_sub_id, text=f'/ {bpb}')
        else:
            self.canvas.itemconfig(self.beat_txt_id, text='—')
            self.canvas.itemconfig(self.beat_sub_id, text=f'/ {bpb}')

    # =========================================================
    #  ANIMATION LOOP (main thread)
    # =========================================================
    def _animate(self):
        now = time.perf_counter()
        dt = now - self._last_frame
        self._last_frame = now
        if self.pulse > 0.0:
            self.pulse = max(0.0, self.pulse - dt * 6.5)   # ~150 мс
            self._render_circle()
        self.root.after(16, self._animate)

    # =========================================================
    #  CONTROLS / LIFECYCLE
    # =========================================================
    def _toggle(self):
        if self.engine.running:
            self._stop()
        else:
            self._start()

    def _start(self):
        self.active_beat = None
        self.pulse = 0.0
        self.engine.bpm = self.bpm
        self.engine.beats_per_bar = self.beats_per_bar
        self.engine.start()
        self.start_btn.configure(
            text='■   СТОП', bg=self.PINK,
            activebackground='#d63a5e')

    def _stop(self):
        self.engine.stop()
        self.active_beat = None
        self.pulse = 0.0
        self._render_circle()
        self.start_btn.configure(
            text='▶   СТАРТ', bg=self.MINT,
            activebackground='#04b487')

    def _bind_keys(self):
        self.root.bind('<space>', lambda e: (self._toggle(), 'break')[1])
        self.root.bind('<Up>',    lambda e: self._nudge(+1))
        self.root.bind('<Down>',  lambda e: self._nudge(-1))
        self.root.bind('<Shift-Up>',   lambda e: self._nudge(+5))
        self.root.bind('<Shift-Down>', lambda e: self._nudge(-5))
        self.root.bind('<Escape>', lambda e: self._stop() if self.engine.running else None)

    def _center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = max(0, (sh - h) // 2 - 30)
        self.root.geometry(f'{w}x{h}+{x}+{y}')


# ============================================================
def main():
    root = tk.Tk()
    MetronomeApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()