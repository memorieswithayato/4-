"""
🎛️ Виртуальный музыкальный конструктор

Ребёнок перетаскивает звуковые блоки из палитры (внизу) на таймлайн
(сетка 8 × 5). Нажимает «Играть» — программа циклично проигрывает
собранную мелодию.

Управление:
  • Перетаскивание блока из палитры на клетку таймлайна — поставить звук.
  • Клик по блоку в таймлайне — убрать.
  • Перетаскивание блока из клетки в клетку — переместить.
  • Правый клик по блоку в клетке — сменить его звук на следующий.
  • ПРОБЕЛ — Играть / Пауза.
  • C — очистить всё, R — случайный рисунок.
  • + / − — темп.
  • ESC — выход.
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
pygame.mixer.set_num_channels(64)

SR = 44100
WIDTH, HEIGHT = 1280, 880
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Музыкальный конструктор")
clock = pygame.time.Clock()

# ============================================================
#  СИНТЕЗ ЗВУКОВ
# ============================================================

def to_sound(samples):
    arr = array.array('h', [int(max(-1.0, min(1.0, s)) * 32000) for s in samples])
    return pygame.mixer.Sound(buffer=arr.tobytes())


def synth_kick():
    dur = 0.42
    n = int(SR * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        f = 160 * math.exp(-t * 20) + 45
        phase += 2 * math.pi * f / SR
        env = math.exp(-t * 7)
        out.append(math.sin(phase) * env * 0.95)
    return to_sound(out)


def synth_snare():
    dur = 0.28
    n = int(SR * dur)
    out = []
    prev = 0.0
    for i in range(n):
        t = i / SR
        noise = random.random() * 2 - 1
        hp = noise - prev * 0.6
        prev = noise
        tone_f = 200 * math.exp(-t * 22) + 90
        tone = math.sin(2 * math.pi * tone_f * t) * math.exp(-t * 25)
        env = math.exp(-t * 18)
        out.append((hp * 0.55 + tone * 0.55) * env * 0.75)
    return to_sound(out)


def synth_hihat():
    dur = 0.09
    n = int(SR * dur)
    out = []
    prev = 0.0
    for i in range(n):
        t = i / SR
        noise = random.random() * 2 - 1
        s = noise - prev
        prev = noise
        env = math.exp(-t * 60)
        out.append(s * env * 0.35)
    return to_sound(out)


def synth_shaker():
    dur = 0.16
    n = int(SR * dur)
    out = []
    prev = 0.0
    for i in range(n):
        t = i / SR
        noise = random.random() * 2 - 1
        s = noise - prev * 0.7
        prev = noise
        env = math.exp(-t * 26)
        out.append(s * env * 0.40)
    return to_sound(out)


def synth_tone(freq, dur, amp=0.5, decay=4.0,
               partials=((1, 1.0), (2, 0.4), (3, 0.15)), attack=0.008):
    n = int(SR * dur)
    a_s = max(1, int(SR * attack))
    out = [0.0] * n
    for mult, p_amp in partials:
        w = 2 * math.pi * freq * mult
        for i in range(n):
            t = i / SR
            env = math.exp(-t * decay)
            if i < a_s:
                env *= i / a_s
            out[i] += math.sin(w * t) * p_amp * env
    peak = max(abs(s) for s in out) or 1.0
    return to_sound([s / peak * amp for s in out])


def synth_crash():
    dur = 1.4
    n = int(SR * dur)
    out = []
    prev = 0.0
    for i in range(n):
        t = i / SR
        noise = random.random() * 2 - 1
        s = noise - prev * 0.8
        prev = noise
        env = math.exp(-t * 3.5)
        out.append(s * env * 0.35)
    return to_sound(out)


def synth_pop():
    dur = 0.14
    n = int(SR * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        f = 900 - 400 * (t / dur)
        phase += 2 * math.pi * f / SR
        env = math.exp(-t * 22)
        out.append(math.sin(phase) * env * 0.5)
    return to_sound(out)


def synth_click():
    n = int(SR * 0.04)
    out = []
    for i in range(n):
        t = i / SR
        out.append(math.sin(2 * math.pi * 1500 * t) * math.exp(-t * 50) * 0.25)
    return to_sound(out)


print("Синтез звуков, пару секунд...")

BLOCKS = [
    {'name': 'Бум',    'color': (230, 85, 85),   'icon': 'kick',   'sound': synth_kick()},
    {'name': 'Хлоп',   'color': (240, 150, 70),  'icon': 'snare',  'sound': synth_snare()},
    {'name': 'Тсс',    'color': (80, 190, 230),  'icon': 'hihat',  'sound': synth_hihat()},
    {'name': 'Бубен',  'color': (130, 210, 120), 'icon': 'shaker', 'sound': synth_shaker()},
    {'name': 'Бас',    'color': (160, 120, 230), 'icon': 'bass',
     'sound': synth_tone(65.41, 0.55, 0.55, 4.0, ((1, 1), (2, 0.4), (3, 0.15)))},
    {'name': 'До',     'color': (230, 190, 70),  'icon': 'bell',
     'sound': synth_tone(523.25, 1.2, 0.40, 2.5,
                         ((1, 1), (2.01, 0.5), (2.98, 0.3), (5.4, 0.13)))},
    {'name': 'Ми',     'color': (240, 130, 195), 'icon': 'bell',
     'sound': synth_tone(659.25, 1.2, 0.40, 2.5,
                         ((1, 1), (2.01, 0.5), (2.98, 0.3), (5.4, 0.13)))},
    {'name': 'Ксил',   'color': (120, 210, 90),  'icon': 'xylo',
     'sound': synth_tone(523.25, 0.6, 0.48, 6.0, ((1, 1), (3, 0.3), (5, 0.1)))},
    {'name': 'Соль',   'color': (60, 200, 180),  'icon': 'xylo',
     'sound': synth_tone(783.99, 0.6, 0.48, 6.0, ((1, 1), (3, 0.3), (5, 0.1)))},
    {'name': 'Дудка',  'color': (100, 180, 240), 'icon': 'flute',
     'sound': synth_tone(392.00, 0.6, 0.38, 2.8,
                         ((1, 1), (2, 0.15), (3, 0.05)), attack=0.05)},
    {'name': 'Тарелка','color': (180, 150, 240), 'icon': 'crash',  'sound': synth_crash()},
    {'name': 'Пик',    'color': (240, 170, 90),  'icon': 'pop',    'sound': synth_pop()},
]

block_sounds = [b['sound'] for b in BLOCKS]
click_sound = synth_click()

print("Готово.")

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


font_title  = get_font(38, bold=True)
font_sub    = get_font(17)
font_btn    = get_font(24, bold=True)
font_cell   = get_font(20, bold=True)
font_pal    = get_font(14, bold=True)
font_small  = get_font(15, bold=True)
font_bpm    = get_font(28, bold=True)
font_hint   = get_font(22, bold=True)

# ============================================================
#  РАЗМЕТКА
# ============================================================

COLS = 8
ROWS = 5
CELL_W = 130
CELL_H = 100
GAP = 6

GRID_W = COLS * CELL_W + (COLS - 1) * GAP
GRID_H = ROWS * CELL_H + (ROWS - 1) * GAP
GRID_X = (WIDTH - GRID_W) // 2
GRID_Y = 145

PAL_W = 92
PAL_H = 92
PAL_GAP = 6
PAL_Y = 725
PAL_TOTAL = len(BLOCKS) * PAL_W + (len(BLOCKS) - 1) * PAL_GAP
PAL_X = (WIDTH - PAL_TOTAL) // 2

palette_rects = [
    pygame.Rect(PAL_X + i * (PAL_W + PAL_GAP), PAL_Y, PAL_W, PAL_H)
    for i in range(len(BLOCKS))
]

BTN_PLAY   = pygame.Rect(WIDTH - 580, 26, 190, 62)
BTN_CLEAR  = pygame.Rect(WIDTH - 380, 26, 160, 62)
BTN_RANDOM = pygame.Rect(WIDTH - 210, 26, 190, 62)

BTN_TEMPO_DOWN = pygame.Rect(510, 36, 46, 46)
BPM_RECT       = pygame.Rect(566, 36, 70, 46)
BTN_TEMPO_UP   = pygame.Rect(646, 36, 46, 46)

# ============================================================
#  ВСПОМОГАТЕЛЬНОЕ
# ============================================================

def lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def cell_rect(r, c):
    return pygame.Rect(
        GRID_X + c * (CELL_W + GAP),
        GRID_Y + r * (CELL_H + GAP),
        CELL_W, CELL_H)


def find_cell(mx, my):
    if not (GRID_X <= mx <= GRID_X + GRID_W):
        return None
    if not (GRID_Y <= my <= GRID_Y + GRID_H):
        return None
    c = (mx - GRID_X) // (CELL_W + GAP)
    r = (my - GRID_Y) // (CELL_H + GAP)
    if 0 <= r < ROWS and 0 <= c < COLS:
        return (int(r), int(c))
    return None


def draw_icon(kind, rect, color, surface):
    """Простые пиктограммы для блоков."""
    cx, cy = rect.center
    w = min(rect.w, rect.h)
    r = max(6, w // 2 - 6)

    if kind == 'kick':
        pygame.draw.circle(surface, color, (cx, cy), r, 4)
        pygame.draw.circle(surface, color, (cx, cy), max(3, r // 3))

    elif kind == 'snare':
        rr = pygame.Rect(cx - r, cy - int(r * 0.7), 2 * r, int(r * 1.4))
        pygame.draw.rect(surface, color, rr, 4, border_radius=6)
        pygame.draw.line(surface, color, (cx - r, cy), (cx + r, cy), 3)

    elif kind == 'hihat':
        rr1 = pygame.Rect(cx - r, cy - r // 2 - 4, 2 * r, 10)
        rr2 = pygame.Rect(cx - r, cy + r // 2 - 6, 2 * r, 10)
        pygame.draw.ellipse(surface, color, rr1)
        pygame.draw.ellipse(surface, color, rr2)
        pygame.draw.line(surface, color, (cx, cy - r // 2), (cx, cy + r // 2), 2)

    elif kind == 'shaker':
        rr = pygame.Rect(cx - r // 2, cy - r, r, 2 * r)
        pygame.draw.ellipse(surface, color, rr, 4)
        for dy in (-r // 2, 0, r // 2):
            pygame.draw.line(surface, color,
                             (cx - r // 3, cy + dy), (cx + r // 3, cy + dy), 2)

    elif kind == 'bass':
        pygame.draw.circle(surface, color, (cx - r // 2, cy + r // 3), 6)
        pygame.draw.circle(surface, color, (cx + r // 2, cy + r // 3), 6)
        pygame.draw.line(surface, color,
                         (cx - r // 2 + 4, cy + r // 3),
                         (cx + r // 2 + 4, cy + r // 3), 4)
        pygame.draw.line(surface, color,
                         (cx + r // 2 + 4, cy + r // 3),
                         (cx + r // 2 + 4, cy - r + 4), 4)

    elif kind == 'bell':
        pts = [(cx - r + 2, cy + r // 2), (cx - r // 2, cy - r + 4),
               (cx + r // 2, cy - r + 4), (cx + r - 2, cy + r // 2)]
        pygame.draw.polygon(surface, color, pts, 4)
        pygame.draw.line(surface, color,
                         (cx - r + 2, cy + r // 2),
                         (cx + r - 2, cy + r // 2), 4)
        pygame.draw.circle(surface, color, (cx, cy + r // 2 + 5), 4)

    elif kind == 'xylo':
        for i in range(3):
            bar_w = 2 * r - i * 6
            bar_x = cx - bar_w // 2
            bar_y = cy - r + i * (2 * r) // 3 + 4
            pygame.draw.rect(surface, color,
                             (bar_x, bar_y, bar_w, 8), border_radius=4)

    elif kind == 'flute':
        rr = pygame.Rect(cx - r, cy - 8, 2 * r, 16)
        pygame.draw.rect(surface, color, rr, 4, border_radius=8)
        for i in range(3):
            pygame.draw.circle(surface, color,
                               (cx - r // 2 + i * (r // 2), cy), 3)

    elif kind == 'crash':
        for i in range(8):
            a = i * math.pi / 4
            x1 = cx + math.cos(a) * (r // 3)
            y1 = cy + math.sin(a) * (r // 3)
            x2 = cx + math.cos(a) * r
            y2 = cy + math.sin(a) * r
            pygame.draw.line(surface, color, (x1, y1), (x2, y2), 4)
        pygame.draw.circle(surface, color, (cx, cy), r // 3)

    elif kind == 'pop':
        pygame.draw.circle(surface, color, (cx, cy), r, 4)
        pygame.draw.circle(surface, color, (cx, cy), 4)


def draw_block_visual(bidx, rect, name_font, glow=0.0):
    """Рисует блок: цвет, обводка, иконка, название."""
    block = BLOCKS[bidx]
    color = block['color']
    if glow > 0:
        color = lerp_color(color, (255, 255, 255), 0.6 * glow)

    # тень
    shadow_col = tuple(max(0, c - 90) for c in color)
    pygame.draw.rect(screen, shadow_col, rect.move(0, 6), border_radius=14)

    # тело
    pygame.draw.rect(screen, color, rect, border_radius=14)
    pygame.draw.rect(screen, (255, 255, 255), rect, 3, border_radius=14)

    # иконка
    icon_h = max(20, rect.h - name_font.get_height() - 18)
    icon_rect = pygame.Rect(rect.x + 10, rect.y + 8,
                            rect.w - 20, icon_h)
    draw_icon(block['icon'], icon_rect, (255, 255, 255), screen)

    # название
    name = block['name']
    img = name_font.render(name, True, (255, 255, 255))
    sh = name_font.render(name, True, (0, 0, 0))
    tx = rect.centerx - img.get_width() // 2
    ty = rect.bottom - img.get_height() - 8
    screen.blit(sh, (tx + 2, ty + 2))
    screen.blit(img, (tx, ty))


# ============================================================
#  СОСТОЯНИЕ
# ============================================================

timeline = [[None] * COLS for _ in range(ROWS)]
is_playing = False
current_step = 0
last_step_ms = 0
tempo_level = 4  # 1..8

cell_flash = {}  # (r, c) -> t0
dragging = None  # {'block_idx': int, 'mx': int, 'my': int, 'origin': (r,c) | None}
pending_cell = None  # для различения клик/драг
mouse_down_pos = (0, 0)


def get_step_ms():
    return 800 - (tempo_level - 1) * 80


def init_preset():
    """Стартовый рисунок — чтобы было с чего начать."""
    for r in range(ROWS):
        for c in range(COLS):
            timeline[r][c] = None
    timeline[0][0] = 0
    timeline[0][4] = 0
    timeline[1][2] = 1
    timeline[1][6] = 1
    timeline[2][0] = 2
    timeline[2][2] = 2
    timeline[2][4] = 2
    timeline[2][6] = 2
    timeline[3][0] = 4
    timeline[3][3] = 4
    timeline[3][6] = 4
    timeline[4][2] = 5
    timeline[4][6] = 5


def random_pattern():
    for r in range(ROWS):
        for c in range(COLS):
            timeline[r][c] = None
    for r in range(ROWS):
        n_cells = random.randint(2, 5)
        cols = random.sample(range(COLS), n_cells)
        for c in cols:
            timeline[r][c] = random.randrange(len(BLOCKS))


def play_step(col, now):
    for r in range(ROWS):
        bidx = timeline[r][col]
        if bidx is not None:
            block_sounds[bidx].play()
            cell_flash[(r, col)] = now


# ============================================================
#  ОТРИСОВКА
# ============================================================

def draw_background(now):
    for y in range(0, HEIGHT, 4):
        t = y / HEIGHT
        c = (int(24 + 22 * t), int(18 + 12 * t), int(50 + 28 * t))
        pygame.draw.rect(screen, c, (0, y, WIDTH, 4))

    # плавающие пятна
    for k in range(5):
        cx = int((WIDTH // 5) * (k + 0.5) + 70 * math.sin(now / 5500 + k))
        cy = int(HEIGHT // 2 + 100 * math.cos(now / 6500 + k * 1.7))
        r = 110 + 40 * k
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 255, 255, 6), (r, r), r)
        screen.blit(s, (cx - r, cy - r))


def draw_header(now):
    title = font_title.render("🎛️  Музыкальный конструктор", True, (255, 240, 200))
    sh = font_title.render("🎛️  Музыкальный конструктор", True, (60, 25, 80))
    screen.blit(sh, (32, 30))
    screen.blit(title, (30, 28))

    sub = font_sub.render(
        "Перетащи блоки на таймлайн, нажми «Играть» — и слушай свою музыку!",
        True, (200, 195, 230))
    screen.blit(sub, (34, 82))

    # Темп
    mx, my = pygame.mouse.get_pos()
    for rect, lbl, base in [
        (BTN_TEMPO_DOWN, "−", (200, 190, 240)),
        (BTN_TEMPO_UP,   "+", (200, 190, 240)),
    ]:
        hovered = rect.collidepoint(mx, my)
        c = tuple(min(255, x + 30) for x in base) if hovered else base
        sh_c = tuple(max(0, x - 80) for x in c)
        pygame.draw.rect(screen, sh_c, rect.move(0, 4), border_radius=12)
        pygame.draw.rect(screen, c, rect, border_radius=12)
        pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=12)
        t = font_btn.render(lbl, True, (40, 30, 70))
        screen.blit(t, (rect.centerx - t.get_width() // 2,
                        rect.centery - t.get_height() // 2))

    pygame.draw.rect(screen, (60, 45, 100), BPM_RECT, border_radius=12)
    pygame.draw.rect(screen, (255, 220, 100), BPM_RECT, 2, border_radius=12)
    bpm = font_bpm.render(str(tempo_level), True, (255, 240, 200))
    screen.blit(bpm, (BPM_RECT.centerx - bpm.get_width() // 2,
                      BPM_RECT.centery - bpm.get_height() // 2))

    lbl = font_small.render("ТЕМП", True, (180, 170, 210))
    screen.blit(lbl, (BPM_RECT.centerx - lbl.get_width() // 2,
                      BPM_RECT.top - 16))

    # Кнопки справа
    for rect, label, base in [
        (BTN_PLAY, "⏸  ПАУЗА" if is_playing else "▶  ИГРАТЬ",
         (100, 220, 130) if not is_playing else (255, 180, 90)),
        (BTN_CLEAR,  "🧹  Очистить", (200, 200, 230)),
        (BTN_RANDOM, "🎲  Случайно", (255, 210, 90)),
    ]:
        hovered = rect.collidepoint(mx, my)
        c = tuple(min(255, x + 25) for x in base) if hovered else base
        sh_c = tuple(max(0, x - 80) for x in c)
        pygame.draw.rect(screen, sh_c, rect.move(0, 5), border_radius=14)
        pygame.draw.rect(screen, c, rect, border_radius=14)
        pygame.draw.rect(screen, (255, 255, 255), rect, 3, border_radius=14)
        t = font_btn.render(label, True, (35, 25, 55))
        screen.blit(t, (rect.centerx - t.get_width() // 2,
                        rect.centery - t.get_height() // 2))


def draw_section_labels():
    lab = font_hint.render("🕒  ТАЙМЛАЙН", True, (255, 220, 150))
    screen.blit(lab, (GRID_X, GRID_Y - 32))

    lab2 = font_hint.render("🎵  БИБЛИОТЕКА ЗВУКОВ", True, (255, 220, 150))
    screen.blit(lab2, (PAL_X, PAL_Y - 32))


def draw_column_numbers():
    fnt = font_small
    for c in range(COLS):
        rect = cell_rect(0, c)
        num = fnt.render(str(c + 1), True, (140, 130, 175))
        screen.blit(num, (rect.centerx - num.get_width() // 2,
                          rect.y - 22))


def draw_timeline(now):
    # фон сетки
    bg = pygame.Rect(GRID_X - 10, GRID_Y - 10, GRID_W + 20, GRID_H + 20)
    pygame.draw.rect(screen, (30, 22, 55), bg, border_radius=22)
    pygame.draw.rect(screen, (70, 55, 110), bg, 3, border_radius=22)

    for r in range(ROWS):
        for c in range(COLS):
            rect = cell_rect(r, c)
            bidx = timeline[r][c]

            # фон клетки
            if bidx is None:
                base = (46, 38, 72)
                # пульсирующая подсветка целевой клетки при перетаскивании
                if dragging and dragging.get('hover') == (r, c):
                    pulse = 0.5 + 0.5 * math.sin(now / 140)
                    base = lerp_color(base, (130, 110, 200), 0.4 + 0.4 * pulse)
                pygame.draw.rect(screen, base, rect, border_radius=14)
                pygame.draw.rect(screen, (65, 55, 95), rect, 2, border_radius=14)
                # маленькая точка в центре
                pygame.draw.circle(screen, (75, 65, 105), rect.center, 4)
            else:
                # вспышка, если только что играл
                t_glow = 0.0
                if (r, c) in cell_flash:
                    dt = now - cell_flash[(r, c)]
                    if dt < 340:
                        t_glow = 1 - dt / 340
                    else:
                        del cell_flash[(r, c)]
                draw_block_visual(bidx, rect, font_cell, glow=t_glow)

    # подсветка активной колонки
    if is_playing or current_step > 0:
        col_x = GRID_X + current_step * (CELL_W + GAP)
        bar = pygame.Rect(col_x - 5, GRID_Y - 12,
                          CELL_W + 10, GRID_H + 24)
        s = pygame.Surface(bar.size, pygame.SRCALPHA)
        s.fill((255, 220, 100, 45))
        screen.blit(s, bar.topleft)
        # верхний маркер
        pygame.draw.polygon(screen, (255, 220, 100), [
            (col_x + CELL_W // 2, GRID_Y - 22),
            (col_x + CELL_W // 2 - 10, GRID_Y - 34),
            (col_x + CELL_W // 2 + 10, GRID_Y - 34),
        ])


def draw_palette(now):
    bg = pygame.Rect(PAL_X - 14, PAL_Y - 14,
                     PAL_TOTAL + 28, PAL_H + 28)
    pygame.draw.rect(screen, (32, 24, 60), bg, border_radius=20)
    pygame.draw.rect(screen, (70, 55, 110), bg, 3, border_radius=20)

    for i, rect in enumerate(palette_rects):
        # уменьшенная версия — берём как есть, просто другой шрифт
        draw_block_visual(i, rect, font_pal)


def draw_hint(now):
    # Если таймлайн пуст — большая подсказка
    empty = all(timeline[r][c] is None for r in range(ROWS) for c in range(COLS))
    if empty and not is_playing:
        pulse = 0.5 + 0.5 * math.sin(now / 400)
        col = (int(200 + 40 * pulse), int(200 + 30 * pulse), 255)
        txt = font_hint.render(
            "↓ Перетащи любой блок вниз, на клетки таймлайна ↓",
            True, col)
        screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2,
                          GRID_Y + GRID_H // 2 - txt.get_height() // 2))


def draw_drag_preview(now):
    if not dragging:
        return
    mx, my = dragging['mx'], dragging['my']
    w, h = 120, 92
    rect = pygame.Rect(mx - w // 2, my - h // 2, w, h)
    # тень + блок
    draw_block_visual(dragging['block_idx'], rect, font_cell, glow=0.4)
    # лёгкая пульсирующая рамка
    pulse = 0.5 + 0.5 * math.sin(now / 120)
    pygame.draw.rect(screen, (255, 255, 255),
                     rect.inflate(14, 14), 3 + int(2 * pulse),
                     border_radius=20)


# ============================================================
#  ГЛАВНЫЙ ЦИКЛ
# ============================================================

def main():
    global is_playing, current_step, last_step_ms, tempo_level
    global dragging, pending_cell, mouse_down_pos

    init_preset()
    last_step_ms = pygame.time.get_ticks()

    running = True
    while running:
        now = pygame.time.get_ticks()

        # ---------------- СОБЫТИЯ ----------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos

                # правый клик — сменить звук блока в клетке
                if event.button == 3:
                    cell = find_cell(mx, my)
                    if cell:
                        r, c = cell
                        bidx = timeline[r][c]
                        if bidx is not None:
                            new_bidx = (bidx + 1) % len(BLOCKS)
                            timeline[r][c] = new_bidx
                            block_sounds[new_bidx].play()
                            cell_flash[(r, c)] = now
                    continue

                if event.button != 1:
                    continue

                # кнопки шапки
                if BTN_PLAY.collidepoint(mx, my):
                    is_playing = not is_playing
                    if is_playing:
                        current_step = 0
                        play_step(0, now)
                        last_step_ms = now
                    continue
                if BTN_CLEAR.collidepoint(mx, my):
                    for r in range(ROWS):
                        for c in range(COLS):
                            timeline[r][c] = None
                    click_sound.play()
                    continue
                if BTN_RANDOM.collidepoint(mx, my):
                    random_pattern()
                    click_sound.play()
                    continue
                if BTN_TEMPO_DOWN.collidepoint(mx, my):
                    tempo_level = max(1, tempo_level - 1)
                    click_sound.play()
                    continue
                if BTN_TEMPO_UP.collidepoint(mx, my):
                    tempo_level = min(8, tempo_level + 1)
                    click_sound.play()
                    continue

                # палитра
                for i, rect in enumerate(palette_rects):
                    if rect.collidepoint(mx, my):
                        dragging = {'block_idx': i, 'mx': mx, 'my': my,
                                    'origin': None, 'hover': None}
                        block_sounds[i].play()
                        break
                else:
                    # таймлайн
                    cell = find_cell(mx, my)
                    if cell:
                        r, c = cell
                        bidx = timeline[r][c]
                        if bidx is not None:
                            pending_cell = (r, c)
                            mouse_down_pos = (mx, my)

            elif event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                if dragging:
                    dragging['mx'] = mx
                    dragging['my'] = my
                    cell = find_cell(mx, my)
                    dragging['hover'] = cell
                elif pending_cell:
                    dx = abs(mx - mouse_down_pos[0])
                    dy = abs(my - mouse_down_pos[1])
                    if dx > 10 or dy > 10:
                        r, c = pending_cell
                        bidx = timeline[r][c]
                        if bidx is not None:
                            dragging = {'block_idx': bidx, 'mx': mx, 'my': my,
                                        'origin': (r, c), 'hover': None}
                            timeline[r][c] = None
                            pending_cell = None

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                mx, my = event.pos

                if dragging:
                    cell = find_cell(mx, my)
                    if cell:
                        r, c = cell
                        timeline[r][c] = dragging['block_idx']
                        block_sounds[dragging['block_idx']].play()
                        cell_flash[(r, c)] = now
                    else:
                        # отмена: вернуть на исходную, если тащили из клетки
                        if dragging.get('origin'):
                            r0, c0 = dragging['origin']
                            timeline[r0][c0] = dragging['block_idx']
                    dragging = None
                elif pending_cell:
                    # был клик по клетке без движения → удаляем блок
                    r, c = pending_cell
                    if timeline[r][c] is not None:
                        timeline[r][c] = None
                        click_sound.play()
                    pending_cell = None

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    is_playing = not is_playing
                    if is_playing:
                        current_step = 0
                        play_step(0, now)
                        last_step_ms = now
                elif event.key == pygame.K_c:
                    for r in range(ROWS):
                        for c in range(COLS):
                            timeline[r][c] = None
                    click_sound.play()
                elif event.key == pygame.K_r:
                    random_pattern()
                    click_sound.play()
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    tempo_level = min(8, tempo_level + 1)
                    click_sound.play()
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    tempo_level = max(1, tempo_level - 1)
                    click_sound.play()

        # ---------------- ЛОГИКА ----------------
        if is_playing:
            step_ms = get_step_ms()
            if now - last_step_ms >= step_ms:
                last_step_ms += step_ms
                if now - last_step_ms > 3 * step_ms:
                    last_step_ms = now
                current_step = (current_step + 1) % COLS
                play_step(current_step, now)

        # ---------------- ОТРИСОВКА ----------------
        draw_background(now)
        draw_header(now)
        draw_section_labels()
        draw_column_numbers()
        draw_timeline(now)
        draw_hint(now)
        draw_palette(now)
        draw_drag_preview(now)

        # курсор-рука при перетаскивании
        if dragging:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()