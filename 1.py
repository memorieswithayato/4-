"""
🎵 Музыкальные кнопки — интерактивная музыкальная программа для детей.
Запуск:  python music_pads.py
Требуется: pip install pygame
"""

import math
import random
import array
import colorsys
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
WIDTH, HEIGHT = 960, 720

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Музыкальные кнопки для детей")
clock = pygame.time.Clock()

# ============================================================
#  СИНТЕЗ ЗВУКОВ (без внешних файлов)
# ============================================================

def to_sound(samples):
    """Превращает список сэмплов [-1..1] в pygame.Sound."""
    arr = array.array('h', [int(max(-1.0, min(1.0, s)) * 32000) for s in samples])
    return pygame.mixer.Sound(buffer=arr.tobytes())


def make_kick():
    n = int(SR * 0.45)
    out = []
    for i in range(n):
        t = i / SR
        f = 160 * math.exp(-t * 18) + 45
        env = math.exp(-t * 9)
        out.append(math.sin(2 * math.pi * f * t) * env * 0.9)
    return to_sound(out)


def make_snare():
    n = int(SR * 0.25)
    out = []
    for i in range(n):
        t = i / SR
        noise = random.random() * 2 - 1
        env = math.exp(-t * 18)
        body_f = 200 * math.exp(-t * 20) + 100
        body = math.sin(2 * math.pi * body_f * t) * math.exp(-t * 22)
        s = (noise * 0.6 + body * 0.55) * env
        out.append(s * 0.85)
    return to_sound(out)


def make_tom():
    n = int(SR * 0.5)
    out = []
    for i in range(n):
        t = i / SR
        f = 280 * math.exp(-t * 10) + 90
        env = math.exp(-t * 6)
        out.append(math.sin(2 * math.pi * f * t) * env * 0.9)
    return to_sound(out)


def make_hat():
    n = int(SR * 0.12)
    out = []
    prev = 0.0
    for i in range(n):
        t = i / SR
        noise = random.random() * 2 - 1
        hp = noise - prev          # грубый фильтр ВЧ
        prev = noise
        env = math.exp(-t * 45)
        out.append(hp * env * 0.35)
    return to_sound(out)


def make_crash():
    n = int(SR * 1.5)
    out = []
    prev = 0.0
    for i in range(n):
        t = i / SR
        noise = random.random() * 2 - 1
        hp = noise - prev * 0.8
        prev = noise
        env = math.exp(-t * 3)
        out.append(hp * env * 0.5)
    return to_sound(out)


def make_bell(freq):
    # Колокол = сумма негармонических обертонов
    partials = [(1.0, 1.0, 2.0), (2.01, 0.5, 2.5), (2.98, 0.3, 3.5), (5.4, 0.13, 5.0)]
    dur = 1.8
    n = int(SR * dur)
    samples = [0.0] * n
    for mult, amp, decay in partials:
        w = 2 * math.pi * freq * mult
        for i in range(n):
            t = i / SR
            samples[i] += math.sin(w * t) * amp * math.exp(-t * decay)
    peak = max(abs(s) for s in samples) or 1.0
    samples = [s / peak * 0.55 for s in samples]
    return to_sound(samples)


print("Загрузка звуков...")
sounds = {
    'kick':  make_kick(),
    'snare': make_snare(),
    'tom':   make_tom(),
    'hat':   make_hat(),
    'crash': make_crash(),
}

NOTE_NAMES = ['До', 'Ре', 'Ми', 'Фа', 'Соль', 'Ля', 'Си', 'До']
NOTE_FREQS = [523.25, 587.33, 659.25, 698.46, 783.99, 880.00, 987.77, 1046.50]
bell_sounds = [make_bell(f) for f in NOTE_FREQS]
print("Готово!")

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

font_title = load_font(42, bold=True)
font_hint  = load_font(18)
font_label = load_font(22, bold=True)
font_small = load_font(16, bold=True)
font_note  = load_font(30, bold=True)

# ============================================================
#  ЦВЕТА И ФОН
# ============================================================

BG_TOP    = (36, 27, 87)
BG_BOTTOM = (90, 20, 64)


def lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


bg_surface = pygame.Surface((WIDTH, HEIGHT))
for y in range(HEIGHT):
    t = y / HEIGHT
    pygame.draw.line(bg_surface, lerp_color(BG_TOP, BG_BOTTOM, t),
                     (0, y), (WIDTH, y))

# ============================================================
#  КЛАСС КНОПКИ
# ============================================================

