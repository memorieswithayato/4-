"""
🔊 Найди звук — детская игра на слух.

Запуск:  python find_sound.py
Требуется: pip install pygame

Как играть:
  • Прозвучит звук (животное или инструмент).
  • Кликни по картинке, которая издаёт этот звук.
  • Управление:
      🔊 Ещё раз / ПРОБЕЛ — повторить звук
      💡 Подсказка / H    — текстовая подсказка и убрать один неверный вариант
      🐾 Животные / 🎵 Инструменты — переключить режим (TAB)
      клавиши 1, 2, 3  — выбрать вариант
      ESC — выход
"""

import math
import random
import array
import sys

import pygame

# ============================================================
#  ИНИЦИАЛИЗАЦИЯ
# ============================================================

pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
pygame.mixer.set_num_channels(32)

SR = 44100
WIDTH, HEIGHT = 1020, 780
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Найди звук")
clock = pygame.time.Clock()

# ============================================================
#  СИНТЕЗ ЗВУКОВ
# ============================================================

def to_sound(samples):
    arr = array.array('h', [int(max(-1.0, min(1.0, s)) * 32000) for s in samples])
    return pygame.mixer.Sound(buffer=arr.tobytes())


def _smooth_env(t, attack, release, dur):
    a = min(1.0, t / max(attack, 1e-4))
    r = max(0.0, min(1.0, (dur - t) / max(release, 1e-4)))
    return a * r


# ---------- ЖИВОТНЫЕ ----------

