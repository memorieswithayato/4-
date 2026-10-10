"""
Guess the Instrument
--------------------
• 8 инструментов, каждый — синтезированный тембр (аддитивный синтез + шум)
• Иконки рисуются векторно на Canvas — никаких внешних файлов
• Раунд: звук → 4 карточки → выбор → анимация + звук + конфетти
• Подсказка: убирает один неверный вариант (1 на раунд)
"""

import tkinter as tk
import math, struct, random

# ============================================================
#  AUDIO
# ============================================================
try:
    import pygame
    pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
    pygame.mixer.init()
    AUDIO = True
except Exception as e:
    print(f"[audio] disabled: {e}")
    AUDIO = False

SR = 44100


def _render(fn, dur, vol=0.5):
    """Рендер моно-функции в stereo 16-bit pygame.Sound."""
    if not AUDIO:
        return None
    n = int(SR * dur)
    buf = bytearray(n * 4)
    for i in range(n):
        t = i / SR
        v = max(-1.0, min(1.0, fn(t)))
        iv = int(v * vol * 30000)
        struct.pack_into('<hh', buf, i * 4, iv, iv)
    return pygame.mixer.Sound(buffer=bytes(buf))


# ---------- ИНСТРУМЕНТЫ (тембры) ----------
def snd_piano():
    """Аккорд C-dur с яркими обертонами и быстрой атакой."""
    notes = [261.63, 329.63, 392.00, 523.25]
    def s(t):
        env = min(1, t * 80) * math.exp(-2.5 * t)
        v = 0
        for f in notes:
            for k in range(1, 6):
                v += (1.0 / k ** 1.6) * math.sin(2 * math.pi * f * k * t)
        return env * v / (len(notes) * 2)
    return _render(s, 1.2, 0.5)


def snd_guitar():
    """Перебор трёх струн Em с щелчком-атакой."""
    notes, delays = [164.81, 196.00, 246.94], [0, 0.04, 0.08]
    def s(t):
        v = 0
        for f, d in zip(notes, delays):
            lt = t - d
            if lt < 0:
                continue
            env = min(1, lt * 200) * math.exp(-3.5 * lt)
            for k in range(1, 6):
                v += (1.0 / k) * math.sin(2 * math.pi * f * k * lt) * env
        if t < 0.01:
            v += random.uniform(-1, 1) * (1 - t / 0.01) * 0.4
        return v / 3
    return _render(s, 1.0, 0.5)


def snd_violin():
    """Смычковый: богатые обертоны, вибрато 5.5 Гц, дыхание смычка."""
    f = 440.0
    def s(t):
        env = min(1, t * 12) * math.exp(-1.2 * t)
        fv = f * (1 + 0.012 * math.sin(2 * math.pi * 5.5 * t))
        v = sum(a * math.sin(2 * math.pi * fv * k * t)
                for k, a in enumerate([1.0, 0.7, 0.5, 0.35, 0.2, 0.1], 1))
        v += random.uniform(-1, 1) * 0.06
        return env * v / 2.5
    return _render(s, 1.5, 0.4)


def snd_flute():
    """Чистая синусоида + лёгкое дыхание + вибрато."""
    f = 587.33
    def s(t):
        env = min(1, t * 20) * math.exp(-1.5 * t)
        fv = f * (1 + 0.005 * math.sin(2 * math.pi * 5 * t))
        v = math.sin(2 * math.pi * fv * t) + 0.15 * math.sin(2 * math.pi * fv * 2 * t)
        v += random.uniform(-1, 1) * 0.06 * math.exp(-4 * t)
        return env * v
    return _render(s, 1.4, 0.4)


def snd_drum():
    """Kick + snare: тон с частотным свипом + шум."""
    def s(t):
        f_sweep = 120 * math.exp(-12 * t) + 40
        v = math.sin(2 * math.pi * f_sweep * t) * math.exp(-7 * t) * 1.2
        v += random.uniform(-1, 1) * math.exp(-14 * t) * 0.6
        if t < 0.005:
            v += random.uniform(-1, 1) * (1 - t / 0.005) * 0.8
        return v
    return _render(s, 0.5, 0.6)