class Pad:
    def __init__(self, rect, label, color_light, color_dark, sound, key):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.c1 = color_light
        self.c2 = color_dark
        self.sound = sound
        self.key = key
        self.hit_time = -9999

    def press(self):
        self.sound.play()
        self.hit_time = pygame.time.get_ticks()

    def draw(self, surface):
        now = pygame.time.get_ticks()
        dt = now - self.hit_time
        pressed = dt < 130
        offset = 6 if pressed else 0
        face = self.rect.move(0, offset)

        # тень (тёмная нижняя часть)
        shadow_rect = self.rect.move(0, 10)
        shadow_color = tuple(max(0, c - 60) for c in self.c2)
        pygame.draw.rect(surface, shadow_color, shadow_rect, border_radius=26)

        # основная (нижняя) часть — тёмная
        pygame.draw.rect(surface, self.c2, face, border_radius=26)

        # верхняя светлая часть
        top = pygame.Rect(face.x + 4, face.y + 4, face.width - 8, face.height - 20)
        pygame.draw.rect(surface, self.c1, top, border_radius=22)

        # белая обводка
        pygame.draw.rect(surface, (255, 255, 255), face, width=3, border_radius=26)

        # блик
        gloss = pygame.Rect(face.x + 12, face.y + 10, face.width - 24, 14)
        gloss_surf = pygame.Surface(gloss.size, pygame.SRCALPHA)
        gloss_surf.fill((255, 255, 255, 90))
        surface.blit(gloss_surf, gloss.topleft)

        # подпись
        shadow_txt = font_label.render(self.label, True, (0, 0, 0))
        txt = font_label.render(self.label, True, (255, 255, 255))
        tx = face.centerx - txt.get_width() // 2
        ty = face.centery - txt.get_height() // 2 + 6
        surface.blit(shadow_txt, (tx + 2, ty + 2))
        surface.blit(txt, (tx, ty))


# ============================================================
#  РАСКЛАДКА ИНТЕРФЕЙСА
# ============================================================

pads = []

def build_layout():
    pads.clear()
    margin = 30
    gap = 16

    # --- барабаны (верхний ряд) ---
    drum_y = 155
    drum_h = 145
    drum_w = (WIDTH - 2 * margin - 4 * gap) // 5
    drum_defs = [
        ("БУМ",   (255, 150, 140), (200, 40, 40),  sounds['kick'],  '1'),
        ("БАМ",   (255, 215, 110), (215, 130, 0),  sounds['snare'], '2'),
        ("ТУК",   (175, 235, 110), (45, 140, 60),  sounds['tom'],   '3'),
        ("ЦСС",   (130, 200, 255), (20, 100, 190), sounds['hat'],   '4'),
        ("ДЗЫНЬ", (215, 195, 255), (105, 65, 215), sounds['crash'], '5'),
    ]
    for i, (label, c1, c2, snd, key) in enumerate(drum_defs):
        x = margin + i * (drum_w + gap)
        pads.append(Pad((x, drum_y, drum_w, drum_h), label, c1, c2, snd, key))

    # --- колокольчики (нижний ряд) ---
    bell_y = 375
    bell_h = 145
    bell_w = (WIDTH - 2 * margin - 7 * gap) // 8
    for i in range(8):
        x = margin + i * (bell_w + gap)
        hue = i / 8
        r, g, b = colorsys.hsv_to_rgb(hue, 0.70, 0.98)
        c1 = (int(r * 255), int(g * 255), int(b * 255))
        r2, g2, b2 = colorsys.hsv_to_rgb(hue, 0.90, 0.60)
        c2 = (int(r2 * 255), int(g2 * 255), int(b2 * 255))
        pads.append(Pad((x, bell_y, bell_w, bell_h),
                        NOTE_NAMES[i], c1, c2, bell_sounds[i], 'asdfghjk'[i]))


build_layout()

