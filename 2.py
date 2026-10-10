"""
🎨 Музыкальная раскраска — интерактивная раскраска для детей.

Запуск:  python music_coloring.py
Требуется: pip install pygame

Как играть:
  • Кликни по области картинки — она закрасится выбранным цветом.
  • Каждый цвет звучит своей нотой (До, Ре, Ми, Фа, Соль, Ля, Си, До²).
  • Кнопка «🎲» — случайная весёлая мелодия.
  • Кнопка «🧽» — очистить картинку.
  • Кнопка «🎵» — проиграть мелодию из цветов, которыми раскрашено.
  • Стрелки ← → листают картинки.
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
pygame.display.set_caption("Музыкальная раскраска")
clock = pygame.time.Clock()

# ============================================================
#  СИНТЕЗ ЗВУКОВ (без внешних файлов)
# ============================================================

def to_sound(samples):
    arr = array.array('h', [int(max(-1.0, min(1.0, s)) * 32000) for s in samples])
    return pygame.mixer.Sound(buffer=arr.tobytes())


def make_note(freq, duration=1.0):
    """Мягкий колокольчик: основной тон + 2 обертона."""
    n = int(SR * duration)
    samples = [0.0] * n
    partials = [(1.0, 1.00, 2.8), (2.0, 0.35, 4.0), (3.0, 0.12, 5.5)]
    for mult, amp, decay in partials:
        w = 2 * math.pi * freq * mult
        for i in range(n):
            t = i / SR
            samples[i] += math.sin(w * t) * amp * math.exp(-t * decay)
    peak = max(abs(s) for s in samples) or 1.0
    return to_sound([s / peak * 0.5 for s in samples])


def make_click():
    n = int(SR * 0.06)
    samples = []
    for i in range(n):
        t = i / SR
        s = math.sin(2 * math.pi * 1400 * t) * math.exp(-t * 45)
        samples.append(s * 0.25)
    return to_sound(samples)


print("Синтез звуков...")
NOTE_NAMES = ['До', 'Ре', 'Ми', 'Фа', 'Соль', 'Ля', 'Си', 'До²']
NOTE_FREQS = [523.25, 587.33, 659.25, 698.46, 783.99, 880.00, 987.77, 1046.50]
note_sounds = [make_note(f) for f in NOTE_FREQS]
click_sound = make_click()
print("Готово.")

# ============================================================
#  ПАЛИТРА ЦВЕТОВ (каждый цвет = нота)
# ============================================================

PALETTE = [
    ((255, 80, 90),   0),   # Красный    — До
    ((255, 165, 60),  1),   # Оранжевый  — Ре
    ((255, 230, 70),  2),   # Жёлтый     — Ми
    ((120, 225, 120), 3),   # Зелёный    — Фа
    ((90, 200, 255),  4),   # Голубой    — Соль
    ((110, 130, 255), 5),   # Синий      — Ля
    ((195, 130, 255), 6),   # Фиолетовый — Си
    ((255, 140, 200), 7),   # Розовый    — До²
]

PAPER = (250, 248, 236)
OUTLINE = (35, 35, 55)

# ============================================================
#  КЛАСС ОБЛАСТИ (закрашиваемой фигуры)
# ============================================================

class Region:
    def __init__(self, kind, coords, fill=(255, 255, 255)):
        self.kind = kind          # 'circle', 'rect', 'ellipse', 'polygon'
        self.coords = coords
        self.fill = fill

    def contains(self, x, y):
        k = self.kind
        if k == 'circle':
            cx, cy, r = self.coords
            return (x - cx) ** 2 + (y - cy) ** 2 <= r * r
        if k == 'rect':
            rx, ry, rw, rh = self.coords
            return rx <= x <= rx + rw and ry <= y <= ry + rh
        if k == 'ellipse':
            cx, cy, rx, ry = self.coords
            if rx == 0 or ry == 0:
                return False
            return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1
        if k == 'polygon':
            return self._in_poly(x, y)
        return False

    def _in_poly(self, x, y):
        pts = self.coords
        n = len(pts)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = pts[i]
            xj, yj = pts[j]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    def draw(self, surface, ox, oy):
        k = self.kind
        if k == 'circle':
            cx, cy, r = self.coords
            pygame.draw.circle(surface, self.fill, (cx + ox, cy + oy), r)
            pygame.draw.circle(surface, OUTLINE, (cx + ox, cy + oy), r, 4)
        elif k == 'rect':
            rx, ry, rw, rh = self.coords
            rect = pygame.Rect(rx + ox, ry + oy, rw, rh)
            pygame.draw.rect(surface, self.fill, rect, border_radius=10)
            pygame.draw.rect(surface, OUTLINE, rect, width=4, border_radius=10)
        elif k == 'ellipse':
            cx, cy, rx, ry = self.coords
            rect = pygame.Rect(cx - rx + ox, cy - ry + oy, rx * 2, ry * 2)
            pygame.draw.ellipse(surface, self.fill, rect)
            pygame.draw.ellipse(surface, OUTLINE, rect, width=4)
        elif k == 'polygon':
            pts = [(px + ox, py + oy) for px, py in self.coords]
            pygame.draw.polygon(surface, self.fill, pts)
            pygame.draw.polygon(surface, OUTLINE, pts, width=4)

    def reset(self):
        self.fill = (255, 255, 255)


# ============================================================
#  КАРТИНКИ (пространство 650 x 690)
# ============================================================

def make_house():
    return [
        Region('circle', (560, 100, 55)),                          # солнце
        Region('rect', (180, 380, 290, 260)),                      # стена
        Region('polygon', [(140, 380), (325, 230), (510, 380)]),   # крыша
        Region('rect', (200, 430, 80, 80)),                        # окно
        Region('rect', (270, 500, 90, 140)),                       # дверь
    ]


def make_flower():
    petals = []
    for i in range(6):
        a = -math.pi / 2 + i * math.pi / 3
        px = 325 + math.cos(a) * 90
        py = 290 + math.sin(a) * 90
        petals.append(Region('circle', (px, py, 55)))
    return [
        Region('rect', (315, 350, 20, 290)),           # стебель
        Region('ellipse', (265, 470, 60, 28)),         # левый лист
        Region('ellipse', (385, 545, 60, 28)),         # правый лист
        *petals,                                       # лепестки
        Region('circle', (325, 290, 55)),              # серединка
    ]


def make_fish():
    return [
        Region('polygon', [(155, 345), (45, 240), (45, 450)]),     # хвост
        Region('polygon', [(260, 245), (330, 190), (395, 255)]),   # плавник
        Region('ellipse', (325, 345, 170, 105)),                   # тело
        Region('circle', (430, 310, 22)),                          # глаз
        Region('circle', (540, 185, 18)),                          # пузыри
        Region('circle', (575, 135, 12)),
        Region('circle', (600, 95, 7)),
    ]


def make_butterfly():
    return [
        Region('ellipse', (240, 435, 75, 55)),         # нижнее левое крыло
        Region('ellipse', (410, 435, 75, 55)),         # нижнее правое
        Region('ellipse', (225, 310, 90, 75)),         # верхнее левое
        Region('ellipse', (425, 310, 90, 75)),         # верхнее правое
        Region('ellipse', (325, 360, 22, 120)),        # тело
        Region('circle', (325, 235, 22)),              # голова
    ]


PICTURES = [
    ("Домик",   make_house),
    ("Цветок",  make_flower),
    ("Рыбка",   make_fish),
    ("Бабочка", make_butterfly),
]
pictures_data = [fn() for _, fn in PICTURES]
current_pic = 0

# ============================================================
#  ШРИФТЫ
# ============================================================

def load_font(size, bold=False):
    for name in ("comicsansms", "segoeui", "arial", "dejavusans"):
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except Exception:
            pass
    return pygame.font.Font(None, size + 6)

font_title   = load_font(38, bold=True)
font_sub     = load_font(18)
font_header  = load_font(22, bold=True)
font_label   = load_font(20, bold=True)
font_button  = load_font(22, bold=True)
font_small   = load_font(15, bold=True)

# ============================================================
#  РАЗМЕТКА
# ============================================================

DRAW_RECT = pygame.Rect(25, 80, 660, 680)
PANEL_X = 700
PANEL_RECT = pygame.Rect(PANEL_X, 80, WIDTH - PANEL_X - 20, 680)

# --- палитра: 2 колонки × 4 ряда ---
SW_SIZE = 105
SW_GAP  = 18
sw_rects = []
sw_start_x = PANEL_X + 18
sw_start_y = 165
for i in range(8):
    col = i % 2
    row = i // 2
    x = sw_start_x + col * (SW_SIZE + SW_GAP)
    y = sw_start_y + row * (SW_SIZE + SW_GAP)
    sw_rects.append(pygame.Rect(x, y, SW_SIZE, SW_SIZE))

# --- кнопки под палитрой ---
BTN_W = PANEL_RECT.width - 36
BTN_H = 48
btn_y = sw_start_y + 4 * SW_SIZE + 3 * SW_GAP + 18

BTN_PREV  = pygame.Rect(PANEL_X + 18, btn_y, 60, BTN_H)
BTN_NEXT  = pygame.Rect(PANEL_X + PANEL_RECT.width - 78, btn_y, 60, BTN_H)
BTN_DICE  = pygame.Rect(PANEL_X + 18, btn_y + 62, BTN_W, BTN_H)
BTN_CLEAR = pygame.Rect(PANEL_X + 18, btn_y + 124, BTN_W, BTN_H)
BTN_PLAY  = pygame.Rect(PANEL_X + 18, btn_y + 186, BTN_W, BTN_H)

# ============================================================
#  СОСТОЯНИЕ
# ============================================================

selected_color_idx = 0
effects = []        # [x, y, t0, char, color]
melody_queue = []   # [(play_at_ms, sound)]
last_click_t = 0

NOTE_CHARS = ['♪', '♫', '♬', '♩']

# ============================================================
#  ЛОГИКА
# ============================================================

def current_regions():
    return pictures_data[current_pic]


def get_palette_color(idx):
    return PALETTE[idx][0]


def color_index_by_rgb(rgb):
    for i, (c, _) in enumerate(PALETTE):
        if c == rgb:
            return i
    return None


def spawn_note(x, y, color):
    effects.append([x, y, pygame.time.get_ticks(),
                    random.choice(NOTE_CHARS), color])


def try_paint(mx, my):
    """Красим область, если клик попал в неё."""
    global last_click_t
    if not DRAW_RECT.collidepoint(mx, my):
        return
    lx = mx - DRAW_RECT.x
    ly = my - DRAW_RECT.y

    regions = current_regions()
    for r in reversed(regions):       # сверху вниз
        if r.contains(lx, ly):
            r.fill = get_palette_color(selected_color_idx)
            note_sounds[selected_color_idx].play()
            spawn_note(mx, my, get_palette_color(selected_color_idx))
            last_click_t = pygame.time.get_ticks()
            return


def clear_picture():
    for r in current_regions():
        r.reset()
    click_sound.play()


def play_color_palette_melody():
    """Играет ноты всех цветов, которые есть на картинке."""
    used = []
    for r in current_regions():
        if r.fill != (255, 255, 255):
            idx = color_index_by_rgb(r.fill)
            if idx is not None:
                used.append(idx)
    if not used:
        used = [0, 2, 4, 7]

    now = pygame.time.get_ticks()
    for i, idx in enumerate(used):
        melody_queue.append((now + 150 + i * 320, note_sounds[idx]))


def play_surprise():
    """Случайная короткая мелодия."""
    now = pygame.time.get_ticks()
    seq = [random.randint(0, 7) for _ in range(8)]
    for i, idx in enumerate(seq):
        melody_queue.append((now + 150 + i * 260, note_sounds[idx]))


def update_melody(now):
    for item in melody_queue[:]:
        if now >= item[0]:
            item[1].play()
            melody_queue.remove(item)


def update_effects(now):
    for e in effects[:]:
        if now - e[2] > 1100:
            effects.remove(e)


def draw_effects(surface, now):
    for x, y, t0, ch, color in effects:
        t = (now - t0) / 1100
        cur_y = y - 170 * t
        alpha = int(255 * (1 - t) ** 0.6)
        size = int(28 + 14 * t)
        fnt = load_font(size, bold=True)
        img = fnt.render(ch, True, color)
        img.set_alpha(alpha)
        surface.blit(img, (x - img.get_width() // 2,
                           cur_y - img.get_height() // 2))

# ============================================================
#  ОТРИСОВКА
# ============================================================

def draw_title(surface):
    title = font_title.render("🎨  Музыкальная раскраска  🎵", True, (255, 240, 210))
    surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 22))

    sub = font_sub.render(
        "Выбери цвет — и раскрашивай! Каждый цвет звучит своей нотой.",
        True, (200, 200, 220))
    surface.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 60))


def draw_drawing_area(surface):
    # белый лист с лёгкой тенью
    shadow = DRAW_RECT.move(4, 6)
    pygame.draw.rect(surface, (0, 0, 0), shadow, border_radius=18)
    pygame.draw.rect(surface, PAPER, DRAW_RECT, border_radius=18)
    pygame.draw.rect(surface, (200, 195, 180), DRAW_RECT, width=3, border_radius=18)

    for r in current_regions():
        r.draw(surface, DRAW_RECT.x, DRAW_RECT.y)

    # название картинки
    name = PICTURES[current_pic][0]
    img = font_header.render(f"Картинка: {name}", True, (60, 40, 90))
    surface.blit(img, (DRAW_RECT.x + 12, DRAW_RECT.y + 10))


def draw_swatch(surface, rect, color, note_idx):
    pygame.draw.rect(surface, (0, 0, 0), rect.move(0, 5), border_radius=18)
    pygame.draw.rect(surface, color, rect, border_radius=18)
    pygame.draw.rect(surface, (255, 255, 255), rect, width=3, border_radius=18)

    # название ноты
    txt = font_label.render(NOTE_NAMES[note_idx], True, (40, 30, 60))
    surface.blit(txt, (rect.centerx - txt.get_width() // 2,
                       rect.centery - txt.get_height() // 2))


def draw_palette(surface):
    header = font_header.render("🎨  ЦВЕТА", True, (255, 230, 180))
    surface.blit(header, (PANEL_X + 18, 130))

    for i, rect in enumerate(sw_rects):
        color = PALETTE[i][0]
        draw_swatch(surface, rect, color, PALETTE[i][1])

        if i == selected_color_idx:
            pygame.draw.rect(surface, (255, 255, 255), rect.inflate(14, 14),
                             width=4, border_radius=22)
            pygame.draw.rect(surface, (40, 30, 60), rect.inflate(8, 8),
                             width=2, border_radius=20)


def draw_button(surface, rect, text, base, hover, icon_only=False):
    mx, my = pygame.mouse.get_pos()
    hovered = rect.collidepoint(mx, my)
    c = hover if hovered else base
    shadow = tuple(max(0, x - 70) for x in c)

    pygame.draw.rect(surface, shadow, rect.move(0, 5), border_radius=16)
    pygame.draw.rect(surface, c, rect, border_radius=16)
    pygame.draw.rect(surface, (255, 255, 255), rect, width=2, border_radius=16)

    txt = font_button.render(text, True, (35, 25, 60))
    surface.blit(txt, (rect.centerx - txt.get_width() // 2,
                       rect.centery - txt.get_height() // 2))


def draw_buttons(surface):
    # стрелки — по бокам от подписи картинки
    name_rect = pygame.Rect(BTN_PREV.right + 6, BTN_PREV.y,
                            BTN_NEXT.left - BTN_PREV.right - 12, BTN_H)
    pygame.draw.rect(surface, (70, 55, 110), name_rect, border_radius=12)
    name = PICTURES[current_pic][0]
    txt = font_label.render(name, True, (240, 235, 255))
    surface.blit(txt, (name_rect.centerx - txt.get_width() // 2,
                       name_rect.centery - txt.get_height() // 2))

    draw_button(surface, BTN_PREV,  "◀",  (200, 190, 240), (230, 220, 255))
    draw_button(surface, BTN_NEXT,  "▶",  (200, 190, 240), (230, 220, 255))
    draw_button(surface, BTN_DICE,  "🎲  Сюрприз",     (255, 210, 90),  (255, 230, 130))
    draw_button(surface, BTN_CLEAR, "🧽  Очистить",    (200, 230, 255), (225, 245, 255))
    draw_button(surface, BTN_PLAY,  "🎵  Проиграть",   (200, 255, 200), (225, 255, 225))


# ============================================================
#  ГЛАВНЫЙ ЦИКЛ
# ============================================================

def main():
    global selected_color_idx, current_pic
    running = True

    while running:
        now = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                # кнопки панели
                if BTN_PREV.collidepoint(mx, my):
                    current_pic = (current_pic - 1) % len(PICTURES)
                    click_sound.play()
                elif BTN_NEXT.collidepoint(mx, my):
                    current_pic = (current_pic + 1) % len(PICTURES)
                    click_sound.play()
                elif BTN_DICE.collidepoint(mx, my):
                    play_surprise()
                elif BTN_CLEAR.collidepoint(mx, my):
                    clear_picture()
                elif BTN_PLAY.collidepoint(mx, my):
                    play_color_palette_melody()
                else:
                    # проверяем палитру
                    hit_swatch = False
                    for i, rect in enumerate(sw_rects):
                        if rect.collidepoint(mx, my):
                            selected_color_idx = i
                            note_sounds[PALETTE[i][1]].play()
                            spawn_note(mx, my, PALETTE[i][0])
                            hit_swatch = True
                            break
                    if not hit_swatch:
                        try_paint(mx, my)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_LEFT:
                    current_pic = (current_pic - 1) % len(PICTURES)
                    click_sound.play()
                elif event.key == pygame.K_RIGHT:
                    current_pic = (current_pic + 1) % len(PICTURES)
                    click_sound.play()
                elif event.key == pygame.K_SPACE:
                    play_surprise()
                elif event.key == pygame.K_c:
                    clear_picture()
                elif event.key == pygame.K_RETURN:
                    play_color_palette_melody()
                elif pygame.K_1 <= event.key <= pygame.K_8:
                    idx = event.key - pygame.K_1
                    selected_color_idx = idx
                    note_sounds[PALETTE[idx][1]].play()
                    spawn_note(WIDTH // 2, HEIGHT // 2, PALETTE[idx][0])

        update_melody(now)
        update_effects(now)

        # ---------- ОТРИСОВКА ----------
        screen.fill((26, 20, 55))

        # фон-градиент сверху вниз
        for y in range(0, HEIGHT, 4):
            t = y / HEIGHT
            c = (int(26 + 30 * t), int(20 + 10 * t), int(55 + 30 * t))
            pygame.draw.rect(screen, c, (0, y, WIDTH, 4))

        draw_title(screen)
        draw_drawing_area(screen)
        draw_palette(screen)
        draw_buttons(screen)
        draw_effects(screen, now)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()