def snd_xylophone():
    """Деревянная пластина — неармонические частичные 2.76x и 5.4x."""
    notes, delays = [523.25, 659.25, 783.99, 1046.50], [0, 0.12, 0.24, 0.36]
    def s(t):
        v = 0
        for f, d in zip(notes, delays):
            lt = t - d
            if lt < 0:
                continue
            env = min(1, lt * 400) * math.exp(-9 * lt)
            v += env * (math.sin(2 * math.pi * f * lt)
                        + 0.5 * math.sin(2 * math.pi * f * 2.76 * lt)
                        + 0.2 * math.sin(2 * math.pi * f * 5.4 * lt))
        return v / 2.5
    return _render(s, 0.95, 0.45)


def snd_trumpet():
    """Медный: сильные гармоники + характерная атака."""
    f = 349.23
    def s(t):
        env = min(1, t * 8) * max(0, min(1, (1.2 - t) * 4))
        v = sum((1.0 / k) * math.sin(2 * math.pi * f * k * t) for k in range(1, 10))
        return env * v / 3
    return _render(s, 1.2, 0.4)


def snd_harp():
    """Арпеджио из шести нот с мягким затуханием."""
    notes = [261.63, 329.63, 392.00, 523.25, 659.25, 783.99]
    delays = [i * 0.07 for i in range(6)]
    def s(t):
        v = 0
        for f, d in zip(notes, delays):
            lt = t - d
            if lt < 0:
                continue
            env = min(1, lt * 150) * math.exp(-3.5 * lt)
            for k, a in enumerate([1, 0.4, 0.2, 0.08], 1):
                v += a * math.sin(2 * math.pi * f * k * lt) * env
        return v / 5
    return _render(s, 1.6, 0.45)


# ---------- ЭФФЕКТЫ ----------
def snd_fanfare():
    """Мажорное арпеджио C-E-G-C."""
    notes, delays = [523.25, 659.25, 783.99, 1046.50], [0, 0.09, 0.18, 0.30]
    def s(t):
        v = 0
        for f, d in zip(notes, delays):
            lt = t - d
            if lt < 0:
                continue
            env = min(1, lt * 60) * math.exp(-3.5 * lt)
            v += env * (math.sin(2 * math.pi * f * lt)
                        + 0.4 * math.sin(2 * math.pi * f * 2 * lt)
                        + 0.15 * math.sin(2 * math.pi * f * 3 * lt))
        return v / 3
    return _render(s, 1.0, 0.5)


def snd_buzz():
    """Низкий биения-«неправильно»."""
    def s(t):
        env = math.exp(-5 * t)
        return env * (0.7 * math.sin(2 * math.pi * 140 * t)
                      + 0.3 * math.sin(2 * math.pi * 155 * t))
    return _render(s, 0.35, 0.45)


def snd_tick():
    """Короткий клик для UI."""
    def s(t):
        return math.exp(-40 * t) * random.uniform(-1, 1)
    return _render(s, 0.05, 0.4)


# ============================================================
#  ИКОНКИ (векторные, рисуются на Canvas)
# ============================================================
def draw_piano(c, cx, cy, s):
    w, h = 62 * s, 40 * s
    c.create_rectangle(cx - w, cy - h, cx + w, cy + h,
                       fill='#1a1a2e', outline='#aab0d0', width=2)
    n = 8
    kw = 2 * w / n
    for i in range(n):
        x1 = cx - w + i * kw + 1
        c.create_rectangle(x1, cy - h + 4 * s, x1 + kw - 2, cy + h - 2,
                           fill='white', outline='#555')
    for i in [0, 1, 3, 4, 5]:
        x1 = cx - w + (i + 1) * kw - 3.5 * s
        c.create_rectangle(x1, cy - h + 4 * s, x1 + 7 * s, cy + 2 * s,
                           fill='#111', outline='')


