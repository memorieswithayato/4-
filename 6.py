"""
🎵 Повтори мелодию — игра на слух и память.

Запуск:  python repeat_melody.py
Требуется: pip install pygame

Как играть:
  • Компьютер играет короткую мелодию — слушай!
  • Повтори её, нажимая на большие цветные кнопки с нотами.
  • Каждый раз при успехе мелодия становится на 1 ноту длиннее.
  • Дойди до 10 нот — и ты победил!

Управление:
  Мышка — нажимать ноты.
  Клавиши 1–8 (и A–K) — те же ноты.
  ПРОБЕЛ — прослушать заново.
  H — подсказка.
  R — начать сначала.
  ESC — выход.
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
WIDTH, HEIGHT = 1200, 820
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Повтори мелодию")
clock = pygame.time.Clock()

# ============================================================
#  СИНТЕЗ ЗВУКОВ
# ============================================================

def to_sound(samples):
    arr = array.array('h', [int(max(-1.0, min(1.0, s)) * 32000) for s in samples])
    return pygame.mixer.Sound(buffer=arr.tobytes())


def make_note(freq, dur=0.75, amp=0.55):
    """Мягкий «колокольчик» — как у ксилофона."""
    n = int(SR * dur)
    out = [0.0] * n
    partials = [(1.0, 1.00, 4.0), (2.0, 0.42, 5.5),
                (3.0, 0.16, 7.0), (4.0, 0.06, 9.0)]
    for mult, p_amp, decay in partials:
        w = 2 * math.pi * freq * mult
        for i in range(n):
            t = i / SR
            out[i] += math.sin(w * t) * p_amp * math.exp(-t * decay)
    attack = max(1, int(SR * 0.006))
    for i in range(attack):
        out[i] *= i / attack
    peak = max(abs(s) for s in out) or 1.0
    return to_sound([s / peak * amp for s in out])


def make_success():
    """Восходящее арпеджио для победы в раунде."""
    notes = [523.25, 659.25, 783.99, 1046.50]
    step = int(SR * 0.09)
    out = []
    for f in notes:
        w = 2 * math.pi * f
        for i in range(step):
            t = i / SR
            env = math.exp(-t * 7)
            out.append(math.sin(w * t) * env * 0.35 +
                       math.sin(2 * w * t) * env * 0.10)
    return to_sound(out)


def make_error():
    """Мягкий «упс» — две нисходящие нотки, не пугает."""
    dur = 0.55
    n = int(SR * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        f = 330 - 60 * (t / dur)
        phase += 2 * math.pi * f / SR
        env = math.exp(-t * 3.5) * min(1, t * 20)
        out.append(math.sin(phase) * env * 0.40)
    return to_sound(out)


def make_fanfare():
    """Праздничная мелодия при победе."""
    notes = [523.25, 659.25, 783.99, 1046.50, 783.99, 1046.50]
    step = int(SR * 0.14)
    out = []
    for f in notes:
        w = 2 * math.pi * f
        for i in range(step):
            t = i / SR
            env = math.exp(-t * 4)
            out.append(math.sin(w * t) * env * 0.30 +
                       math.sin(2 * w * t) * env * 0.08)
    return to_sound(out)


def make_click():
    n = int(SR * 0.05)
    out = []
    for i in range(n):
        t = i / SR
        out.append(math.sin(2 * math.pi * 1200 * t) * math.exp(-t * 45) * 0.25)
    return to_sound(out)


def make_start():
    """Стартовое «пиу-пиу-пиу»."""
    notes = [392.00, 523.25, 659.25]
    step = int(SR * 0.10)
    out = []
    for f in notes:
        w = 2 * math.pi * f
        for i in range(step):
            t = i / SR
            env = math.exp(-t * 6)
            out.append(math.sin(w * t) * env * 0.35)
    return to_sound(out)


print("Синтез звуков...")

# Ноты мажорной гаммы (До мажор, 1-я октава + До 2-й октавы)
NOTE_DEFS = [
    # (название, частота, основной цвет, светлый оттенок)
    ('До',    261.63, (240,  90,  90), (255, 160, 160)),
    ('Ре',    293.66, (245, 150,  70), (255, 205, 140)),
    ('Ми',    329.63, (245, 215,  80), (255, 240, 165)),
    ('Фа',    349.23, (150, 220, 110), (205, 245, 185)),
    ('Соль',  392.00, ( 90, 205, 190), (165, 240, 230)),
    ('Ля',    440.00, (105, 165, 240), (175, 210, 255)),
    ('Си',    493.88, (165, 130, 240), (215, 190, 255)),
    ('До²',   523.25, (245, 130, 200), (255, 195, 235)),
]

note_sounds = [make_note(f) for _, f, _, _ in NOTE_DEFS]
success_sound = make_success()
error_sound = make_error()
fanfare_sound = make_fanfare()
click_sound = make_click()
start_sound = make_start()

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


font_title = get_font(46, bold=True)
font_sub   = get_font(20)
font_msg   = get_font(34, bold=True)
font_note  = get_font(40, bold=True)
font_sym   = get_font(40, bold=True)
font_btn   = get_font(22, bold=True)
font_small = get_font(16, bold=True)
font_score = get_font(24, bold=True)

# ============================================================
#  РАЗМЕТКА
# ============================================================

BTN_MARGIN = 24
BTN_GAP = 12
BTN_W = (WIDTH - 2 * BTN_MARGIN - 7 * BTN_GAP) // 8
BTN_H = 290
BTN_Y = 430

btn_rects = [
    pygame.Rect(BTN_MARGIN + i * (BTN_W + BTN_GAP), BTN_Y, BTN_W, BTN_H)
    for i in range(8)
]

# Верхние кнопки управления
BTN_REPLAY = pygame.Rect(WIDTH - 540, 18, 170, 46)
BTN_HINT   = pygame.Rect(WIDTH - 360, 18, 170, 46)
BTN_RESET  = pygame.Rect(WIDTH - 180, 18, 160, 46)

# Счёт
SCORE_RECT = pygame.Rect(20, 18, 320, 46)

# Область сообщения
MESSAGE_Y = 110
STRIP_Y = 185       # полоска с точками-нотами
STRIP_H = 90

# ============================================================
#  ВСПОМОГАТЕЛЬНОЕ
# ============================================================

def lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


ripples = []   # [x, y, t0, color, max_r]
sparkles = []  # [x, y, t0, color, vx, vy]
play_glow = {} # note_idx -> ms


def spawn_ripple(x, y, color):
    ripples.append([x, y, pygame.time.get_ticks(), color, 180])


def spawn_sparkle(x, y, color):
    angle = random.uniform(0, 2 * math.pi)
    speed = random.uniform(2.0, 5.5)
    sparkles.append([x, y, pygame.time.get_ticks(), color,
                     math.cos(angle) * speed, math.sin(angle) * speed])


def update_effects(now):
    for r in ripples[:]:
        if now - r[2] > 700:
            ripples.remove(r)
    for s in sparkles[:]:
        if now - s[2] > 1200:
            sparkles.remove(s)


def draw_effects(surface, now):
    # Волны
    for x, y, t0, color, max_r in ripples:
        t = (now - t0) / 700
        radius = int(max_r * t)
        if radius < 2:
            continue
        alpha = int(210 * (1 - t))
        size = radius * 2 + 6
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, alpha), (size // 2, size // 2),
                           radius, max(2, int(7 * (1 - t))))
        surface.blit(s, (x - size // 2, y - size // 2))

    # Искры
    for x, y, t0, color, vx, vy in sparkles:
        t = (now - t0) / 1200
        cx = x + vx * (now - t0) * 0.25
        cy = y + vy * (now - t0) * 0.25 + 0.0008 * (now - t0) ** 2
        alpha = int(255 * max(0.0, 1 - t))
        size = int(10 * (1 - t) + 3)
        s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, alpha), (size, size), size)
        surface.blit(s, (cx - size, cy - size))


# ============================================================
#  СОСТОЯНИЕ ИГРЫ
# ============================================================

sequence = []            # список индексов нот (мелодия)
input_index = 0          # сколько нот уже правильно нажал игрок
phase = 'listen'         # listen | input | win | error | game_won
phase_t0 = 0
listen_played = set()    # какие ноты уже проиграны на этом проигрывании
current_round = 0
score = 0
max_len_reached = 0
consecutive_errors = 0
hint_note_idx = -1
hint_until = 0

START_LEN = 3
MAX_LEN = 10
NOTE_INTERVAL = 560      # мс между нотами при воспроизведении
PAUSE_AFTER = 320        # мс пауза после последней ноты


def start_listen(now):
    global phase, phase_t0, listen_played, input_index
    phase = 'listen'
    phase_t0 = now
    listen_played = set()
    input_index = 0


def start_new_game(now):
    global sequence, score, current_round, max_len_reached, consecutive_errors
    global input_index
    sequence = [random.randrange(8) for _ in range(START_LEN)]
    score = 0
    current_round = 1
    max_len_reached = START_LEN
    consecutive_errors = 0
    input_index = 0
    if start_sound:
        start_sound.play()
    start_listen(now)


def handle_note_press(i, mx, my, now):
    global input_index, phase, phase_t0, score, max_len_reached
    global consecutive_errors, hint_note_idx, hint_until

    if phase != 'input':
        return

    # Звук самой ноты
    note_sounds[i].play()
    play_glow[i] = now

    # Волна и искра
    rect = btn_rects[i]
    spawn_ripple(rect.centerx, rect.centery, NOTE_DEFS[i][2])
    for _ in range(6):
        spawn_sparkle(rect.centerx, rect.centery, NOTE_DEFS[i][3])

    # Сбрасываем подсказку
    hint_until = 0
    hint_note_idx = -1

    # Проверяем правильность
    if i == sequence[input_index]:
        input_index += 1
        consecutive_errors = 0
        if input_index >= len(sequence):
            # Раунд пройден!
            score += 1
            if len(sequence) > max_len_reached:
                max_len_reached = len(sequence)
            phase = 'win'
            phase_t0 = now
            success_sound.play()

            # Праздничные искры
            for _ in range(40):
                rect = btn_rects[sequence[-1]]
                spawn_sparkle(rect.centerx + random.randint(-80, 80),
                              rect.centery + random.randint(-120, 40),
                              random.choice([
                                  (255, 220, 100), (255, 150, 200),
                                  (150, 220, 255), (200, 255, 150)]))
    else:
        # Ошибка
        phase = 'error'
        phase_t0 = now
        consecutive_errors += 1
        error_sound.play()


def start_hint(now):
    """Подсветить следующую ожидаемую ноту."""
    global hint_note_idx, hint_until
    if phase != 'input' or input_index >= len(sequence):
        return
    hint_note_idx = sequence[input_index]
    hint_until = now + 900
    # Тихо проиграем эту ноту — ещё один намёк
    note_sounds[hint_note_idx].play()
    play_glow[hint_note_idx] = now


# ============================================================
#  ОТРИСОВКА
# ============================================================

def draw_background(now):
    # Плавный градиент
    for y in range(0, HEIGHT, 4):
        t = y / HEIGHT
        c = (int(30 + 25 * t), int(20 + 15 * t), int(60 + 30 * t))
        pygame.draw.rect(screen, c, (0, y, WIDTH, 4))

    # Мягкие плавающие пузыри
    for k in range(6):
        cx = int((WIDTH // 6) * (k + 0.5) +
                 60 * math.sin(now / 4000 + k * 1.3))
        cy = int(HEIGHT * 0.45 + 80 * math.cos(now / 5000 + k * 0.9))
        r = 80 + 30 * k
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 255, 255, 6), (r, r), r)
        screen.blit(s, (cx - r, cy - r))


def draw_header(now):
    # Заголовок
    title = font_title.render("🎵 Повтори мелодию", True, (255, 240, 200))
    shadow = font_title.render("🎵 Повтори мелодию", True, (70, 30, 90))
    screen.blit(shadow, (24, 26))
    screen.blit(title, (22, 24))

    # Счёт
    pygame.draw.rect(screen, (60, 45, 100), SCORE_RECT, border_radius=14)
    pygame.draw.rect(screen, (255, 220, 100), SCORE_RECT, 3, border_radius=14)
    txt = font_score.render(
        f"⭐ Раунд: {current_round}   |   Нот: {len(sequence) if sequence else 0}",
        True, (255, 240, 200))
    screen.blit(txt, (SCORE_RECT.centerx - txt.get_width() // 2,
                      SCORE_RECT.centery - txt.get_height() // 2))

    # Кнопки управления
    mx, my = pygame.mouse.get_pos()

    for rect, label, base in [
        (BTN_REPLAY, "🔁 Прослушать", (110, 180, 240)),
        (BTN_HINT,   "💡 Подсказка",  (255, 210, 90)),
        (BTN_RESET,  "🔄 Заново",     (200, 160, 230)),
    ]:
        hovered = rect.collidepoint(mx, my)
        c = tuple(min(255, x + 30) for x in base) if hovered else base
        sh = tuple(max(0, x - 70) for x in c)
        pygame.draw.rect(screen, sh, rect.move(0, 4), border_radius=12)
        pygame.draw.rect(screen, c, rect, border_radius=12)
        pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=12)
        t = font_btn.render(label, True, (30, 20, 50))
        screen.blit(t, (rect.centerx - t.get_width() // 2,
                        rect.centery - t.get_height() // 2))


def draw_message(now):
    if phase == 'listen':
        # Если сейчас играет — покажем, какая нота
        elapsed = now - phase_t0
        current_playing = -1
        for k, note_idx in enumerate(sequence):
            t_start = k * NOTE_INTERVAL
            if t_start <= elapsed < t_start + NOTE_INTERVAL * 0.75:
                current_playing = k
                break
        msg = "👂 Слушай внимательно..."
        col = (255, 240, 180)
    elif phase == 'input':
        msg = "🎹 Твой ход! Повтори мелодию"
        col = (180, 240, 200)
    elif phase == 'win':
        msg = "🎉 Молодец! Правильно!"
        col = (255, 220, 120)
    elif phase == 'error':
        msg = "🤔 Ой! Послушай ещё раз..."
        col = (255, 180, 180)
    elif phase == 'game_won':
        msg = "🏆 Победа! Ты справился!"
        col = (255, 230, 120)
    else:
        msg = ""
        col = (255, 255, 255)

    img = font_msg.render(msg, True, col)
    sh = font_msg.render(msg, True, (0, 0, 0))
    x = WIDTH // 2 - img.get_width() // 2
    screen.blit(sh, (x + 3, MESSAGE_Y + 3))
    screen.blit(img, (x, MESSAGE_Y))


def draw_melody_strip(now):
    """Полоска с точками — сколько нот в мелодии и где мы сейчас."""
    if not sequence:
        return

    n = len(sequence)
    dot_r = 18 if n <= 6 else (14 if n <= 8 else 11)
    gap = 20
    total_w = n * (dot_r * 2 + gap) - gap
    start_x = WIDTH // 2 - total_w // 2
    cy = STRIP_Y + STRIP_H // 2

    for k, note_idx in enumerate(sequence):
        cx = start_x + k * (dot_r * 2 + gap) + dot_r
        color = NOTE_DEFS[note_idx][2]
        light = NOTE_DEFS[note_idx][3]

        # Базовая точка
        pygame.draw.circle(screen, (45, 35, 75), (cx, cy), dot_r + 4)
        pygame.draw.circle(screen, color, (cx, cy), dot_r)

        # Что произошло:
        if phase in ('input', 'win', 'error') and k < input_index:
            # Уже правильно сыграно — светлая галочка
            pygame.draw.circle(screen, light, (cx, cy), dot_r)
            pygame.draw.circle(screen, (255, 255, 255), (cx, cy), dot_r, 3)
            # Галочка
            pygame.draw.lines(screen, (60, 160, 80), False, [
                (cx - dot_r // 2, cy),
                (cx - dot_r // 6, cy + dot_r // 2),
                (cx + dot_r // 2, cy - dot_r // 2),
            ], 4)

        if phase == 'listen':
            # Подсветим играющую сейчас ноту
            elapsed = now - phase_t0
            t_start = k * NOTE_INTERVAL
            if t_start <= elapsed < t_start + NOTE_INTERVAL * 0.75:
                pulse = 1 - (elapsed - t_start) / (NOTE_INTERVAL * 0.75)
                r2 = dot_r + 6 + int(8 * pulse)
                pygame.draw.circle(screen, (255, 255, 255), (cx, cy), r2, 3)
                pygame.draw.circle(screen, light, (cx, cy), dot_r)

        if phase == 'input' and k == input_index:
            # Текущая ожидаемая — пульсирующий контур
            pulse = 0.5 + 0.5 * math.sin(now / 180)
            r2 = dot_r + 4 + int(4 * pulse)
            pygame.draw.circle(screen, (255, 255, 255), (cx, cy), r2, 3)

        if phase == 'error' and k == input_index:
            # Где споткнулись
            pulse = 0.5 + 0.5 * math.sin(now / 100)
            r2 = dot_r + 6 + int(4 * pulse)
            pygame.draw.circle(screen, (255, 100, 120), (cx, cy), r2, 4)


def draw_note_button(i, now):
    rect = btn_rects[i]
    name, freq, color, light = NOTE_DEFS[i]

    # Величина свечения от нажатия
    t_glow = 0.0
    if i in play_glow:
        dt = now - play_glow[i]
        if dt < 340:
            t_glow = 1 - dt / 340

    # Подсветка при наведении мыши
    mx, my = pygame.mouse.get_pos()
    hover = rect.collidepoint(mx, my) and phase == 'input'

    # Подсказка: если hint_note_idx == i и не вышло время
    hint_active = (i == hint_note_idx and now < hint_until)
    if hint_active:
        hp = 0.5 + 0.5 * math.sin(now / 130)
        t_glow = max(t_glow, 0.6 + 0.4 * hp)

    # Отскок (кнопка как будто уходит вглубь при свечении)
    offset = int(7 * t_glow)

    # Тень
    shadow_rect = rect.move(0, 9 - offset)
    shadow_color = tuple(max(0, c - 95) for c in color)
    pygame.draw.rect(screen, shadow_color, shadow_rect, border_radius=26)

    # Основная часть
    body = rect.move(0, -offset)
    base_color = color
    if t_glow > 0:
        base_color = lerp_color(color, (255, 255, 255), 0.55 * t_glow)
    elif hover:
        base_color = lerp_color(color, (255, 255, 255), 0.18)

    pygame.draw.rect(screen, base_color, body, border_radius=26)

    # Верхняя светлая полоса (глянец)
    gloss = pygame.Rect(body.x + 12, body.y + 12, body.w - 24, 46)
    gloss_color = lerp_color(base_color, (255, 255, 255), 0.5)
    gsurf = pygame.Surface(gloss.size, pygame.SRCALPHA)
    pygame.draw.rect(gsurf, (*gloss_color, 120), gsurf.get_rect(),
                     border_radius=18)
    screen.blit(gsurf, gloss.topleft)

    # Обводка
    pygame.draw.rect(screen, (255, 255, 255), body, 3, border_radius=26)

    # Нотный символ сверху
    sym = font_sym.render("♪", True, (255, 255, 255))
    sx = body.centerx - sym.get_width() // 2
    sy = body.y + 26
    screen.blit(font_sym.render("♪", True, (0, 0, 0)), (sx + 2, sy + 2))
    screen.blit(sym, (sx, sy))

    # Название ноты
    img = font_note.render(name, True, (255, 255, 255))
    sh = font_note.render(name, True, (0, 0, 0))
    nx = body.centerx - img.get_width() // 2
    ny = body.centery - img.get_height() // 2 + 40
    screen.blit(sh, (nx + 3, ny + 3))
    screen.blit(img, (nx, ny))

    # Номер-клавиша мелким шрифтом внизу
    num = font_small.render(str(i + 1), True, (255, 255, 255, 200))
    screen.blit(num, (body.centerx - num.get_width() // 2,
                      body.bottom - num.get_height() - 12))


def draw_game_won(now):
    """Оверлей при победе."""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((20, 10, 40, 180))
    screen.blit(overlay, (0, 0))

    title = font_title.render("🏆 Победа!", True, (255, 240, 120))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 120))

    sub = font_msg.render(f"Ты повторил мелодию из {MAX_LEN} нот!",
                          True, (255, 240, 200))
    screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, HEIGHT // 2 - 50))

    info = font_sub.render("Нажми 🔄 Заново или ПРОБЕЛ, чтобы играть ещё",
                           True, (210, 200, 240))
    screen.blit(info, (WIDTH // 2 - info.get_width() // 2, HEIGHT // 2 + 20))


# ============================================================
#  ГЛАВНЫЙ ЦИКЛ
# ============================================================

def main():
    global phase, phase_t0, sequence, input_index, current_round
    global score, max_len_reached, consecutive_errors, hint_until, hint_note_idx

    start_new_game(pygame.time.get_ticks())

    running = True
    while running:
        now = pygame.time.get_ticks()

        # ---------- события ----------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                if BTN_REPLAY.collidepoint(mx, my):
                    if phase in ('input', 'error', 'win'):
                        start_listen(now)
                elif BTN_HINT.collidepoint(mx, my):
                    start_hint(now)
                elif BTN_RESET.collidepoint(mx, my):
                    start_new_game(now)
                else:
                    for i, rect in enumerate(btn_rects):
                        if rect.collidepoint(mx, my):
                            handle_note_press(i, mx, my, now)
                            break

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    if phase == 'game_won':
                        start_new_game(now)
                    elif phase in ('input', 'error', 'win'):
                        start_listen(now)
                elif event.key == pygame.K_r:
                    start_new_game(now)
                elif event.key == pygame.K_h:
                    start_hint(now)
                elif pygame.K_1 <= event.key <= pygame.K_8:
                    i = event.key - pygame.K_1
                    mx, my = btn_rects[i].center
                    handle_note_press(i, mx, my, now)
                else:
                    # буквы a..k для нот
                    keymap = {'a': 0, 's': 1, 'd': 2, 'f': 3,
                              'g': 4, 'h': 5, 'j': 6, 'k': 7}
                    ch = event.unicode.lower() if event.unicode else ''
                    if ch in keymap:
                        i = keymap[ch]
                        mx, my = btn_rects[i].center
                        handle_note_press(i, mx, my, now)

        # ---------- логика фаз ----------
        if phase == 'listen':
            elapsed = now - phase_t0
            for k, note_idx in enumerate(sequence):
                if k not in listen_played and elapsed >= k * NOTE_INTERVAL:
                    listen_played.add(k)
                    note_sounds[note_idx].play()
                    play_glow[note_idx] = now
                    rect = btn_rects[note_idx]
                    spawn_ripple(rect.centerx, rect.centery,
                                 NOTE_DEFS[note_idx][2])
            if elapsed >= len(sequence) * NOTE_INTERVAL + PAUSE_AFTER:
                phase = 'input'
                input_index = 0
                phase_t0 = now

        elif phase == 'win':
            if now - phase_t0 > 1400:
                # Следующий раунд
                if len(sequence) >= MAX_LEN:
                    phase = 'game_won'
                    phase_t0 = now
                    fanfare_sound.play()
                else:
                    sequence.append(random.randrange(8))
                    current_round += 1
                    start_listen(now)

        elif phase == 'error':
            if now - phase_t0 > 1100:
                # Автоподсказка после 2 ошибок подряд
                if consecutive_errors >= 2:
                    start_hint(now)
                start_listen(now)

        update_effects(now)

        # ---------- отрисовка ----------
        draw_background(now)
        draw_header(now)
        draw_message(now)
        draw_melody_strip(now)

        for i in range(8):
            draw_note_button(i, now)

        draw_effects(screen, now)

        if phase == 'game_won':
            draw_game_won(now)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()