def make_meow():
    dur = 0.65
    n = int(SR * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        if t < 0.15:
            f = 400 + (660 - 400) * (t / 0.15)
        else:
            f = 660 - (660 - 340) * ((t - 0.15) / (dur - 0.15))
        f *= 1 + 0.03 * math.sin(2 * math.pi * 18 * t)
        phase += 2 * math.pi * f / SR
        env = _smooth_env(t, 0.03, 0.25, dur) * math.exp(-t * 1.2)
        s = math.sin(phase) + 0.6 * math.sin(2 * phase) \
            + 0.3 * math.sin(3 * phase) + 0.15 * math.sin(4 * phase)
        out.append(s / 2.05 * env * 0.6)
    return to_sound(out)


def make_bark():
    dur = 0.35
    n = int(SR * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        if t < 0.12:
            local, active = t, True
        elif t < 0.15:
            active, local = False, 0
        else:
            local, active = t - 0.15, True
        if not active:
            out.append(0.0)
            continue
        f = 180 * math.exp(-local * 8) + 90
        phase += 2 * math.pi * f / SR
        env = math.exp(-local * 22)
        noise = random.random() * 2 - 1
        s = noise * 0.35 + math.sin(phase) * 0.7
        out.append(s * env * 0.85)
    return to_sound(out)


def make_moo():
    dur = 0.95
    n = int(SR * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        f = 110 + 25 * math.sin(2 * math.pi * 2 * t)
        phase += 2 * math.pi * f / SR
        env = _smooth_env(t, 0.15, 0.35, dur)
        s = math.sin(phase) + 0.55 * math.sin(2 * phase) + 0.3 * math.sin(3 * phase)
        out.append(s / 1.85 * env * 0.65)
    return to_sound(out)


def make_quack():
    dur = 0.22
    n = int(SR * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        f = 320 - 110 * (t / dur)
        phase += 2 * math.pi * f / SR
        env = _smooth_env(t, 0.02, 0.08, dur) * math.exp(-t * 6)
        s = 0.0
        for h in range(1, 8):
            s += math.sin(phase * h) / h
        out.append(s * env * 0.8)
    return to_sound(out)


def make_croak():
    dur = 0.55
    n = int(SR * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        phase += 2 * math.pi * 140 / SR
        am = 0.45 + 0.55 * abs(math.sin(2 * math.pi * 22 * t))
        env = _smooth_env(t, 0.03, 0.18, dur)
        s = math.sin(phase) + 0.5 * math.sin(2 * phase) + 0.3 * math.sin(3 * phase)
        out.append(s / 1.8 * env * am * 0.75)
    return to_sound(out)


def make_chirp():
    dur = 0.62
    n = int(SR * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        in_chirp, local = False, 0.0
        for start in (0.0, 0.20, 0.40):
            if start <= t < start + 0.12:
                in_chirp, local = True, t - start
                break
        if not in_chirp:
            out.append(0.0)
            continue
        f = 2500 + 1500 * (local / 0.12)
        phase += 2 * math.pi * f / SR
        env = math.exp(-local * 15)
        out.append(math.sin(phase) * env * 0.55)
    return to_sound(out)


# ---------- ИНСТРУМЕНТЫ ----------

def make_drum():
    dur = 0.4
    n = int(SR * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        f = 160 * math.exp(-t * 15) + 50
        phase += 2 * math.pi * f / SR
        env = math.exp(-t * 8)
        out.append(math.sin(phase) * env * 0.9)
    return to_sound(out)


def make_bell():
    dur = 1.5
    n = int(SR * dur)
    out = [0.0] * n
    for mult, amp, decay in [(1.0, 1.0, 2.0), (2.01, 0.5, 2.5),
                              (2.98, 0.3, 3.5), (5.4, 0.13, 5.0)]:
        w = 2 * math.pi * 660 * mult
        for i in range(n):
            t = i / SR
            out[i] += math.sin(w * t) * amp * math.exp(-t * decay)
    peak = max(abs(s) for s in out) or 1.0
    return to_sound([s / peak * 0.5 for s in out])


def make_flute():
    dur = 0.9
    n = int(SR * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        f = 660 * (1 + 0.005 * math.sin(2 * math.pi * 5 * t))
        phase += 2 * math.pi * f / SR
        env = _smooth_env(t, 0.05, 0.2, dur)
        breath = (random.random() * 2 - 1) * 0.05 * env
        s = math.sin(phase) + 0.15 * math.sin(2 * phase)
        out.append(s * env * 0.5 + breath)
    return to_sound(out)


def make_piano():
    dur = 1.3
    n = int(SR * dur)
    out = [0.0] * n
    f0 = 440
    for h, amp, decay in [(1, 1.0, 2.5), (2, 0.55, 3.5), (3, 0.3, 5),
                           (4, 0.15, 7), (5, 0.08, 9), (6, 0.04, 12)]:
        w = 2 * math.pi * f0 * h
        for i in range(n):
            t = i / SR
            attack = min(1, t * 90)
            out[i] += math.sin(w * t) * amp * attack * math.exp(-t * decay)
    peak = max(abs(s) for s in out) or 1.0
    return to_sound([s / peak * 0.55 for s in out])


def make_guitar():
    dur = 1.4
    n = int(SR * dur)
    out = [0.0] * n
    f0 = 330
    for h, amp, decay in [(1, 1.0, 3.5), (2, 0.5, 4.5), (3, 0.25, 5.5),
                           (4, 0.12, 7), (5, 0.06, 9)]:
        w = 2 * math.pi * f0 * h
        for i in range(n):
            t = i / SR
            attack = min(1, t * 200)
            out[i] += math.sin(w * t) * amp * attack * math.exp(-t * decay)
    peak = max(abs(s) for s in out) or 1.0
    return to_sound([s / peak * 0.5 for s in out])


def make_xylo():
    dur = 0.65
    n = int(SR * dur)
    out = [0.0] * n
    f0 = 880
    for h, amp, decay in [(1, 1.0, 8), (3.0, 0.4, 10), (5.5, 0.15, 14)]:
        w = 2 * math.pi * f0 * h
        for i in range(n):
            t = i / SR
            out[i] += math.sin(w * t) * amp * math.exp(-t * decay)
    peak = max(abs(s) for s in out) or 1.0
    return to_sound([s / peak * 0.5 for s in out])


# ---------- ОБРАТНАЯ СВЯЗЬ ----------

def make_correct():
    notes = [523.25, 659.25, 783.99, 1046.50]
    step = int(SR * 0.11)
    dur = len(notes) * step / SR + 0.4
    n = int(SR * dur)
    out = []
    for i in range(n):
        t = i / SR
        idx = min(len(notes) - 1, i // step)
        f = notes[idx]
        local_t = (i % step) / SR
        env = math.exp(-local_t * 9)
        out.append(math.sin(2 * math.pi * f * t) * env * 0.35)
    return to_sound(out)


def make_wrong():
    dur = 0.5
    n = int(SR * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        f = 220 - 70 * (t / dur)
        phase += 2 * math.pi * f / SR
        env = _smooth_env(t, 0.02, 0.2, dur)
        s = math.sin(phase) + 0.5 * math.sin(2 * phase)
        out.append(s * env * 0.4)
    return to_sound(out)


def make_click():
    n = int(SR * 0.05)
    out = []
    for i in range(n):
        t = i / SR
        out.append(math.sin(2 * math.pi * 1500 * t) * math.exp(-t * 55) * 0.25)
    return to_sound(out)


print("Загрузка звуков...")
ANIMALS = [
    {'name': 'Кошка',    'hint': '«Мяу!» — я люблю молоко.',
     'draw': lambda s, r: draw_cat(s, r),  'sound': make_meow()},
    {'name': 'Собака',   'hint': '«Гав-гав!» — я охраняю дом.',
     'draw': lambda s, r: draw_dog(s, r),  'sound': make_bark()},
    {'name': 'Корова',   'hint': '«Му-у!» — я даю молоко.',
     'draw': lambda s, r: draw_cow(s, r),  'sound': make_moo()},
    {'name': 'Утка',     'hint': '«Кря-кря!» — я плаваю в пруду.',
     'draw': lambda s, r: draw_duck(s, r), 'sound': make_quack()},
    {'name': 'Лягушка',  'hint': '«Ква-ква!» — я сижу на кувшинке.',
     'draw': lambda s, r: draw_frog(s, r), 'sound': make_croak()},
    {'name': 'Птичка',   'hint': '«Чик-чирик!» — я летаю в небе.',
     'draw': lambda s, r: draw_bird(s, r), 'sound': make_chirp()},
]

INSTRUMENTS = [
    {'name': 'Барабан',     'hint': '«Бум-бум!» — я громко стучу.',
     'draw': lambda s, r: draw_drum(s, r),  'sound': make_drum()},
    {'name': 'Колокольчик', 'hint': '«Дзынь-дзынь!» — я звонко звоню.',
     'draw': lambda s, r: draw_bell(s, r),  'sound': make_bell()},
    {'name': 'Дудочка',     'hint': '«Ту-ту!» — я играю нежно.',
     'draw': lambda s, r: draw_flute(s, r), 'sound': make_flute()},
    {'name': 'Пианино',     'hint': 'Я играю красивые мелодии.',
     'draw': lambda s, r: draw_piano(s, r), 'sound': make_piano()},
    {'name': 'Гитара',      'hint': 'Я звучу струнами.',
     'draw': lambda s, r: draw_guitar(s, r),'sound': make_guitar()},
    {'name': 'Ксилофон',    'hint': 'Я весело стучу по цветным пластинкам.',
     'draw': lambda s, r: draw_xylo(s, r),  'sound': make_xylo()},
]

correct_sound = make_correct()
wrong_sound   = make_wrong()
click_sound   = make_click()
print("Готово!")

# ============================================================
#  РИСОВАНИЕ КАРТИНОК (эмодзи заменены на фигуры pygame)
# ============================================================

OUTLINE = (35, 35, 55)


def draw_cat(s, r):
    cx, cy = r.center
    w = min(r.width, r.height)
    ear_l = [(cx - w * .32, cy - w * .10), (cx - w * .16, cy - w * .38),
             (cx - w * .02, cy - w * .14)]
    ear_r = [(cx + w * .32, cy - w * .10), (cx + w * .16, cy - w * .38),
             (cx + w * .02, cy - w * .14)]
    for e in (ear_l, ear_r):
        pygame.draw.polygon(s, (255, 180, 140), e)
        pygame.draw.polygon(s, OUTLINE, e, 3)
    pygame.draw.circle(s, (255, 205, 160), (cx, cy), int(w * .30))
    pygame.draw.circle(s, OUTLINE, (cx, cy), int(w * .30), 3)
    ex, ey = w * .11, -w * .05
    for sx in (-ex, ex):
        pygame.draw.circle(s, (255, 255, 255), (int(cx + sx), int(cy + ey)),
                           int(w * .055))
        pygame.draw.circle(s, OUTLINE, (int(cx + sx), int(cy + ey)),
                           int(w * .028))
    ny = cy + w * .06
    pygame.draw.polygon(s, (255, 120, 150),
                        [(cx, ny + w * .03), (cx - w * .03, ny),
                         (cx + w * .03, ny)])
    for dy in (-w * .03, 0, w * .03):
        pygame.draw.line(s, OUTLINE, (cx - w * .32, cy + w * .06 + dy),
                         (cx - w * .14, cy + w * .06 + dy), 2)
        pygame.draw.line(s, OUTLINE, (cx + w * .32, cy + w * .06 + dy),
                         (cx + w * .14, cy + w * .06 + dy), 2)


def draw_dog(s, r):
    cx, cy = r.center
    w = min(r.width, r.height)
    for sx in (-w * .31, w * .31):
        pygame.draw.ellipse(s, (150, 90, 60),
                            pygame.Rect(int(cx + sx - w * .10),
                                        int(cy - w * .20),
                                        int(w * .20), int(w * .42)))
        pygame.draw.ellipse(s, OUTLINE,
                            pygame.Rect(int(cx + sx - w * .10),
                                        int(cy - w * .20),
                                        int(w * .20), int(w * .42)), 3)
    pygame.draw.circle(s, (200, 140, 90), (cx, cy), int(w * .30))
    pygame.draw.circle(s, OUTLINE, (cx, cy), int(w * .30), 3)
    mz = pygame.Rect(int(cx - w * .16), int(cy + w * .02),
                     int(w * .32), int(w * .22))
    pygame.draw.ellipse(s, (245, 220, 190), mz)
    pygame.draw.ellipse(s, OUTLINE, mz, 2)
    pygame.draw.circle(s, OUTLINE, (cx, int(cy + w * .05)), int(w * .04))
    for sx in (-w * .10, w * .10):
        pygame.draw.circle(s, OUTLINE, (int(cx + sx), int(cy - w * .08)),
                           int(w * .035))


def draw_cow(s, r):
    cx, cy = r.center
    w = min(r.width, r.height)
    for pts in (
        [(cx - w * .22, cy - w * .24), (cx - w * .32, cy - w * .40),
         (cx - w * .14, cy - w * .28)],
        [(cx + w * .22, cy - w * .24), (cx + w * .32, cy - w * .40),
         (cx + w * .14, cy - w * .28)],
    ):
        pygame.draw.polygon(s, (220, 200, 160), pts)
        pygame.draw.polygon(s, OUTLINE, pts, 2)
    for sx in (-w * .35, w * .35):
        pygame.draw.ellipse(s, (150, 110, 80),
                            pygame.Rect(int(cx + sx - w * .09),
                                        int(cy - w * .18),
                                        int(w * .18), int(w * .12)))
    pygame.draw.circle(s, (250, 250, 245), (cx, cy), int(w * .30))
    pygame.draw.circle(s, OUTLINE, (cx, cy), int(w * .30), 3)
    pygame.draw.circle(s, (60, 60, 80),
                       (int(cx - w * .18), int(cy - w * .10)), int(w * .05))
    pygame.draw.circle(s, (60, 60, 80),
                       (int(cx + w * .15), int(cy - w * .16)), int(w * .04))
    mz = pygame.Rect(int(cx - w * .16), int(cy + w * .04),
                     int(w * .32), int(w * .18))
    pygame.draw.ellipse(s, (255, 180, 180), mz)
    pygame.draw.ellipse(s, OUTLINE, mz, 2)
    pygame.draw.circle(s, (120, 60, 60),
                       (int(cx - w * .05), int(cy + w * .12)), int(w * .02))
    pygame.draw.circle(s, (120, 60, 60),
                       (int(cx + w * .05), int(cy + w * .12)), int(w * .02))
    for sx in (-w * .12, w * .12):
        pygame.draw.circle(s, OUTLINE, (int(cx + sx), int(cy - w * .06)),
                           int(w * .035))


def draw_duck(s, r):
    cx, cy = r.center
    w = min(r.width, r.height)
    body = pygame.Rect(int(cx - w * .40), int(cy - w * .05),
                       int(w * .70), int(w * .40))
    pygame.draw.ellipse(s, (255, 220, 80), body)
    pygame.draw.ellipse(s, OUTLINE, body, 3)
    pygame.draw.ellipse(s, (240, 190, 60),
                        pygame.Rect(int(cx - w * .20), int(cy + w * .05),
                                    int(w * .35), int(w * .18)))
    hd = (int(cx + w * .20), int(cy - w * .20))
    pygame.draw.circle(s, (255, 220, 80), hd, int(w * .18))
    pygame.draw.circle(s, OUTLINE, hd, int(w * .18), 3)
    beak = [(cx + w * .36, cy - w * .20), (cx + w * .58, cy - w * .18),
            (cx + w * .36, cy - w * .10)]
    pygame.draw.polygon(s, (255, 140, 40), beak)
    pygame.draw.polygon(s, OUTLINE, beak, 2)
    pygame.draw.circle(s, OUTLINE, (int(cx + w * .22), int(cy - w * .24)),
                       int(w * .025))


def draw_frog(s, r):
    cx, cy = r.center
    w = min(r.width, r.height)
    for sx in (-w * .15, w * .15):
        pygame.draw.circle(s, (110, 210, 110),
                           (int(cx + sx), int(cy - w * .20)), int(w * .13))
        pygame.draw.circle(s, OUTLINE,
                           (int(cx + sx), int(cy - w * .20)), int(w * .13), 3)
        pygame.draw.circle(s, (255, 255, 255),
                           (int(cx + sx), int(cy - w * .22)), int(w * .07))
        pygame.draw.circle(s, OUTLINE,
                           (int(cx + sx), int(cy - w * .22)), int(w * .035))
    body = pygame.Rect(int(cx - w * .35), int(cy - w * .12),
                       int(w * .70), int(w * .50))
    pygame.draw.ellipse(s, (110, 210, 110), body)
    pygame.draw.ellipse(s, OUTLINE, body, 3)
    pygame.draw.arc(s, OUTLINE,
                    pygame.Rect(int(cx - w * .22), int(cy + w * .02),
                                int(w * .44), int(w * .20)), 3.5, 6.0, 3)


def draw_bird(s, r):
    cx, cy = r.center
    w = min(r.width, r.height)
    body = pygame.Rect(int(cx - w * .32), int(cy - w * .15),
                       int(w * .60), int(w * .45))
    pygame.draw.ellipse(s, (100, 180, 255), body)
    pygame.draw.ellipse(s, OUTLINE, body, 3)
    pygame.draw.ellipse(s, (60, 140, 220),
                        pygame.Rect(int(cx - w * .18), int(cy - w * .05),
                                    int(w * .30), int(w * .22)))
    hd = (int(cx + w * .24), int(cy - w * .18))
    pygame.draw.circle(s, (100, 180, 255), hd, int(w * .16))
    pygame.draw.circle(s, OUTLINE, hd, int(w * .16), 3)
    beak = [(cx + w * .38, cy - w * .20), (cx + w * .56, cy - w * .14),
            (cx + w * .38, cy - w * .08)]
    pygame.draw.polygon(s, (255, 180, 50), beak)
    pygame.draw.polygon(s, OUTLINE, beak, 2)
    pygame.draw.circle(s, OUTLINE, (int(cx + w * .26), int(cy - w * .22)),
                       int(w * .03))
    tail = [(cx - w * .30, cy + w * .05), (cx - w * .50, cy - w * .10),
            (cx - w * .48, cy + w * .15)]
    pygame.draw.polygon(s, (60, 140, 220), tail)
    pygame.draw.polygon(s, OUTLINE, tail, 3)


def draw_drum(s, r):
    cx, cy = r.center
    w = min(r.width, r.height)
    body = pygame.Rect(int(cx - w * .32), int(cy - w * .22),
                       int(w * .64), int(w * .52))
    pygame.draw.rect(s, (220, 90, 60), body, border_radius=8)
    pygame.draw.rect(s, OUTLINE, body, 3, border_radius=8)
    top = pygame.Rect(body.x, body.y - int(w * .06), body.w, int(w * .16))
    pygame.draw.ellipse(s, (250, 220, 180), top)
    pygame.draw.ellipse(s, OUTLINE, top, 3)
    pygame.draw.line(s, OUTLINE, (body.x + 4, body.centery),
                     (body.right - 4, body.centery), 2)
    pygame.draw.line(s, (150, 90, 50), (cx - w * .40, cy - w * .32),
                     (cx - w * .10, cy - w * .08), 6)
    pygame.draw.line(s, (150, 90, 50), (cx + w * .40, cy - w * .32),
                     (cx + w * .10, cy - w * .08), 6)


def draw_bell(s, r):
    cx, cy = r.center
    w = min(r.width, r.height)
    pygame.draw.circle(s, (255, 210, 60), (cx, int(cy - w * .30)), int(w * .06))
    pts = [(cx - w * .26, cy + w * .18), (cx - w * .16, cy - w * .22),
           (cx + w * .16, cy - w * .22), (cx + w * .26, cy + w * .18)]
    pygame.draw.polygon(s, (255, 210, 60), pts)
    pygame.draw.polygon(s, OUTLINE, pts, 3)
    rim = pygame.Rect(int(cx - w * .30), int(cy + w * .12),
                      int(w * .60), int(w * .14))
    pygame.draw.ellipse(s, (255, 180, 40), rim)
    pygame.draw.ellipse(s, OUTLINE, rim, 3)
    pygame.draw.circle(s, OUTLINE, (cx, int(cy + w * .22)), int(w * .05))


def draw_flute(s, r):
    cx, cy = r.center
    w = min(r.width, r.height)
    tube = pygame.Rect(int(cx - w * .42), int(cy - w * .06),
                       int(w * .84), int(w * .14))
    pygame.draw.rect(s, (200, 170, 110), tube, border_radius=8)
    pygame.draw.rect(s, OUTLINE, tube, 3, border_radius=8)
    for i in range(5):
        x = tube.x + int(w * .18) + i * int(w * .13)
        pygame.draw.circle(s, OUTLINE, (x, tube.centery), int(w * .025))
    mouth = pygame.Rect(tube.right - int(w * .06), tube.y - 3,
                        int(w * .06), tube.h + 6)
    pygame.draw.rect(s, (160, 130, 80), mouth, border_radius=4)
    pygame.draw.rect(s, OUTLINE, mouth, 2, border_radius=4)


def draw_piano(s, r):
    cx, cy = r.center
    w = min(r.width, r.height)
    body = pygame.Rect(int(cx - w * .40), int(cy - w * .28),
                       int(w * .80), int(w * .56))
    pygame.draw.rect(s, (60, 60, 80), body, border_radius=10)
    pygame.draw.rect(s, OUTLINE, body, 3, border_radius=10)
    n = 7
    kw = body.w / n
    for i in range(n):
        kr = pygame.Rect(int(body.x + i * kw) + 3, body.y + 5,
                         int(kw) - 6, body.h - 10)
        pygame.draw.rect(s, (250, 250, 250), kr)
        pygame.draw.rect(s, (60, 60, 80), kr, 2)
    for i in (0, 1, 3, 4, 5):
        bx = int(body.x + (i + 1) * kw)
        br = pygame.Rect(bx - int(kw * .32), body.y + 5,
                         int(kw * .64), int(body.h * .55))
        pygame.draw.rect(s, (25, 25, 40), br, border_radius=4)


def draw_guitar(s, r):
    cx, cy = r.center
    w = min(r.width, r.height)
    neck = pygame.Rect(int(cx - w * .06), int(cy - w * .42),
                       int(w * .12), int(w * .42))
    pygame.draw.rect(s, (120, 70, 40), neck)
    pygame.draw.rect(s, OUTLINE, neck, 2)
    head = pygame.Rect(int(cx - w * .11), int(cy - w * .50),
                       int(w * .22), int(w * .10))
    pygame.draw.rect(s, (80, 50, 30), head, border_radius=4)
    pygame.draw.rect(s, OUTLINE, head, 2, border_radius=4)
    b1 = pygame.Rect(int(cx - w * .30), int(cy - w * .05),
                     int(w * .60), int(w * .46))
    b2 = pygame.Rect(int(cx - w * .24), int(cy + w * .05),
                     int(w * .48), int(w * .34))
    pygame.draw.ellipse(s, (200, 140, 80), b1)
    pygame.draw.ellipse(s, (200, 140, 80), b2)
    pygame.draw.ellipse(s, OUTLINE, b1, 3)
    pygame.draw.ellipse(s, OUTLINE, b2, 3)
    pygame.draw.circle(s, (60, 30, 20), (cx, int(cy + w * .14)),
                       int(w * .07))
    for dx in (-6, 0, 6):
        pygame.draw.line(s, (240, 240, 240),
                         (cx + dx, int(cy - w * .42)),
                         (cx + dx, int(cy + w * .30)), 1)


def draw_xylo(s, r):
    cx, cy = r.center
    w = min(r.width, r.height)
    colors = [(255, 90, 90), (255, 180, 60), (255, 240, 70),
              (130, 220, 130), (90, 180, 255), (180, 130, 255)]
    n = 6
    bar_w = w * .75 / n
    for i in range(n):
        x = int(cx - w * .375 + i * bar_w)
        h = int(w * .35 - i * 2)
        y = int(cy - w * .10)
        rr = pygame.Rect(x + 2, y, int(bar_w) - 4, h)
        pygame.draw.rect(s, colors[i], rr, border_radius=6)
        pygame.draw.rect(s, OUTLINE, rr, 2, border_radius=6)
    pygame.draw.line(s, (120, 70, 40), (cx - w * .36, cy + w * .28),
                     (cx - w * .10, cy + w * .10), 5)
    pygame.draw.circle(s, (255, 90, 90),
                       (int(cx - w * .10), int(cy + w * .10)), int(w * .045))
    pygame.draw.line(s, (120, 70, 40), (cx + w * .36, cy + w * .28),
                     (cx + w * .10, cy + w * .10), 5)
    pygame.draw.circle(s, (90, 180, 255),
                       (int(cx + w * .10), int(cy + w * .10)), int(w * .045))


# ============================================================
#  ШРИФТЫ
# ============================================================

_font_cache = {}


def get_font(size, bold=False):
    key = (size, bold)
    if key not in _font_cache:
        for name in ("comicsansms", "segoeui", "arial", "dejavusans"):
            try:
                _font_cache[key] = pygame.font.SysFont(name, size, bold=bold)
                break
            except Exception:
                pass
        else:
            _font_cache[key] = pygame.font.Font(None, size + 6)
    return _font_cache[key]


font_title   = get_font(42, bold=True)
font_sub     = get_font(19)
font_small   = get_font(17, bold=True)
font_card    = get_font(24, bold=True)
font_button  = get_font(22, bold=True)
font_score   = get_font(24, bold=True)
font_hint    = get_font(22, bold=True)

# ============================================================
#  РАЗМЕТКА
# ============================================================

CARD_W, CARD_H = 240, 240
CARD_GAP = 40
total_cards_w = 3 * CARD_W + 2 * CARD_GAP
cards_y = 235
start_x = (WIDTH - total_cards_w) // 2
CARD_RECTS = [
    pygame.Rect(start_x + i * (CARD_W + CARD_GAP), cards_y, CARD_W, CARD_H)
    for i in range(3)
]

BTN_REPEAT = pygame.Rect(300, 520, 200, 64)
BTN_HINT   = pygame.Rect(520, 520, 200, 64)

BTN_MODE_ANIMALS = pygame.Rect(30, 25, 210, 52)
BTN_MODE_INSTR   = pygame.Rect(250, 25, 240, 52)
SCORE_RECT       = pygame.Rect(WIDTH - 230, 25, 200, 52)

# ============================================================
#  СОСТОЯНИЕ ИГРЫ
# ============================================================

state = {
    'mode': 'animals',
    'score': 0,
    'streak': 0,
    'best_streak': 0,
    'target': 0,
    'options': [],
    'wrong_picked': set(),
    'round_start': 0,
    'round_over': False,
    'next_round_at': 0,
    'hint_text': None,
    'hint_used': False,
    'sound_playing_until': 0,
}

effects = []   # [x, y, t0, char, color]
NOTE_CHARS = ['♪', '♫', '♬', '♩', '✦']


def get_items():
    return ANIMALS if state['mode'] == 'animals' else INSTRUMENTS


def spawn_note(x, y, color):
    effects.append([x, y, pygame.time.get_ticks(),
                    random.choice(NOTE_CHARS), color])


def update_effects(now):
    for e in effects[:]:
        if now - e[2] > 1200:
            effects.remove(e)


def draw_effects(surface, now):
    for x, y, t0, ch, color in effects:
        t = (now - t0) / 1200
        cy = y - 200 * t
        alpha = int(255 * max(0.0, (1 - t)) ** 0.6)
        size = int(30 + 18 * t)
        fnt = get_font(size, bold=True)
        img = fnt.render(ch, True, color)
        img.set_alpha(alpha)
        surface.blit(img, (x - img.get_width() // 2,
                           cy - img.get_height() // 2))


# ============================================================
#  ЛОГИКА РАУНДА
# ============================================================

def play_current_sound():
    items = get_items()
    snd = items[state['target']]['sound']
    snd.play()
    dur_ms = int(snd.get_length() * 1000)
    state['sound_playing_until'] = pygame.time.get_ticks() + dur_ms


def new_round():
    items = get_items()
    n = len(items)
    state['target'] = random.randrange(n)
    others = [i for i in range(n) if i != state['target']]
    random.shuffle(others)
    opts = [state['target']] + others[:2]
    random.shuffle(opts)
    state['options'] = opts
    state['wrong_picked'] = set()
    state['round_start'] = pygame.time.get_ticks()
    state['round_over'] = False
    state['next_round_at'] = 0
    state['hint_text'] = None
    state['hint_used'] = False
    play_current_sound()


def repeat_sound():
    if state['round_over']:
        return
    play_current_sound()


def show_hint():
    """Показывает текстовую подсказку и убирает один неверный вариант."""
    if state['round_over']:
        return
    items = get_items()
    state['hint_text'] = items[state['target']]['hint']
    # Убираем один неверный вариант (если ещё есть)
    candidates = [i for i, o in enumerate(state['options'])
                  if o != state['target'] and i not in state['wrong_picked']]
    if candidates:
        i = random.choice(candidates)
        state['wrong_picked'].add(i)
        click_sound.play()
    state['hint_used'] = True


def pick_option(opt_idx):
    if state['round_over'] or opt_idx in state['wrong_picked']:
        return
    items = get_items()
    picked = state['options'][opt_idx]
    if picked == state['target']:
        # --- правильный ответ ---
        state['score'] += 1
        state['streak'] += 1
        if state['streak'] > state['best_streak']:
            state['best_streak'] = state['streak']
        correct_sound.play()
        state['round_over'] = True
        state['next_round_at'] = pygame.time.get_ticks() + 1700
        # фейерверк ноток
        card = CARD_RECTS[opt_idx]
        for _ in range(10):
            x = random.randint(card.left, card.right)
            y = random.randint(card.top, card.bottom)
            spawn_note(x, y, random.choice([
                (255, 220, 100), (255, 150, 200),
                (150, 220, 255), (200, 255, 150)]))
    else:
        # --- ошибка ---
        state['streak'] = 0
        wrong_sound.play()
        state['wrong_picked'].add(opt_idx)
        state['shake_start'] = pygame.time.get_ticks()
        state['shake_card'] = opt_idx
        # после двух ошибок — автоматическая подсказка
        if len(state['wrong_picked']) >= 2 and not state['hint_text']:
            state['hint_text'] = items[state['target']]['hint']


def toggle_mode():
    state['mode'] = 'instruments' if state['mode'] == 'animals' else 'animals'
    click_sound.play()
    new_round()


# ============================================================
#  ОБРАБОТКА КЛИКА
# ============================================================

def handle_click(pos):
    if BTN_REPEAT.collidepoint(pos):
        repeat_sound()
        return
    if BTN_HINT.collidepoint(pos):
        show_hint()
        return
    if BTN_MODE_ANIMALS.collidepoint(pos) and state['mode'] != 'animals':
        toggle_mode()
        return
    if BTN_MODE_INSTR.collidepoint(pos) and state['mode'] != 'instruments':
        toggle_mode()
        return
    for i, rect in enumerate(CARD_RECTS):
        if rect.collidepoint(pos):
            pick_option(i)
            return


# ============================================================
#  ОТРИСОВКА
# ============================================================

def get_shake_offset(idx, now):
    if state.get('shake_card') != idx:
        return 0
    t = (now - state['shake_start']) / 400
    if t >= 1:
        state['shake_card'] = None
        return 0
    return int(math.sin(t * 32) * 14 * (1 - t))


def draw_card(surface, rect, item, idx, now):
    is_wrong = idx in state['wrong_picked']
    is_correct = (state['round_over']
                  and idx == state['options'].index(state['target']))

    shake = get_shake_offset(idx, now)
    r = rect.move(shake, 0)

    # тень
    pygame.draw.rect(surface, (0, 0, 0), r.move(0, 8), border_radius=26)

    # фон карточки
    if is_wrong:
        base = (95, 85, 115)
    elif is_correct:
        pulse = 0.5 + 0.5 * math.sin(now / 120)
        base = (int(110 + 60 * pulse), int(230 + 20 * pulse), int(130 + 40 * pulse))
    else:
        base = (255, 250, 240)

    pygame.draw.rect(surface, base, r, border_radius=26)

    # обводка
    if is_correct:
        pygame.draw.rect(surface, (60, 200, 90), r, 5, border_radius=26)
        # лёгкое свечение
        glow = pygame.Surface((r.w + 30, r.h + 30), pygame.SRCALPHA)
        pygame.draw.rect(glow, (60, 220, 90, 60),
                         glow.get_rect(), border_radius=36)
        surface.blit(glow, (r.x - 15, r.y - 15))
        pygame.draw.rect(surface, base, r, border_radius=26)
        pygame.draw.rect(surface, (60, 200, 90), r, 5, border_radius=26)
    elif is_wrong:
        pygame.draw.rect(surface, (180, 60, 70), r, 4, border_radius=26)
    else:
        pygame.draw.rect(surface, (70, 55, 110), r, 4, border_radius=26)

    # картинка внутри
    icon_rect = pygame.Rect(r.x + 18, r.y + 14, r.w - 36, r.h - 72)
    try:
        item['draw'](surface, icon_rect)
    except Exception:
        pass

    # подпись
    color = (230, 220, 245) if is_wrong else (55, 45, 85)
    name = font_card.render(item['name'], True, color)
    surface.blit(name, (r.centerx - name.get_width() // 2,
                        r.bottom - 56))

    # крестик на неверной
    if is_wrong:
        pad = 30
        overlay = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 70))
        surface.blit(overlay, r.topleft)
        pygame.draw.line(surface, (255, 90, 100),
                         (r.x + pad, r.y + pad),
                         (r.right - pad, r.bottom - pad), 9)
        pygame.draw.line(surface, (255, 90, 100),
                         (r.right - pad, r.y + pad),
                         (r.x + pad, r.bottom - pad), 9)
        pygame.draw.line(surface, (255, 255, 255),
                         (r.x + pad, r.y + pad),
                         (r.right - pad, r.bottom - pad), 3)
        pygame.draw.line(surface, (255, 255, 255),
                         (r.right - pad, r.y + pad),
                         (r.x + pad, r.bottom - pad), 3)


def draw_sound_wave(surface, cx, cy, now):
    if now > state['sound_playing_until']:
        return
    t = now / 130.0
    for i in range(7):
        h = 8 + 26 * abs(math.sin(t + i * 0.6))
        x = cx + (i - 3) * 14
        pygame.draw.rect(surface, (255, 220, 100),
                         (x - 4, cy - h / 2, 8, h), border_radius=4)
        pygame.draw.rect(surface, (200, 160, 40),
                         (x - 4, cy - h / 2, 8, h), 2, border_radius=4)


def draw_button(surface, rect, text, base, hover, active=False):
    mx, my = pygame.mouse.get_pos()
    hovered = rect.collidepoint(mx, my) and not active
    c = hover if hovered else base
    if active:
        c = hover
    shadow = tuple(max(0, x - 70) for x in c)
    pygame.draw.rect(surface, shadow, rect.move(0, 5), border_radius=18)
    pygame.draw.rect(surface, c, rect, border_radius=18)
    pygame.draw.rect(surface, (255, 255, 255), rect, 3, border_radius=18)
    txt = font_button.render(text, True, (35, 25, 60))
    surface.blit(txt, (rect.centerx - txt.get_width() // 2,
                       rect.centery - txt.get_height() // 2))


def draw_header(surface, now):
    # режимы
    a_active = state['mode'] == 'animals'
    draw_button(surface, BTN_MODE_ANIMALS, "🐾 Животные",
                (200, 220, 255), (225, 240, 255), a_active)
    draw_button(surface, BTN_MODE_INSTR, "🎵 Инструменты",
                (255, 220, 200), (255, 240, 225), not a_active)

    # счёт
    pygame.draw.rect(surface, (60, 45, 100), SCORE_RECT, border_radius=16)
    pygame.draw.rect(surface, (255, 220, 100), SCORE_RECT, 3, border_radius=16)
    txt = font_score.render(f"⭐  Очки: {state['score']}", True, (255, 240, 200))
    surface.blit(txt, (SCORE_RECT.centerx - txt.get_width() // 2,
                       SCORE_RECT.centery - txt.get_height() // 2))

    # заголовок
    title = font_title.render("🔊  Найди звук!", True, (255, 240, 210))
    surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 98))

    sub_text = ("Послушай звук и выбери правильную картинку."
                if not state['round_over']
                else "Молодец! 🎉")
    sub = font_sub.render(sub_text, True, (200, 200, 225))
    surface.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 152))

    # индикатор звука
    draw_sound_wave(surface, WIDTH // 2, 195, now)


def draw_footer(surface):
    draw_button(surface, BTN_REPEAT, "🔊  Ещё раз",
                (200, 230, 255), (225, 245, 255))
    draw_button(surface, BTN_HINT, "💡  Подсказка",
                (255, 235, 170), (255, 245, 200))

    if state['hint_text']:
        # фон плашки
        txt = font_hint.render("💡  " + state['hint_text'], True, (60, 40, 90))
        pad = 18
        rect = pygame.Rect(0, 0, txt.get_width() + pad * 2,
                           txt.get_height() + pad)
        rect.centerx = WIDTH // 2
        rect.y = 620
        pygame.draw.rect(surface, (255, 245, 200), rect, border_radius=18)
        pygame.draw.rect(surface, (230, 190, 90), rect, 3, border_radius=18)
        surface.blit(txt, (rect.x + pad, rect.y + pad // 2))


def draw_streak(surface):
    if state['streak'] >= 2 and not state['round_over']:
        pass  # можно показать «серия»
    if state['streak'] >= 2:
        txt = font_small.render(
            f"🔥 серия: {state['streak']}  (рекорд: {state['best_streak']})",
            True, (255, 200, 120))
        surface.blit(txt, (WIDTH - txt.get_width() - 30, HEIGHT - 40))


# ============================================================
#  ГЛАВНЫЙ ЦИКЛ
# ============================================================

def main():
    new_round()
    running = True
    while running:
        now = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                handle_click(event.pos)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    repeat_sound()
                elif event.key == pygame.K_h:
                    show_hint()
                elif event.key == pygame.K_TAB:
                    toggle_mode()
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    pick_option(event.key - pygame.K_1)
                elif event.key == pygame.K_r:
                    state['score'] = 0
                    state['streak'] = 0
                    click_sound.play()

        # авто-подсказка через 8 секунд
        if (not state['round_over']
                and state['hint_text'] is None
                and now - state['round_start'] > 8000):
            state['hint_text'] = get_items()[state['target']]['hint']

        # переход к новому раунду
        if state['round_over'] and state['next_round_at'] > 0 \
                and now >= state['next_round_at']:
            new_round()

        update_effects(now)

        # ---------- отрисовка ----------
        screen.fill((26, 20, 55))
        for y in range(0, HEIGHT, 4):
            t = y / HEIGHT
            c = (int(26 + 30 * t), int(20 + 8 * t), int(55 + 30 * t))
            pygame.draw.rect(screen, c, (0, y, WIDTH, 4))

        draw_header(screen, now)

        items = get_items()
        for i, rect in enumerate(CARD_RECTS):
            opt = state['options'][i] if i < len(state['options']) else 0
            draw_card(screen, rect, items[opt], i, now)

        draw_footer(screen)
        draw_streak(screen)
        draw_effects(screen, now)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()