def draw_guitar(c, cx, cy, s):
    c.create_oval(cx - 30 * s, cy + 8 * s, cx + 30 * s, cy + 48 * s,
                  fill='#c68a4e', outline='#7a5228', width=2)
    c.create_oval(cx - 24 * s, cy - 16 * s, cx + 24 * s, cy + 28 * s,
                  fill='#c68a4e', outline='#7a5228', width=2)
    c.create_oval(cx - 7 * s, cy + 8 * s, cx + 7 * s, cy + 22 * s,
                  fill='#3a2410', outline='#1a0f05')
    c.create_rectangle(cx - 6 * s, cy - 58 * s, cx + 6 * s, cy - 8 * s,
                       fill='#5a3a1b', outline='#3a2410')
    c.create_rectangle(cx - 9 * s, cy - 68 * s, cx + 9 * s, cy - 56 * s,
                       fill='#2a1808', outline='#1a0f05')
    for side in (-1, 1):
        for k in range(3):
            yy = cy - 65 * s + k * 3.5 * s
            c.create_oval(cx + side * 9 * s - 1.5 * s, yy - 1.5 * s,
                          cx + side * 9 * s + 1.5 * s, yy + 1.5 * s,
                          fill='#e9eeff', outline='')
    for k in (-1, 0, 1):
        c.create_line(cx + k * 3.5 * s, cy - 58 * s, cx + k * 3.5 * s, cy + 38 * s,
                      fill='#e9eeff', width=1)


def draw_violin(c, cx, cy, s):
    c.create_oval(cx - 22 * s, cy - 24 * s, cx + 22 * s, cy + 4 * s,
                  fill='#a0522d', outline='#5a2a10', width=2)
    c.create_oval(cx - 26 * s, cy + 4 * s, cx + 26 * s, cy + 38 * s,
                  fill='#a0522d', outline='#5a2a10', width=2)
    c.create_rectangle(cx - 19 * s, cy - 10 * s, cx + 19 * s, cy + 18 * s,
                       fill='#a0522d', outline='')
    for side in (-1, 1):
        x1 = cx + side * 11 * s - 2.5 * s
        c.create_oval(x1, cy - 2 * s, x1 + 5 * s, cy + 14 * s,
                      fill='#3a1a08', outline='')
    c.create_rectangle(cx - 4 * s, cy - 56 * s, cx + 4 * s, cy - 22 * s,
                       fill='#3a1a08', outline='#1a0805')
    c.create_oval(cx - 7 * s, cy - 66 * s, cx + 7 * s, cy - 52 * s,
                  fill='#3a1a08', outline='#1a0805')
    for k in (-1, 0, 1):
        c.create_line(cx + k * 2.5 * s, cy - 56 * s, cx + k * 2.5 * s, cy + 34 * s,
                      fill='#e9eeff', width=1)


def draw_flute(c, cx, cy, s):
    c.create_rectangle(cx - 60 * s, cy - 5 * s, cx + 60 * s, cy + 5 * s,
                       fill='#c0c0d8', outline='#606080', width=2)
    c.create_oval(cx - 68 * s, cy - 7 * s, cx - 52 * s, cy + 7 * s,
                  fill='#a0a0c0', outline='#606080', width=2)
    for i in range(6):
        x = cx - 18 * s + i * 12 * s
        c.create_oval(x - 2.5 * s, cy - 3.5 * s, x + 2.5 * s, cy + 3.5 * s,
                      fill='#303048', outline='#1a1a2a')
    c.create_line(cx - 55 * s, cy - 2 * s, cx + 55 * s, cy - 2 * s,
                  fill='#f0f0ff', width=1)


def draw_drum(c, cx, cy, s):
    c.create_rectangle(cx - 42 * s, cy - 4 * s, cx + 42 * s, cy + 42 * s,
                       fill='#c43a3a', outline='#7a1a1a', width=2)
    c.create_oval(cx - 42 * s, cy - 22 * s, cx + 42 * s, cy + 8 * s,
                  fill='#f0e0c0', outline='#7a1a1a', width=2)
    c.create_line(cx - 42 * s, cy - 4 * s, cx + 42 * s, cy - 4 * s,
                  fill='#7a1a1a', width=2)
    c.create_line(cx - 50 * s, cy - 55 * s, cx - 18 * s, cy - 16 * s,
                  fill='#d4a574', width=4, capstyle='round')
    c.create_line(cx + 30 * s, cy - 58 * s, cx - 4 * s, cy - 18 * s,
                  fill='#d4a574', width=4, capstyle='round')