# Кнопка «Сюрприз»
SURPRISE_RECT = pygame.Rect(WIDTH // 2 - 130, HEIGHT - 95, 260, 66)

# ============================================================
#  ВИЗУАЛЬНЫЕ ЭФФЕКТЫ
# ============================================================

ripples = []      # [x, y, t0, color, max_radius]
floaters = []     # [x, y, t0, char, color]
flash_time = -9999
flash_color = (255, 255, 255)

NOTE_CHARS = ['♪', '♫', '♬', '♩', '♭']


def emit_effects(pad, mx=None, my=None):
    if mx is None:
        mx = pad.rect.centerx
        my = pad.rect.centery

    ripples.append([mx, my, pygame.time.get_ticks(), pad.c1,
                    max(pad.rect.width, pad.rect.height)])

    color = random.choice([
        (255, 220, 100), (255, 150, 200),
        (150, 220, 255), (200, 255, 150)
    ])
    floaters.append([mx, my, pygame.time.get_ticks(),
                     random.choice(NOTE_CHARS), color])

    global flash_time, flash_color
    flash_time = pygame.time.get_ticks()
    flash_color = pad.c1


def update_effects(now):
    for r in ripples[:]:
        if now - r[2] > 650:
            ripples.remove(r)
    for f in floaters[:]:
        if now - f[2] > 1100:
            floaters.remove(f)


def draw_effects(surface, now):
    # расходящиеся круги
    for x, y, t0, color, max_r in ripples:
        t = (now - t0) / 650
        radius = int(max_r * 1.3 * t)
        if radius < 1:
            continue
        alpha = int(200 * (1 - t))
        size = radius * 2
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        width = max(2, int(7 * (1 - t)))
        pygame.draw.circle(surf, (*color, alpha), (radius, radius), radius, width=width)
        surface.blit(surf, (x - radius, y - radius))

    # улетающие нотки
    for x, y, t0, ch, color in floaters:
        t = (now - t0) / 1100
        cur_y = y - 200 * t
        alpha = int(255 * (1 - t) ** 0.6)
        size = int(28 + 16 * t)
        fnt = load_font(size, bold=True)
        img = fnt.render(ch, True, color)
        img.set_alpha(alpha)
        surface.blit(img, (x - img.get_width() // 2, cur_y - img.get_height() // 2))

    # вспышка на весь экран
    if now - flash_time < 380:
        t = (now - flash_time) / 380
        alpha = int(70 * (1 - t))
        flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        flash.fill((*flash_color, alpha))
        surface.blit(flash, (0, 0))


# ============================================================
#  СЮРПРИЗ-МЕЛОДИЯ
# ============================================================

surprise = {'active': False, 'events': [], 'start': 0, 'played': set()}


def start_surprise():
    if surprise['active']:
        return
    surprise['active'] = True
    surprise['start'] = pygame.time.get_ticks() + 200
    surprise['played'] = set()

    events = []
    steps = 8
    beat = 280
    bell_indices = list(range(5, 13))
    for i in range(steps):
        t = i * beat
        events.append((t, random.choice(bell_indices)))
        if i % 4 == 0:
            events.append((t, random.choice([0, 1])))
        if i % 2 == 1 and random.random() < 0.5:
            events.append((t, 3))
    surprise['events'] = sorted(events)


def update_surprise(now):
    if not surprise['active']:
        return
    elapsed = now - surprise['start']
    for idx, (t, pi) in enumerate(surprise['events']):
        if idx in surprise['played']:
            continue
        if elapsed >= t:
            pad = pads[pi]
            pad.press()
            emit_effects(pad)
            surprise['played'].add(idx)
    if elapsed > 8 * 280 + 600:
        surprise['active'] = False


# ============================================================
#  ОБРАБОТКА ВВОДА
# ============================================================

def find_pad_at(mx, my):
    for p in pads:
        if p.rect.collidepoint(mx, my):
            return p
    return None


def find_pad_by_key(k):
    for p in pads:
        if p.key == k:
            return p
    return None


# ============================================================
#  ОТРИСОВКА СТАТИЧНЫХ ЭЛЕМЕНТОВ
# ============================================================

def draw_title(surface):
    title = font_title.render("♪  Музыкальные кнопки  ♪", True, (255, 240, 200))
    surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 22))

    hint = font_hint.render(
        "Нажимай на кнопки мышкой.  Клавиши:  1–5 — барабаны,  A–K — колокольчики,  ПРОБЕЛ — сюрприз",
        True, (200, 200, 220))
    surface.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 88))


def draw_section_labels(surface):
    lab1 = font_small.render("🥁  БАРАБАНЫ", True, (255, 220, 180))
    surface.blit(lab1, (34, 130))
    lab2 = font_small.render("🔔  КОЛОКОЛЬЧИКИ", True, (200, 230, 255))
    surface.blit(lab2, (34, 350))


def draw_surprise_button(surface):
    rect = SURPRISE_RECT
    mx, my = pygame.mouse.get_pos()
    hover = rect.collidepoint(mx, my)

    base = (255, 225, 90) if hover else (255, 200, 40)
    shadow = (170, 120, 0)

    pygame.draw.rect(surface, shadow, rect.move(0, 7), border_radius=30)
    pygame.draw.rect(surface, base, rect, border_radius=30)
    pygame.draw.rect(surface, (255, 255, 255), rect, width=3, border_radius=30)

    txt = font_label.render("★  СЮРПРИЗ  ★", True, (60, 30, 90))
    surface.blit(txt, (rect.centerx - txt.get_width() // 2,
                       rect.centery - txt.get_height() // 2))


# ============================================================
#  ГЛАВНЫЙ ЦИКЛ
# ============================================================

def main():
    running = True
    while running:
        now = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if SURPRISE_RECT.collidepoint(event.pos):
                    start_surprise()
                else:
                    pad = find_pad_at(*event.pos)
                    if pad:
                        pad.press()
                        emit_effects(pad, *event.pos)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    start_surprise()
                else:
                    ch = event.unicode.lower() if event.unicode else ''
                    pad = find_pad_by_key(ch)
                    if pad:
                        pad.press()
                        emit_effects(pad)

        update_surprise(now)
        update_effects(now)

        # ---- отрисовка ----
        screen.blit(bg_surface, (0, 0))
        draw_title(screen)
        draw_section_labels(screen)

        for p in pads:
            p.draw(screen)

        draw_surprise_button(screen)
        draw_effects(screen, now)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()