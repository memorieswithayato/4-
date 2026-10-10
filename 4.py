"""
🎼 Детский оркестр — упрощённый Launchpad для детей.

Запуск:  python kids_orchestra.py
Требуется: pip install pygame

Управление:
  • Клик по большой кнопке — включить/выключить инструмент.
  • ПРОБЕЛ — пауза / продолжить.
  • R — выключить все, M — случайный микс.
  • Клавиши 1–8 — переключать инструменты.
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
WIDTH, HEIGHT = 1160, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Детский оркестр")
clock = pygame.time.Clock()

# ============================================================
#  СИНТЕЗ ЗВУКОВ
# ============================================================

def to_sound(samples):
    arr = array.array('h', [int(max(-1.0, min(1.0, s)) * 32000) for s in samples])
    return pygame.mixer.Sound(buffer=arr.tobytes())


def make_tone(freq, dur, amp=0.5, decay=4.0,
              partials=((1, 1.0), (2, 0.4), (3, 0.15)), attack=0.008):
    """Общий генератор гармонического тона с огибающей."""
    n = int(SR * dur)
    a_samples = max(1, int(SR * attack))
    samples = [0.0] * n
    for mult, p_amp in partials:
        w = 2 * math.pi * freq * mult
        for i in range(n):
            t = i / SR
            env = math.exp(-t * decay)
            if i < a_samples:
                env *= i / a_samples
            samples[i] += math.sin(w * t) * p_amp * env
    peak = max(abs(s) for s in samples) or 1.0
    return to_sound([s / peak * amp for s in samples])


def make_kick():
    dur = 0.40
    n = int(SR * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        f = 150 * math.exp(-t * 22) + 45
        phase += 2 * math.pi * f / SR
        env = math.exp(-t * 7)
        out.append(math.sin(phase) * env * 0.95)
    return to_sound(out)


def make_snare():
    dur = 0.25
    n = int(SR * dur)
    out = []
    prev = 0.0
    for i in range(n):
        t = i / SR
        noise = random.random() * 2 - 1
        hp = noise - prev * 0.6
        prev = noise
        env_n = math.exp(-t * 20)
        tone_f = 180 * math.exp(-t * 22) + 90
        tone = math.sin(2 * math.pi * tone_f * t) * math.exp(-t * 25)
        out.append((hp * 0.55 + tone * 0.55) * env_n * 0.75)
    return to_sound(out)


def make_hihat():
    dur = 0.09
    n = int(SR * dur)
    out = []
    prev = 0.0
    for i in range(n):
        t = i / SR
        noise = random.random() * 2 - 1
        s = noise - prev
        prev = noise
        env = math.exp(-t * 65)
        out.append(s * env * 0.35)
    return to_sound(out)


def make_shaker():
    dur = 0.14
    n = int(SR * dur)
    out = []
    prev = 0.0
    for i in range(n):
        t = i / SR
        noise = random.random() * 2 - 1
        s = noise - prev * 0.75
        prev = noise
        env = math.exp(-t * 28)
        out.append(s * env * 0.42)
    return to_sound(out)


print("Синтез звуков, подожди пару секунд...")

NOTE = {
    'G2': 98.00,  'C3': 130.81, 'E3': 164.81, 'G3': 196.00,
    'C4': 261.63, 'D4': 293.66, 'E4': 329.63, 'F4': 349.23,
    'G4': 392.00, 'A4': 440.00, 'B4': 493.88,
    'C5': 523.25, 'D5': 587.33, 'E5': 659.25, 'G5': 783.99,
    'C6': 1046.50,
}

INST_SOUNDS = {}
INST_SOUNDS['kick']   = {'kick':   make_kick()}
INST_SOUNDS['snare']  = {'snare':  make_snare()}
INST_SOUNDS['hihat']  = {'hihat':  make_hihat()}
INST_SOUNDS['shaker'] = {'shaker': make_shaker()}

INST_SOUNDS['bass'] = {
    n: make_tone(NOTE[n], 0.55, amp=0.55, decay=4.0,
                 partials=((1, 1.0), (2, 0.4), (3, 0.15)))
    for n in ['C3', 'G2']
}

INST_SOUNDS['xylo'] = {
    n: make_tone(NOTE[n], 0.60, amp=0.50, decay=6.0,
                 partials=((1, 1.0), (3, 0.30), (5, 0.10)))
    for n in ['C5', 'E5', 'G5', 'C6']
}

INST_SOUNDS['flute'] = {
    n: make_tone(NOTE[n], 0.55, amp=0.40, decay=3.0,
                 partials=((1, 1.0), (2, 0.15), (3, 0.05)), attack=0.05)
    for n in ['G4', 'A4', 'B4', 'C5']
}

INST_SOUNDS['bell'] = {
    n: make_tone(NOTE[n], 1.20, amp=0.38, decay=2.5,
                 partials=((1, 1.0), (2.01, 0.5), (2.98, 0.3), (5.4, 0.13)))
    for n in ['C6', 'G5']
}

print("Готово!")

# ============================================================
#  ОПИСАНИЕ ИНСТРУМЕНТОВ
# ============================================================

INSTRUMENTS = [
    {
        'id': 'kick', 'name': 'Барабан',
        'color': (235, 90, 90), 'accent': (255, 170, 150),
        'pattern': {0: 'kick', 4: 'kick', 8: 'kick', 12: 'kick'},
    },
    {
        'id': 'snare', 'name': 'Хлопки',
        'color': (245, 175, 60), 'accent': (255, 220, 130),
        'pattern': {4: 'snare', 12: 'snare'},
    },
    {
        'id': 'hihat', 'name': 'Тарелки',
        'color': (75, 190, 235), 'accent': (160, 230, 255),
        'pattern': {s: 'hihat' for s in range(0, 16, 2)},
    },
    {
        'id': 'shaker', 'name': 'Бубен',
        'color': (120, 215, 120), 'accent': (195, 250, 195),
        'pattern': {s: 'shaker' for s in (2, 6, 10, 14)},
    },
    {
        'id': 'bass', 'name': 'Бас',
        'color': (160, 120, 235), 'accent': (215, 190, 255),
        'pattern': {0: 'C3', 3: 'C3', 6: 'G2', 9: 'G2', 12: 'C3', 15: 'G2'},
    },
    {
        'id': 'xylo', 'name': 'Ксилофон',
        'color': (245, 120, 190), 'accent': (255, 190, 230),
        'pattern': {0: 'C5', 2: 'E5', 4: 'G5', 6: 'E5',
                    8: 'C5', 10: 'E5', 12: 'G5', 14: 'C6'},
    },
    {
        'id': 'flute', 'name': 'Дудочка',
        'color': (90, 205, 205), 'accent': (180, 245, 245),
        'pattern': {0: 'G4', 2: 'A4', 4: 'B4', 6: 'C5',
                    8: 'G4', 10: 'A4', 12: 'B4', 14: 'C5'},
    },
    {
        'id': 'bell', 'name': 'Колокольчик',
        'color': (230, 200, 70), 'accent': (255, 240, 170),
        'pattern': {0: 'C6', 8: 'G5'},
    },
]

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


font_title    = get_font(46, bold=True)
font_sub      = get_font(20)
font_btn      = get_font(22, bold=True)
font_label    = get_font(28, bold=True)
font_hint     = get_font(20)
font_small    = get_font(16, bold=True)

# ============================================================
#  РАЗМЕТКА
# ============================================================

COLS, ROWS = 4, 2
MARGIN_X = 30
MARGIN_TOP = 165
MARGIN_BOTTOM = 90
GAP = 20

BTN_W = (WIDTH - 2 * MARGIN_X - (COLS - 1) * GAP) // COLS
BTN_H = (HEIGHT - MARGIN_TOP - MARGIN_BOTTOM - (ROWS - 1) * GAP) // ROWS

BTN_RECTS = []
for r in range(ROWS):
    for c in range(COLS):
        x = MARGIN_X + c * (BTN_W + GAP)
        y = MARGIN_TOP + r * (BTN_H + GAP)
        BTN_RECTS.append(pygame.Rect(x, y, BTN_W, BTN_H))

BTN_PLAY   = pygame.Rect(WIDTH - 520, 55, 160, 70)
BTN_CLEAR  = pygame.Rect(WIDTH - 350, 55, 160, 70)
BTN_RANDOM = pygame.Rect(WIDTH - 180, 55, 160, 70)

# ============================================================
#  ВСПОМОГАТЕЛЬНОЕ
# ============================================================

def lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw_rounded_glow(surface, rect, color, alpha, radius, expand=16):
    r = rect.inflate(expand * 2, expand * 2)
    glow = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
    pygame.draw.rect(glow, (*color, alpha), glow.get_rect(),
                     border_radius=radius + expand)
    surface.blit(glow, r.topleft)


def draw_button(surface, rect, text, base, hover, pressed=False, big=False):
    mx, my = pygame.mouse.get_pos()
    hovered = rect.collidepoint(mx, my) and not pressed
    c = hover if hovered else base
    shadow = tuple(max(0, x - 70) for x in c)
    pygame.draw.rect(surface, shadow, rect.move(0, 5), border_radius=18)
    pygame.draw.rect(surface, c, rect, border_radius=18)
    pygame.draw.rect(surface, (255, 255, 255), rect, 3, border_radius=18)
    fnt = get_font(24 if big else 22, bold=True)
    txt = fnt.render(text, True, (35, 25, 60))
    surface.blit(txt, (rect.centerx - txt.get_width() // 2,
                       rect.centery - txt.get_height() // 2))

# ============================================================
#  ИКОНКИ ИНСТРУМЕНТОВ
# ============================================================

def draw_icon(surface, inst_id, rect, color):
    cx, cy = rect.center
    w = min(rect.w, rect.h)

    if inst_id == 'kick':
        r = w // 2 - 4
        pygame.draw.circle(surface, color, (cx, cy), r)
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy), r, 3)
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy), r // 3, 2)

    elif inst_id == 'snare':
        rr = pygame.Rect(cx - w // 2 + 6, cy - w // 3, w - 12, 2 * w // 3)
        pygame.draw.rect(surface, color, rr, border_radius=12)
        pygame.draw.rect(surface, (255, 255, 255), rr, 3, border_radius=12)
        pygame.draw.line(surface, (255, 255, 255),
                         (cx - w // 3, cy - w // 2 + 4),
                         (cx + w // 4, cy - w // 6), 5)
        pygame.draw.line(surface, (255, 255, 255),
                         (cx + w // 3, cy - w // 2 + 4),
                         (cx - w // 4, cy - w // 6), 5)

    elif inst_id == 'hihat':
        rr1 = pygame.Rect(cx - w // 2 + 6, cy - w // 4, w - 12, 14)
        rr2 = pygame.Rect(cx - w // 2 + 6, cy + w // 4 - 14, w - 12, 14)
        pygame.draw.ellipse(surface, color, rr1)
        pygame.draw.ellipse(surface, color, rr2)
        pygame.draw.ellipse(surface, (255, 255, 255), rr1, 3)
        pygame.draw.ellipse(surface, (255, 255, 255), rr2, 3)

    elif inst_id == 'shaker':
        rr = pygame.Rect(cx - w // 3, cy - w // 2 + 6, 2 * w // 3, w - 12)
        pygame.draw.ellipse(surface, color, rr)
        pygame.draw.ellipse(surface, (255, 255, 255), rr, 3)
        for dy in (-10, 0, 10):
            pygame.draw.line(surface, (255, 255, 255),
                             (cx - 12, cy + dy), (cx + 12, cy + dy), 2)

    elif inst_id == 'bass':
        rr = pygame.Rect(cx - 16, cy - w // 2 + 4, 32, w - 8)
        pygame.draw.rect(surface, color, rr, border_radius=16)
        pygame.draw.rect(surface, (255, 255, 255), rr, 3, border_radius=16)
        pygame.draw.line(surface, (255, 255, 255),
                         (cx - 8, cy - 12), (cx + 8, cy - 12), 2)
        pygame.draw.line(surface, (255, 255, 255),
                         (cx - 8, cy + 4), (cx + 8, cy + 4), 2)
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy + 20), 5)

    elif inst_id == 'xylo':
        colors = [(255, 100, 100), (255, 200, 60),
                  (130, 220, 130), (110, 180, 255)]
        n = 4
        for i in range(n):
            bar_w = w - 20 - i * 12
            bar_x = cx - bar_w // 2
            bar_y = cy - w // 3 + i * (2 * w // 3) // n
            rr = pygame.Rect(bar_x, bar_y, bar_w, 12)
            pygame.draw.rect(surface, colors[i], rr, border_radius=6)
            pygame.draw.rect(surface, (255, 255, 255), rr, 2, border_radius=6)

    elif inst_id == 'flute':
        rr = pygame.Rect(cx - w // 2 + 6, cy - 10, w - 12, 20)
        pygame.draw.rect(surface, color, rr, border_radius=10)
        pygame.draw.rect(surface, (255, 255, 255), rr, 3, border_radius=10)
        for i in range(4):
            pygame.draw.circle(surface, (255, 255, 255),
                               (cx - 30 + i * 20, cy), 4)

    elif inst_id == 'bell':
        pts = [
            (cx - w // 3, cy + w // 4),
            (cx - w // 4, cy - w // 3),
            (cx + w // 4, cy - w // 3),
            (cx + w // 3, cy + w // 4),
        ]
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.polygon(surface, (255, 255, 255), pts, 3)
        pygame.draw.circle(surface, (255, 255, 255),
                           (cx, cy + w // 4 + 10), 6)

# ============================================================
#  ОТРИСОВКА ИНТЕРФЕЙСА
# ============================================================

def draw_header(surface, is_playing, now):
    # Заголовок
    title = font_title.render("Детский оркестр", True, (255, 245, 210))
    surface.blit(title, (34, 26))

    # Маленькая нотка рядом с заголовком (декор)
    nx = 34 + title.get_width() + 14
    pygame.draw.ellipse(surface, (255, 210, 110),
                        pygame.Rect(nx, 62, 14, 10))
    pygame.draw.line(surface, (255, 210, 110),
                     (nx + 13, 62), (nx + 13, 26), 3)
    pygame.draw.line(surface, (255, 210, 110),
                     (nx + 13, 26), (nx + 24, 30), 3)

    sub = font_sub.render(
        "Нажимай на инструменты — создай свою музыку!",
        True, (205, 200, 230))
    surface.blit(sub, (36, 90))

    # Кнопки управления
    draw_button(surface, BTN_PLAY,
                "ПАУЗА" if is_playing else "ПУСК",
                (255, 200, 80), (255, 225, 130), big=True)
    draw_button(surface, BTN_CLEAR, "СБРОС",
                (200, 220, 255), (225, 240, 255))
    draw_button(surface, BTN_RANDOM, "МИКС",
                (200, 255, 210), (225, 255, 230))


def draw_instrument_button(surface, inst, rect, enabled, current_step, now):
    if enabled:
        pulse = 0.5 + 0.5 * math.sin(now / 130)
        draw_rounded_glow(surface, rect, inst['accent'],
                          int(45 + 35 * pulse), radius=28, expand=14)

    # Тень
    pygame.draw.rect(surface, (0, 0, 0), rect.move(0, 8), border_radius=28)

    # Основа
    base = inst['color'] if enabled else (60, 50, 88)
    if enabled and current_step in inst['pattern']:
        flash = 0.5 + 0.5 * math.sin(now / 80)
        base = lerp_color(base, (255, 255, 255), 0.22 * flash)

    pygame.draw.rect(surface, base, rect, border_radius=28)

    # Обводка
    border_col = inst['accent'] if enabled else (95, 85, 125)
    pygame.draw.rect(surface, border_col, rect, 4, border_radius=28)

    # Иконка
    icon_rect = pygame.Rect(rect.x + 40, rect.y + 18,
                            rect.w - 80, rect.h - 140)
    icon_col = (255, 255, 255) if enabled else (150, 140, 185)
    draw_icon(surface, inst['id'], icon_rect, icon_col)

    # Название
    label_col = (255, 255, 255) if enabled else (175, 165, 205)
    label = font_label.render(inst['name'], True, label_col)
    shadow_label = font_label.render(inst['name'], True, (0, 0, 0))
    lx = rect.centerx - label.get_width() // 2
    ly = rect.y + rect.h - 108
    surface.blit(shadow_label, (lx + 2, ly + 2))
    surface.blit(label, (lx, ly))

    # Полоска паттерна (16 точек)
    strip_x = rect.x + 25
    strip_y = rect.y + rect.h - 52
    strip_w = rect.w - 50
    strip_h = 30
    cell_w = strip_w / 16

    for s in range(16):
        cx = strip_x + s * cell_w + cell_w / 2
        cy = strip_y + strip_h / 2

        has_note = s in inst['pattern']
        is_current = (s == current_step)

        bg_col = (80, 70, 115) if enabled else (55, 48, 78)
        pygame.draw.circle(surface, bg_col, (int(cx), int(cy)), 8)

        if has_note:
            col = inst['accent'] if enabled else (115, 105, 150)
            pygame.draw.circle(surface, col, (int(cx), int(cy)), 6)

        if is_current:
            hl = (255, 255, 255) if enabled else (185, 175, 215)
            pygame.draw.circle(surface, hl, (int(cx), int(cy)), 11, 2)


def draw_footer(surface):
    hint = font_hint.render(
        "Подсказка: попробуй включить Барабан + Тарелки + Бас — получится бит!",
        True, (200, 195, 225))
    surface.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 55))


def draw_bursts(surface, bursts, now):
    for x, y, t0, color in bursts:
        t = (now - t0) / 700
        if t > 1:
            continue
        r = int(20 + 90 * t)
        alpha = int(180 * (1 - t))
        size = r * 2
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, alpha), (r, r), r, width=6)
        surface.blit(s, (x - r, y - r))

# ============================================================
#  ГЛАВНЫЙ ЦИКЛ
# ============================================================

def main():
    enabled = [False] * len(INSTRUMENTS)
    # Немного включённого по умолчанию — чтобы сразу звучало
    enabled[0] = True   # барабан
    enabled[2] = True   # тарелки
    enabled[5] = True   # ксилофон

    is_playing = True
    current_step = 0
    last_step_time = pygame.time.get_ticks()
    STEP_MS = 160

    bursts = []

    running = True
    while running:
        now = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                if BTN_PLAY.collidepoint(mx, my):
                    is_playing = not is_playing
                    last_step_time = now

                elif BTN_CLEAR.collidepoint(mx, my):
                    enabled = [False] * len(INSTRUMENTS)

                elif BTN_RANDOM.collidepoint(mx, my):
                    enabled = [random.random() < 0.45 for _ in INSTRUMENTS]
                    if not any(enabled):
                        enabled[random.randrange(len(INSTRUMENTS))] = True

                else:
                    for i, rect in enumerate(BTN_RECTS):
                        if rect.collidepoint(mx, my):
                            enabled[i] = not enabled[i]
                            inst = INSTRUMENTS[i]
                            bursts.append([rect.centerx, rect.centery,
                                           now, inst['accent']])
                            if enabled[i]:
                                first = min(inst['pattern'])
                                key = inst['pattern'][first]
                                snd = INST_SOUNDS[inst['id']].get(key)
                                if snd:
                                    snd.play()
                            break

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    is_playing = not is_playing
                    last_step_time = now
                elif event.key == pygame.K_r:
                    enabled = [False] * len(INSTRUMENTS)
                elif event.key == pygame.K_m:
                    enabled = [random.random() < 0.45 for _ in INSTRUMENTS]
                    if not any(enabled):
                        enabled[random.randrange(len(INSTRUMENTS))] = True
                elif pygame.K_1 <= event.key <= pygame.K_8:
                    i = event.key - pygame.K_1
                    if i < len(INSTRUMENTS):
                        enabled[i] = not enabled[i]
                        rect = BTN_RECTS[i]
                        inst = INSTRUMENTS[i]
                        bursts.append([rect.centerx, rect.centery,
                                       now, inst['accent']])
                        if enabled[i]:
                            first = min(inst['pattern'])
                            snd = INST_SOUNDS[inst['id']].get(inst['pattern'][first])
                            if snd:
                                snd.play()

        # ----- продвижение секвенсора -----
        if is_playing:
            while now - last_step_time >= STEP_MS:
                last_step_time += STEP_MS
                if now - last_step_time > 3 * STEP_MS:
                    last_step_time = now
                    break
                current_step = (current_step + 1) % 16
                for i, inst in enumerate(INSTRUMENTS):
                    if enabled[i] and current_step in inst['pattern']:
                        key = inst['pattern'][current_step]
                        snd = INST_SOUNDS[inst['id']].get(key)
                        if snd:
                            snd.play()

        # ----- отрисовка -----
        # фон-градиент
        for y in range(0, HEIGHT, 4):
            t = y / HEIGHT
            c = (int(20 + 25 * t), int(15 + 10 * t), int(45 + 45 * t))
            pygame.draw.rect(screen, c, (0, y, WIDTH, 4))

        # мягкие плавающие круги на фоне
        for k in range(5):
            cx = (WIDTH // 6 * (k + 1) + int(40 * math.sin(now / 3000 + k))) % WIDTH
            cy = (HEIGHT // 5 * (k + 1) + int(30 * math.cos(now / 3500 + k))) % HEIGHT
            r = 60 + 30 * k
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 255, 255, 8), (r, r), r)
            screen.blit(s, (cx - r, cy - r))

        draw_header(screen, is_playing, now)

        for i, inst in enumerate(INSTRUMENTS):
            draw_instrument_button(screen, inst, BTN_RECTS[i],
                                   enabled[i], current_step, now)

        draw_footer(screen)
        draw_bursts(screen, bursts, now)
        bursts[:] = [b for b in bursts if now - b[2] < 700]

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()