def draw_xylophone(c, cx, cy, s):
    colors = ['#ff6b6b', '#ffa94d', '#ffd166', '#06d6a0', '#4cc9f0', '#9775fa']
    widths = [58, 51, 44, 37, 30, 23]
    for i, (col, w) in enumerate(zip(colors, widths)):
        y = cy - 45 * s + i * 15 * s
        c.create_rectangle(cx - w * s, y, cx + w * s, y + 10 * s,
                           fill=col, outline='#2a2a3d', width=2)
        c.create_oval(cx - w * s + 4 * s, y + 3 * s,
                      cx - w * s + 7 * s, y + 6 * s, fill='#2a2a3d', outline='')
        c.create_oval(cx + w * s - 7 * s, y + 3 * s,
                      cx + w * s - 4 * s, y + 6 * s, fill='#2a2a3d', outline='')


def draw_trumpet(c, cx, cy, s):
    c.create_polygon(cx + 30 * s, cy - 4 * s, cx + 30 * s, cy + 22 * s,
                     cx + 65 * s, cy + 38 * s, cx + 65 * s, cy - 26 * s,
                     fill='#f4c430', outline='#a08020', width=2)
    c.create_oval(cx + 60 * s, cy - 28 * s, cx + 70 * s, cy + 40 * s,
                  fill='#f4c430', outline='#a08020', width=2)
    c.create_rectangle(cx - 52 * s, cy + 4 * s, cx + 32 * s, cy + 16 * s,
                       fill='#f4c430', outline='#a08020', width=2)
    for x in [-22, -6, 10]:
        c.create_rectangle(cx + x * s, cy - 12 * s,
                           cx + (x + 7) * s, cy + 4 * s,
                           fill='#e0b020', outline='#a08020', width=2)
        c.create_oval(cx + (x + 1) * s, cy - 18 * s,
                      cx + (x + 6) * s, cy - 10 * s,
                      fill='#fff0a0', outline='#a08020')
    c.create_oval(cx - 62 * s, cy, cx - 48 * s, cy + 20 * s,
                  fill='#d0a020', outline='#a08020', width=2)


def draw_harp(c, cx, cy, s):
    ax, ay = cx - 38 * s, cy - 62 * s
    bx, by = cx - 38 * s, cy + 58 * s
    dx, dy = cx + 52 * s, cy + 32 * s
    c.create_line(ax, ay, bx, by, fill='#d4a574', width=8, capstyle='round')
    c.create_line(bx, by, dx, dy, fill='#c09060', width=10, capstyle='round')
    c.create_line(ax, ay, cx + 5 * s, cy - 50 * s, cx + 35 * s, cy - 15 * s,
                  dx, dy, fill='#d4a574', width=6, capstyle='round', smooth=True)
    for i in range(1, 10):
        t = i / 10
        px = ax + (dx - ax) * t
        py = ay + (dy - ay) * t - 18 * s * math.sin(math.pi * t)
        sx = bx + (dx - bx) * t
        sy = by + (dy - by) * t
        c.create_line(px, py, sx, sy, fill='#f0e9d0', width=1)


INSTRUMENTS = {
    'piano':     {'name': 'Пианино',  'color': '#4dabf7',
                  'draw': draw_piano,     'sound': snd_piano,     'scale': 0.72},
    'guitar':    {'name': 'Гитара',   'color': '#ffa94d',
                  'draw': draw_guitar,    'sound': snd_guitar,    'scale': 0.72},
    'violin':    {'name': 'Скрипка',  'color': '#c77dff',
                  'draw': draw_violin,    'sound': snd_violin,    'scale': 0.75},
    'flute':     {'name': 'Флейта',   'color': '#06d6a0',
                  'draw': draw_flute,     'sound': snd_flute,     'scale': 0.75},
    'drum':      {'name': 'Барабан',  'color': '#ef476f',
                  'draw': draw_drum,      'sound': snd_drum,      'scale': 0.72},
    'xylophone': {'name': 'Ксилофон', 'color': '#ffd166',
                  'draw': draw_xylophone, 'sound': snd_xylophone, 'scale': 0.70},
    'trumpet':   {'name': 'Труба',    'color': '#ff6b6b',
                  'draw': draw_trumpet,   'sound': snd_trumpet,   'scale': 0.70},
    'harp':      {'name': 'Арфа',     'color': '#4cc9f0',
                  'draw': draw_harp,      'sound': snd_harp,      'scale': 0.72},
}


# ============================================================
#  UI HELPERS
# ============================================================
def round_rect(canvas, x1, y1, x2, y2, r, **kw):
    """Скруглённый прямоугольник через smooth-полигон (1 item вместо 6)."""
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
           x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
           x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


# ============================================================
#  GAME
# ============================================================
class Game:
    BG      = '#0a0f1e'
    FG      = '#e9eeff'
    MUTED   = '#7c8ab8'
    GOLD    = '#ffd166'
    CARD_BG = '#161d33'
    GREEN   = '#06d6a0'
    RED     = '#ef476f'

    W, H = 900, 780

    def __init__(self, root):
        self.root = root
        root.title('🎵  Угадай инструмент')
        root.configure(bg=self.BG)
        root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=self.W, height=self.H,
                                bg=self.BG, highlightthickness=0)
        self.canvas.pack()

        # --- state ---
        self.score = 0
        self.streak = 0
        self.best = 0
        self.correct_key = None
        self.cards = []
        self.locked = False
        self.eliminated = set()
        self.hints_left = 1
        self.pulse = 0.0
        self.particles = []
        self._round_tok = 0

        # --- звуки ---
        self.inst_sounds = {}
        if AUDIO:
            for key, info in INSTRUMENTS.items():
                try:
                    self.inst_sounds[key] = info['sound']()
                except Exception as e:
                    print(f'[sound {key}] {e}')
        self.snd_ok = snd_fanfare()
        self.snd_no = snd_buzz()
        self.snd_tick = snd_tick()

        # --- сборка ---
        self._draw_bg()
        self._draw_header()
        self._draw_sound_button()
        self.new_round()
        self._animate()
        self._center()

    # ---------- геометрия/центрирование ----------
    def _center(self):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - self.W) // 2
        y = max(0, (sh - self.H) // 2 - 20)
        self.root.geometry(f'{self.W}x{self.H}+{x}+{y}')

    # ---------- фон ----------
    def _draw_bg(self):
        for _ in range(90):
            x = random.randint(0, self.W)
            y = random.randint(0, self.H)
            r = random.choice([1, 1, 2])
            col = random.choice(['#1a1f3a', '#232a4a', '#2d345a'])
            self.canvas.create_oval(x, y, x + r, y + r, fill=col, outline='')

    # ---------- заголовок ----------
    def _draw_header(self):
        self.canvas.create_text(self.W // 2, 40,
                                text='🎵  Угадай инструмент  🎵',
                                fill=self.GOLD, font=('Segoe UI', 26, 'bold'))
        self.score_txt = self.canvas.create_text(
            self.W - 40, 40, text='', fill=self.FG,
            font=('Segoe UI', 20, 'bold'), anchor='e')
        self._update_score()

    def _update_score(self):
        self.canvas.itemconfig(self.score_txt, text=f'⭐ {self.score}')

    # ---------- кнопка звука ----------
    def _draw_sound_button(self):
        cx, cy, r = self.W // 2, 175, 65
        self.btn_center = (cx, cy, r)

        self.btn_glow = self.canvas.create_oval(0, 0, 0, 0, fill='', outline='')
        self.btn_main = self.canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            fill='#4cc9f0', outline='#7de0ff', width=4, tags=('sndbtn',))
        # иконка динамика
        self.canvas.create_polygon(
            cx - 22, cy - 8, cx - 10, cy - 8, cx + 2, cy - 24,
            cx + 2, cy + 24, cx - 10, cy + 8, cx - 22, cy + 8,
            fill=self.BG, outline='', tags=('sndbtn',))
        self.canvas.create_arc(cx + 6, cy - 22, cx + 36, cy + 22,
                               start=-55, extent=110, style='arc',
                               outline=self.BG, width=4, tags=('sndbtn',))
        self.canvas.create_arc(cx + 6, cy - 36, cx + 52, cy + 36,
                               start=-55, extent=110, style='arc',
                               outline=self.BG, width=4, tags=('sndbtn',))

        self.canvas.create_text(cx, cy + r + 22,
                                text='🔊  Нажми, чтобы послушать снова',
                                fill=self.MUTED, font=('Segoe UI', 13))

        self.canvas.tag_bind('sndbtn', '<Button-1>', lambda e: self.play_sound())
        self.canvas.tag_bind('sndbtn', '<Enter>',
                             lambda e: self.canvas.configure(cursor='hand2'))
        self.canvas.tag_bind('sndbtn', '<Leave>',
                             lambda e: self.canvas.configure(cursor=''))

    # ---------- новый раунд ----------
    def new_round(self):
        self.locked = False
        self.eliminated = set()
        self.hints_left = 1
        self._round_tok += 1
        tok = self._round_tok

        self.canvas.delete('dynamic')
        self.canvas.delete('particle')
        self.particles = []

        keys = list(INSTRUMENTS.keys())
        random.shuffle(keys)
        self.correct_key = keys[0]
        opts = [self.correct_key] + keys[1:4]
        random.shuffle(opts)

        self.question_id = self.canvas.create_text(
            self.W // 2, 310, text='🎧  Что звучит?', fill=self.FG,
            font=('Segoe UI', 20, 'bold'), tags=('dynamic',))

        self._draw_cards(opts)
        self._draw_hint()

        self.root.after(450, lambda: self._auto_play(tok))

    def _auto_play(self, tok):
        if tok == self._round_tok and not self.locked:
            self.play_sound()

    # ---------- карточки ----------
    def _draw_cards(self, opts):
        self.cards = []
        cw, ch, gap = 380, 165, 28
        total = cw * 2 + gap
        sx = (self.W - total) // 2
        sy = 360
        positions = [
            (sx, sy), (sx + cw + gap, sy),
            (sx, sy + ch + gap), (sx + cw + gap, sy + ch + gap),
        ]

        for i, (key, (x, y)) in enumerate(zip(opts, positions)):
            info = INSTRUMENTS[key]
            tag = f'opt{i}'
            before = set(self.canvas.find_all())

            # тень + карточка
            round_rect(self.canvas, x + 4, y + 4, x + cw + 4, y + ch + 4, 22,
                       fill='#000', outline='')
            rid = round_rect(self.canvas, x, y, x + cw, y + ch, 22,
                             fill=self.CARD_BG, outline=info['color'], width=3)

            # иконка
            info['draw'](self.canvas, x + cw // 2, y + 62, info['scale'])

            # название
            nid = self.canvas.create_text(
                x + cw // 2, y + ch - 28, text=info['name'], fill=self.FG,
                font=('Segoe UI', 20, 'bold'))

            # тегируем всё новое
            after = set(self.canvas.find_all())
            for item in after - before:
                self.canvas.addtag_withtag(tag, item)
                self.canvas.addtag_withtag('dynamic', item)

            self.cards.append({
                'tag': tag, 'x': x, 'y': y, 'w': cw, 'h': ch,
                'key': key, 'rect': rid, 'name_id': nid,
            })

            self.canvas.tag_bind(tag, '<Button-1>', lambda e, k=key: self.on_pick(k))
            self.canvas.tag_bind(tag, '<Enter>',
                                 lambda e: self.canvas.configure(cursor='hand2'))
            self.canvas.tag_bind(tag, '<Leave>',
                                 lambda e: self.canvas.configure(cursor=''))

    # ---------- кнопка подсказки ----------
    def _draw_hint(self):
        cx, cy = self.W // 2, 725
        w, h = 240, 48
        color = self.GOLD if self.hints_left > 0 else self.MUTED
        round_rect(self.canvas, cx - w // 2, cy - h // 2,
                   cx + w // 2, cy + h // 2, 24,
                   fill='#1a1a2e', outline=color, width=2,
                   tags=('dynamic', 'hintbtn'))
        self.hint_text = self.canvas.create_text(
            cx, cy, text=f'💡  Подсказка ({self.hints_left})', fill=color,
            font=('Segoe UI', 14, 'bold'),
            tags=('dynamic', 'hintbtn', 'hint_text'))
        self.canvas.tag_bind('hintbtn', '<Button-1>', lambda e: self.use_hint())
        self.canvas.tag_bind('hintbtn', '<Enter>',
                             lambda e: self.canvas.configure(cursor='hand2'))
        self.canvas.tag_bind('hintbtn', '<Leave>',
                             lambda e: self.canvas.configure(cursor=''))

    # ---------- логика ----------
    def play_sound(self):
        if self.locked:
            return
        s = self.inst_sounds.get(self.correct_key)
        if s:
            try:
                s.play()
            except Exception:
                pass
        self.pulse = 1.0

    def use_hint(self):
        if self.locked or self.hints_left <= 0:
            return
        wrong = [c for c in self.cards
                 if c['key'] != self.correct_key and c['key'] not in self.eliminated]
        if not wrong:
            return
        victim = random.choice(wrong)
        self.eliminated.add(victim['key'])
        self.hints_left -= 1

        self.canvas.itemconfig(
            self.hint_text,
            text=f'💡  Подсказка ({self.hints_left})',
            fill=self.MUTED if self.hints_left <= 0 else self.GOLD)

        x, y, w, h = victim['x'], victim['y'], victim['w'], victim['h']
        self.canvas.create_line(x + 30, y + 30, x + w - 30, y + h - 30,
                                fill=self.RED, width=6, tags=('dynamic',))
        self.canvas.create_line(x + w - 30, y + 30, x + 30, y + h - 30,
                                fill=self.RED, width=6, tags=('dynamic',))
        self.canvas.itemconfig(victim['rect'], fill='#0e0e1c')

        if self.snd_tick:
            try:
                self.snd_tick.play()
            except Exception:
                pass

    def on_pick(self, key):
        if self.locked or key in self.eliminated:
            return
        self.locked = True

        correct_card = next(c for c in self.cards if c['key'] == self.correct_key)
        picked_card = next(c for c in self.cards if c['key'] == key)

        if key == self.correct_key:
            self.score += 1
            self.streak += 1
            self.best = max(self.best, self.streak)
            self._update_score()
            if self.snd_ok:
                try:
                    self.snd_ok.play()
                except Exception:
                    pass
            self.canvas.itemconfig(correct_card['rect'], fill='#0a3d2a',
                                   outline=self.GREEN, width=5)
            self.canvas.itemconfig(self.question_id,
                                   text='✅  Правильно!', fill=self.GREEN)
            self._spawn_confetti(correct_card)
        else:
            self.streak = 0
            if self.snd_no:
                try:
                    self.snd_no.play()
                except Exception:
                    pass
            self.canvas.itemconfig(picked_card['rect'], fill='#3d0a1a',
                                   outline=self.RED, width=5)
            self.canvas.itemconfig(correct_card['rect'], fill='#0a3d2a',
                                   outline=self.GREEN, width=5)
            self.canvas.itemconfig(self.question_id,
                                   text='❌  Это не он...', fill=self.RED)

        self.root.after(1800, self.new_round)

    # ---------- частицы ----------
    def _spawn_confetti(self, card):
        cx = card['x'] + card['w'] // 2
        cy = card['y'] + card['h'] // 2
        colors = ['#ff6b6b', '#ffd166', '#06d6a0', '#4cc9f0', '#9775fa', '#f783ac']
        for _ in range(55):
            size = random.uniform(4, 9)
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(3, 11)
            item = self.canvas.create_oval(cx - size, cy - size, cx + size, cy + size,
                                           fill=random.choice(colors),
                                           outline='', tags=('particle',))
            self.particles.append({
                'item': item, 'x': cx, 'y': cy,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed - 3.5,
                'size': size, 'life': 1.7,
            })

    # ---------- основной цикл ----------
    def _animate(self):
        if self.pulse > 0:
            self.pulse = max(0.0, self.pulse - 0.05)
            self._render_btn_pulse()

        if self.particles:
            alive = []
            for p in self.particles:
                p['vy'] += 0.55
                p['vx'] *= 0.99
                p['x'] += p['vx']
                p['y'] += p['vy']
                p['life'] -= 0.02
                if p['life'] <= 0 or p['y'] > self.H + 40:
                    try:
                        self.canvas.delete(p['item'])
                    except Exception:
                        pass
                else:
                    try:
                        self.canvas.coords(p['item'],
                                           p['x'] - p['size'], p['y'] - p['size'],
                                           p['x'] + p['size'], p['y'] + p['size'])
                        alive.append(p)
                    except Exception:
                        pass
            self.particles = alive

        self.root.after(16, self._animate)

    def _render_btn_pulse(self):
        cx, cy, r = self.btn_center
        p = self.pulse
        if p > 0.02:
            gr = r + 18 + 26 * p
            self.canvas.coords(self.btn_glow, cx - gr, cy - gr, cx + gr, cy + gr)
            self.canvas.itemconfig(self.btn_glow, fill='#1e4a6a', outline='')
        else:
            self.canvas.coords(self.btn_glow, 0, 0, 0, 0)


# ============================================================
def main():
    root = tk.Tk()
    Game(root)
    root.mainloop()


if __name__ == '__main__':
    main()