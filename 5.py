"""
🎬 Интерактивная сказка «Колобок» — HD-версия.

Возможности:
  • Профессиональная озвучка (pyttsx3) с подсветкой слов «как караоке».
  • Фоновая атмосферная музыка с приглушением во время речи диктора.
  • Реплики героев в речевых облачках при клике.
  • Плавные переходы между страницами (слайд).
  • Падающие частицы: искры, листья, светлячки — по странице.
  • Кнопка MUTE, прогресс страниц, подсказки-подсветки.

Запуск:  python tale_hd.py
Клавиши: ← → листать, 1-3 страница, R читать заново,
         ПРОБЕЛ пауза голоса, M выкл/вкл звук, ESC выход.
"""

import math
import random
import array
import sys
import os
import tempfile
import threading

import pygame

# ============================================================
#  ИНИЦИАЛИЗАЦИЯ
# ============================================================

pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
pygame.mixer.set_num_channels(64)

SR = 44100
WIDTH, HEIGHT = 1180, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Интерактивная сказка: Колобок")
clock = pygame.time.Clock()

MUSIC_CHANNEL = pygame.mixer.Channel(0)

# ============================================================
#  СИНТЕЗ ЗВУКОВ
# ============================================================

def to_sound(samples):
    arr = array.array('h', [int(max(-1.0, min(1.0, s)) * 32000) for s in samples])
    return pygame.mixer.Sound(buffer=arr.tobytes())


def make_ambient():
    dur = 4.0
    n = int(SR * dur)
    tones = [(261.75, 0.34), (329.75, 0.26), (392.00, 0.22),
             (523.50, 0.16), (659.50, 0.10)]
    out = [0.0] * n
    for f, a in tones:
        w = 2 * math.pi * f
        for i in range(n):
            t = i / SR
            trem = 0.75 + 0.25 * math.sin(2 * math.pi * t / dur)
            out[i] += math.sin(w * t) * a * trem
    w_shim = 2 * math.pi * 1047.0
    for i in range(n):
        t = i / SR
        out[i] += 0.05 * math.sin(w_shim * t) * \
                  (0.5 + 0.5 * math.sin(2 * math.pi * 0.5 * t))
    peak = max(abs(s) for s in out) or 1.0
    return to_sound([s / peak * 0.42 for s in out])


def make_tone(freq, dur, amp=0.5, decay=4.0,
              partials=((1, 1.0), (2, 0.4), (3, 0.15)), attack=0.008):
    n = int(SR * dur)
    a_samples = max(1, int(SR * attack))
    out = [0.0] * n
    for mult, p_amp in partials:
        w = 2 * math.pi * freq * mult
        for i in range(n):
            t = i / SR
            env = math.exp(-t * decay)
            if i < a_samples:
                env *= i / a_samples
            out[i] += math.sin(w * t) * p_amp * env
    peak = max(abs(s) for s in out) or 1.0
    return to_sound([s / peak * amp for s in out])


def make_melody(notes, step=0.16, amp=0.4):
    total = int(SR * step * len(notes)) + int(SR * 0.3)
    out = [0.0] * total
    for k, f in enumerate(notes):
        w = 2 * math.pi * f
        for i in range(int(SR * step)):
            t = i / SR
            env = math.exp(-t * 3.0)
            idx = k * int(SR * step) + i
            if idx < total:
                out[idx] += math.sin(w * t) * env * amp
                out[idx] += math.sin(2 * w * t) * env * amp * 0.25
    return to_sound(out)


def make_sad_note(freq=330):
    dur = 0.75
    n = int(SR * dur)
    out = []
    for i in range(n):
        t = i / SR
        f = freq * (1 - 0.12 * t / dur)
        env = math.exp(-t * 2.5)
        out.append(math.sin(2 * math.pi * f * t) * env * 0.45)
    return to_sound(out)


def make_puff():
    dur = 0.45
    n = int(SR * dur)
    out = []
    prev = 0.0
    for i in range(n):
        t = i / SR
        noise = random.random() * 2 - 1
        lp = noise * 0.35 + prev * 0.65
        prev = lp
        am = 0.5 + 0.5 * math.sin(2 * math.pi * 6 * t)
        env = math.exp(-t * 4.0) * am
        out.append(lp * env * 0.6)
    return to_sound(out)


def make_creak():
    dur = 0.55
    n = int(SR * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        f = 160 + 40 * math.sin(2 * math.pi * 4 * t) - 30 * t / dur
        phase += 2 * math.pi * f / SR
        env = math.exp(-t * 3.0)
        out.append(math.sin(phase) * env * 0.45)
    return to_sound(out)


def make_chime():
    dur = 0.9
    n = int(SR * dur)
    out = [0.0] * n
    for mult, amp, decay in [(1.0, 1.0, 2.5), (2.7, 0.4, 3.5), (5.3, 0.15, 5.0)]:
        w = 2 * math.pi * 880 * mult
        for i in range(n):
            t = i / SR
            out[i] += math.sin(w * t) * amp * math.exp(-t * decay)
    peak = max(abs(s) for s in out) or 1.0
    return to_sound([s / peak * 0.4 for s in out])


def make_roll():
    dur = 1.1
    n = int(SR * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        f = 300 + 500 * (t / dur)
        phase += 2 * math.pi * f / SR
        env = math.sin(math.pi * t / dur) ** 1.5
        out.append(math.sin(phase) * env * 0.35)
    return to_sound(out)


def make_jump():
    dur = 0.22
    n = int(SR * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        f = 500 + 900 * (t / dur)
        phase += 2 * math.pi * f / SR
        env = math.exp(-t * 9.0)
        out.append(math.sin(phase) * env * 0.45)
    return to_sound(out)


def make_rustle():
    dur = 0.7
    n = int(SR * dur)
    out = []
    prev = 0.0
    for i in range(n):
        t = i / SR
        noise = random.random() * 2 - 1
        hp = noise - prev
        prev = noise
        env = math.exp(-t * 3.5) * (0.6 + 0.4 * math.sin(2 * math.pi * 8 * t))
        out.append(hp * env * 0.18)
    return to_sound(out)


def make_growl():
    dur = 0.9
    n = int(SR * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        f = 90 + 15 * math.sin(2 * math.pi * 7 * t)
        phase += 2 * math.pi * f / SR
        mod = 0.6 + 0.4 * math.sin(2 * math.pi * 14 * t)
        env = min(1.0, t * 6) * math.exp(-max(0, t - 0.4) * 4)
        out.append(math.sin(phase) * env * mod * 0.55)
    return to_sound(out)


def make_bear():
    dur = 1.0
    n = int(SR * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        f = 60 + 8 * math.sin(2 * math.pi * 4 * t)
        phase += 2 * math.pi * f / SR
        env = min(1.0, t * 5) * math.exp(-max(0, t - 0.5) * 3)
        out.append(math.sin(phase) * env * 0.65)
        out.append(math.sin(2 * phase) * env * 0.2)
    return to_sound(out)


def make_yip():
    dur = 0.32
    n = int(SR * dur)
    out = [0.0] * n
    for chunk in range(2):
        start = int(chunk * n / 2.2)
        chunk_n = int(n / 3)
        phase = 0.0
        for i in range(chunk_n):
            t = i / SR
            f = max(200, 600 - 200 * (t / 0.12))
            phase += 2 * math.pi * f / SR
            env = math.exp(-t * 18)
            idx = start + i
            if idx < n:
                out[idx] += math.sin(phase) * env * 0.5
                out[idx] += (random.random() * 2 - 1) * env * 0.12
    return to_sound(out)


def make_crunch():
    dur = 0.35
    n = int(SR * dur)
    out = []
    prev = 0.0
    for i in range(n):
        t = i / SR
        noise = random.random() * 2 - 1
        hp = noise - prev * 0.5
        prev = noise
        env = math.exp(-t * 12)
        out.append(hp * env * 0.55)
    return to_sound(out)


def make_whoosh():
    dur = 0.35
    n = int(SR * dur)
    out = []
    prev = 0.0
    for i in range(n):
        t = i / SR
        noise = random.random() * 2 - 1
        hp = noise - prev * 0.85
        prev = noise
        env = math.sin(math.pi * t / dur) ** 2
        out.append(hp * env * 0.22)
    return to_sound(out)


def make_pop():
    dur = 0.10
    n = int(SR * dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        f = 900 - 500 * (t / dur)
        phase += 2 * math.pi * f / SR
        env = math.exp(-t * 30)
        out.append(math.sin(phase) * env * 0.4)
    return to_sound(out)


print("Синтез звуков, пару секунд...")
SFX = {
    'kolobok_melody': make_melody([523.25, 659.25, 783.99, 1046.50], 0.16),
    'sad_note':       make_sad_note(330),
    'puff':           make_puff(),
    'creak':          make_creak(),
    'chime':          make_chime(),
    'roll':           make_roll(),
    'jump':           make_jump(),
    'rustle':         make_rustle(),
    'growl':          make_growl(),
    'bear':           make_bear(),
    'yip':            make_yip(),
    'crunch':         make_crunch(),
    'whoosh':         make_whoosh(),
    'pop':            make_pop(),
}
AMBIENT = make_ambient()
print("Готово.")

# ============================================================
#  ОЗВУЧКА ТЕКСТА
# ============================================================

voice_cache = {}
voice_ready = threading.Event()
voice_status = "Подготовка голоса..."
voice_channel = None
narration_start_ms = 0
narration_duration_ms = 0
narration_word_timings = []


def compute_word_timings(text, total_ms):
    words = text.split()
    weights = [max(1, len(w)) for w in words]
    tot = sum(weights)
    timings = []
    cum = 0
    for w, wt in zip(words, weights):
        start = cum / tot * total_ms
        end = (cum + wt) / tot * total_ms
        timings.append((w, start, end))
        cum += wt
    return timings


def generate_voice(pages):
    global voice_status
    try:
        import pyttsx3
        tmpdir = tempfile.gettempdir()
        for i, page in enumerate(pages):
            path = os.path.join(
                tmpdir,
                f"tale_hd_{i}_{abs(hash(page['text'])) % 100000}.wav")
            if not os.path.exists(path) or os.path.getsize(path) < 1000:
                engine = pyttsx3.init()
                try:
                    for v in engine.getProperty('voices'):
                        vid = ((v.id or "") + " " +
                               (getattr(v, "name", "") or "")).lower()
                        if any(tag in vid for tag in
                               ("ru", "russian", "irina", "svetlana",
                                "pavel", "milena")):
                            engine.setProperty('voice', v.id)
                            break
                except Exception:
                    pass
                engine.setProperty('rate', 148)
                engine.setProperty('volume', 1.0)
                engine.save_to_file(page['text'], path)
                engine.runAndWait()
                try:
                    engine.stop()
                except Exception:
                    pass
            if os.path.exists(path) and os.path.getsize(path) > 1000:
                snd = pygame.mixer.Sound(path)
                voice_cache[i] = snd
                ms = int(snd.get_length() * 1000)
                voice_cache[f'{i}_ms'] = ms
                voice_cache[f'{i}_words'] = compute_word_timings(
                    page['text'], ms)
        voice_status = "Готово"
    except Exception as e:
        print("TTS не сработал:", e)
        voice_status = "Без голоса"
    voice_ready.set()


def play_voice(page_idx):
    global voice_channel, narration_start_ms, narration_duration_ms
    global narration_word_timings
    if voice_channel:
        voice_channel.stop()
    snd = voice_cache.get(page_idx)
    if not snd:
        return
    if not SOUND_ENABLED:
        return
    voice_channel = snd.play()
    narration_start_ms = pygame.time.get_ticks()
    narration_duration_ms = voice_cache.get(f'{page_idx}_ms', 0)
    narration_word_timings = voice_cache.get(f'{page_idx}_words', [])

# ============================================================
#  ФЛАГ ЗВУКА
# ============================================================

SOUND_ENABLED = True


def set_sound_enabled(enabled):
    global SOUND_ENABLED
    SOUND_ENABLED = enabled
    if enabled:
        if not MUSIC_CHANNEL.get_busy():
            MUSIC_CHANNEL.play(AMBIENT, loops=-1)
        MUSIC_CHANNEL.set_volume(0.45)
    else:
        MUSIC_CHANNEL.stop()
        if voice_channel:
            voice_channel.stop()

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


font_title = get_font(36, bold=True)
font_sub   = get_font(17)
font_body  = get_font(25)
font_btn   = get_font(20, bold=True)
font_small = get_font(15, bold=True)
font_label = get_font(18, bold=True)
font_bub   = get_font(20, bold=True)

# ============================================================
#  РАЗМЕТКА
# ============================================================

TOP_H = 74
ILLUST_RECT = pygame.Rect(0, TOP_H, WIDTH, 545)
TEXT_RECT = pygame.Rect(0, TOP_H + 545, WIDTH, HEIGHT - TOP_H - 545)

BTN_PREV = pygame.Rect(360, 16, 130, 42)
BTN_READ = pygame.Rect(WIDTH // 2 - 100, 14, 200, 46)
BTN_NEXT = pygame.Rect(WIDTH // 2 + 110, 16, 130, 42)
BTN_MUTE = pygame.Rect(WIDTH - 62, 18, 44, 40)

# ============================================================
#  РИСОВАНИЕ ФИГУР
# ============================================================

def draw_cloud(s, x, y, size, color=(252, 250, 255)):
    pygame.draw.circle(s, color, (x, y), size)
    pygame.draw.circle(s, color, (x + int(size * 0.9), y - 6), int(size * 0.75))
    pygame.draw.circle(s, color, (x + int(size * 1.8), y), int(size * 0.85))
    pygame.draw.circle(s, color, (x + int(size * 0.9), y + size // 2),
                       int(size * 0.8))


def draw_sun(s, x, y, r, t):
    for i in range(12):
        a = i * math.pi / 6 + t * 0.3
        x2 = x + math.cos(a) * (r + 14)
        y2 = y + math.sin(a) * (r + 14)
        pygame.draw.line(s, (255, 220, 90), (x, y), (x2, y2), 4)
    pygame.draw.circle(s, (255, 210, 80), (x, y), r)
    pygame.draw.circle(s, (255, 240, 130), (x, y), r, 4)


def draw_tree(s, x, y, scale=1.0, color_trunk=(120, 70, 40),
              color_crown=(80, 170, 80)):
    tw = int(24 * scale)
    th = int(90 * scale)
    pygame.draw.rect(s, color_trunk, (x - tw // 2, y - th, tw, th))
    pygame.draw.rect(s, (60, 30, 20), (x - tw // 2, y - th, tw, th), 3)
    r = int(60 * scale)
    pygame.draw.circle(s, color_crown, (x, y - th - int(20 * scale)), r)
    pygame.draw.circle(s, color_crown,
                       (x - int(40 * scale), y - th), int(r * 0.8))
    pygame.draw.circle(s, color_crown,
                       (x + int(40 * scale), y - th), int(r * 0.8))
    pygame.draw.circle(s, (50, 130, 60),
                       (x, y - th - int(20 * scale)), r, 3)


def draw_bush(s, x, y, scale=1.0, color=(90, 180, 100)):
    pygame.draw.circle(s, color, (x, y), int(30 * scale))
    pygame.draw.circle(s, color, (x - int(22 * scale), y + 8), int(22 * scale))
    pygame.draw.circle(s, color, (x + int(22 * scale), y + 8), int(22 * scale))
    pygame.draw.circle(s, (55, 140, 70), (x, y), int(30 * scale), 3)


def draw_ground(s, y):
    pygame.draw.rect(s, (130, 200, 100), (0, y, WIDTH, HEIGHT - y))
    for i in range(0, WIDTH, 60):
        pygame.draw.line(s, (90, 170, 80), (i, y + 8), (i + 14, y + 4), 3)
        pygame.draw.line(s, (90, 170, 80), (i + 30, y + 20), (i + 46, y + 16), 3)


def draw_kolobok(s, x, y, r, t=0.0, sad=False):
    bob = math.sin(t * 2.4) * 3
    y = int(y + bob)
    pygame.draw.circle(s, (240, 190, 60), (x, y + 4), r)
    pygame.draw.circle(s, (255, 220, 90), (x, y), r)
    pygame.draw.circle(s, (200, 150, 40), (x, y), r, 4)
    pygame.draw.circle(s, (255, 170, 140),
                       (x - int(r * 0.55), y + int(r * 0.15)), int(r * 0.18))
    pygame.draw.circle(s, (255, 170, 140),
                       (x + int(r * 0.55), y + int(r * 0.15)), int(r * 0.18))
    pygame.draw.circle(s, (255, 240, 180),
                       (x - int(r * 0.35), y - int(r * 0.4)), int(r * 0.16))
    blink = (math.sin(t * 1.7) > 0.97)
    ex, ey = int(r * 0.32), int(r * 0.12)
    for sx in (-1, 1):
        if blink:
            pygame.draw.line(s, (40, 30, 20),
                             (x + sx * ex - 6, y - ey),
                             (x + sx * ex + 6, y - ey), 3)
        else:
            pygame.draw.circle(s, (255, 255, 255),
                               (x + sx * ex, y - ey), int(r * 0.18))
            pygame.draw.circle(s, (40, 30, 20),
                               (x + sx * ex, y - ey), int(r * 0.10))
    if sad:
        pts = [(x - int(r * 0.3), y + int(r * 0.45)),
               (x, y + int(r * 0.35)),
               (x + int(r * 0.3), y + int(r * 0.45))]
    else:
        pts = [(x - int(r * 0.3), y + int(r * 0.3)),
               (x, y + int(r * 0.5)),
               (x + int(r * 0.3), y + int(r * 0.3))]
    pygame.draw.lines(s, (120, 60, 40), False, pts, 4)


def draw_babushka(s, x, y, t=0.0):
    sway = math.sin(t * 1.2) * 2
    x = int(x + sway)
    pygame.draw.polygon(s, (170, 90, 160),
                        [(x - 55, y + 130), (x + 55, y + 130),
                         (x + 35, y + 20), (x - 35, y + 20)])
    pygame.draw.polygon(s, (110, 60, 110),
                        [(x - 55, y + 130), (x + 55, y + 130),
                         (x + 35, y + 20), (x - 35, y + 20)], 3)
    pygame.draw.polygon(s, (255, 230, 200),
                        [(x - 30, y + 130), (x + 30, y + 130),
                         (x + 22, y + 60), (x - 22, y + 60)])
    pygame.draw.line(s, (240, 200, 170),
                     (x - 35, y + 40), (x - 65, y + 90), 14)
    pygame.draw.line(s, (240, 200, 170),
                     (x + 35, y + 40), (x + 65, y + 90), 14)
    pygame.draw.circle(s, (245, 205, 175), (x, y), 42)
    pygame.draw.circle(s, (180, 140, 120), (x, y), 42, 3)
    pygame.draw.polygon(s, (220, 60, 70),
                        [(x - 42, y - 5), (x + 42, y - 5),
                         (x + 30, y - 45), (x - 30, y - 45)])
    pygame.draw.circle(s, (240, 80, 90), (x, y - 30), 22)
    pygame.draw.circle(s, (50, 30, 20), (x - 13, y + 4), 4)
    pygame.draw.circle(s, (50, 30, 20), (x + 13, y + 4), 4)
    pygame.draw.arc(s, (150, 50, 50),
                    pygame.Rect(x - 14, y + 12, 28, 14), 3.6, 5.9, 3)


def draw_starik(s, x, y, t=0.0):
    sway = math.sin(t * 1.1 + 1) * 2
    x = int(x + sway)
    pygame.draw.rect(s, (95, 130, 185), (x - 42, y + 20, 84, 110),
                     border_radius=14)
    pygame.draw.rect(s, (55, 80, 130), (x - 42, y + 20, 84, 110), 3,
                     border_radius=14)
    pygame.draw.line(s, (245, 205, 175),
                     (x - 42, y + 50), (x - 68, y + 95), 14)
    pygame.draw.line(s, (245, 205, 175),
                     (x + 42, y + 50), (x + 68, y + 95), 14)
    pygame.draw.circle(s, (245, 205, 175), (x, y), 40)
    pygame.draw.circle(s, (180, 140, 120), (x, y), 40, 3)
    pygame.draw.ellipse(s, (230, 230, 235), pygame.Rect(x - 34, y + 5, 68, 60))
    pygame.draw.ellipse(s, (180, 180, 195),
                        pygame.Rect(x - 34, y + 5, 68, 60), 3)
    pygame.draw.polygon(s, (120, 60, 30),
                        [(x - 42, y - 22), (x + 42, y - 22),
                         (x + 20, y - 62), (x - 20, y - 62)])
    pygame.draw.polygon(s, (70, 35, 15),
                        [(x - 42, y - 22), (x + 42, y - 22),
                         (x + 20, y - 62), (x - 20, y - 62)], 3)
    pygame.draw.circle(s, (50, 30, 20), (x - 13, y - 4), 4)
    pygame.draw.circle(s, (50, 30, 20), (x + 13, y - 4), 4)
    pygame.draw.circle(s, (60, 40, 30), (x - 13, y - 4), 9, 2)
    pygame.draw.circle(s, (60, 40, 30), (x + 13, y - 4), 9, 2)
    pygame.draw.line(s, (60, 40, 30), (x - 4, y - 4), (x + 4, y - 4), 2)


def draw_stove(s, x, y, t=0.0):
    pygame.draw.rect(s, (225, 210, 190), (x - 80, y, 160, 150),
                     border_radius=8)
    pygame.draw.rect(s, (150, 130, 110), (x - 80, y, 160, 150), 3,
                     border_radius=8)
    pygame.draw.rect(s, (200, 60, 50), (x - 30, y - 80, 60, 80))
    pygame.draw.rect(s, (130, 30, 25), (x - 30, y - 80, 60, 80), 3)
    for k in range(4):
        dy = y - 90 - k * 18 + int(6 * math.sin(t * 2 + k))
        dr = 10 + k * 4
        alpha = 180 - k * 30
        sm = pygame.Surface((dr * 2, dr * 2), pygame.SRCALPHA)
        pygame.draw.circle(sm, (200, 200, 200, alpha), (dr, dr), dr)
        s.blit(sm, (x - dr, dy - dr))
    pygame.draw.rect(s, (60, 30, 20), (x - 42, y + 40, 84, 70),
                     border_radius=6)
    for i in range(5):
        fx = x - 30 + i * 14
        fy = y + 95 - (10 + 6 * (i % 2))
        pygame.draw.polygon(s, (255, 160 + 20 * i, 60),
                            [(fx - 8, y + 100), (fx + 8, y + 100), (fx, fy)])
        pygame.draw.polygon(s, (255, 90, 30),
                            [(fx - 5, y + 98), (fx + 5, y + 98),
                             (fx, fy + 6)], 2)


def draw_house(s, x, y, w=260, h=170):
    pygame.draw.rect(s, (215, 170, 120), (x, y, w, h))
    pygame.draw.rect(s, (140, 100, 60), (x, y, w, h), 4)
    for i in range(1, 6):
        yy = y + i * (h // 6)
        pygame.draw.line(s, (180, 140, 90), (x, yy), (x + w, yy), 2)
    pygame.draw.polygon(s, (150, 80, 60),
                        [(x - 18, y), (x + w + 18, y), (x + w // 2, y - 80)])
    pygame.draw.polygon(s, (95, 45, 35),
                        [(x - 18, y), (x + w + 18, y), (x + w // 2, y - 80)], 4)
    wx, wy = x + w // 2 - 45, y + 50
    pygame.draw.rect(s, (230, 245, 255), (wx, wy, 90, 70))
    pygame.draw.rect(s, (90, 60, 40), (wx, wy, 90, 70), 4)
    pygame.draw.line(s, (90, 60, 40), (wx + 45, wy), (wx + 45, wy + 70), 3)
    pygame.draw.line(s, (90, 60, 40), (wx, wy + 35), (wx + 90, wy + 35), 3)


def draw_zayats(s, x, y, t=0.0):
    bob = math.sin(t * 3.0) * 4
    y = int(y + bob)
    pygame.draw.ellipse(s, (200, 200, 210), pygame.Rect(x - 42, y, 84, 70))
    pygame.draw.ellipse(s, (120, 120, 140),
                        pygame.Rect(x - 42, y, 84, 70), 3)
    pygame.draw.circle(s, (240, 240, 245), (x - 42, y + 50), 10)
    pygame.draw.circle(s, (150, 150, 170), (x - 42, y + 50), 10, 2)
    pygame.draw.circle(s, (220, 220, 230), (x + 30, y + 10), 30)
    pygame.draw.circle(s, (140, 140, 160), (x + 30, y + 10), 30, 3)
    for sx in (-1, 1):
        ex = x + 30 + sx * 12
        pts = [(ex - 8, y - 6), (ex + 8, y - 6),
               (ex + sx * 4, y - 70), (ex - sx * 2, y - 68)]
        pygame.draw.polygon(s, (220, 220, 230), pts)
        pygame.draw.polygon(s, (140, 140, 160), pts, 3)
        pygame.draw.polygon(s, (255, 180, 190),
                            [(ex - 3, y - 12), (ex + 3, y - 12),
                             (ex + sx * 2, y - 58), (ex - sx * 1, y - 56)])
    pygame.draw.circle(s, (40, 30, 20), (x + 22, y + 4), 4)
    pygame.draw.circle(s, (40, 30, 20), (x + 40, y + 4), 4)
    pygame.draw.circle(s, (255, 130, 140), (x + 46, y + 20), 4)
    pygame.draw.line(s, (60, 60, 70), (x + 50, y + 22), (x + 66, y + 18), 2)
    pygame.draw.line(s, (60, 60, 70), (x + 50, y + 24), (x + 66, y + 28), 2)


def draw_wolf(s, x, y, t=0.0):
    bob = math.sin(t * 1.5) * 3
    y = int(y + bob)
    pygame.draw.ellipse(s, (130, 130, 145), pygame.Rect(x - 55, y, 110, 80))
    pygame.draw.ellipse(s, (70, 70, 85),
                        pygame.Rect(x - 55, y, 110, 80), 3)
    pygame.draw.ellipse(s, (110, 110, 125), pygame.Rect(x - 90, y + 35, 50, 22))
    pygame.draw.ellipse(s, (70, 70, 85),
                        pygame.Rect(x - 90, y + 35, 50, 22), 3)
    pygame.draw.circle(s, (150, 150, 165), (x + 35, y + 5), 34)
    pygame.draw.circle(s, (70, 70, 85), (x + 35, y + 5), 34, 3)
    pygame.draw.polygon(s, (150, 150, 165),
                        [(x + 10, y - 22), (x + 22, y - 55), (x + 32, y - 25)])
    pygame.draw.polygon(s, (70, 70, 85),
                        [(x + 10, y - 22), (x + 22, y - 55), (x + 32, y - 25)], 3)
    pygame.draw.polygon(s, (150, 150, 165),
                        [(x + 40, y - 22), (x + 52, y - 55), (x + 62, y - 25)])
    pygame.draw.polygon(s, (70, 70, 85),
                        [(x + 40, y - 22), (x + 52, y - 55), (x + 62, y - 25)], 3)
    pygame.draw.circle(s, (240, 230, 120), (x + 24, y - 2), 6)
    pygame.draw.circle(s, (240, 230, 120), (x + 48, y - 2), 6)
    pygame.draw.circle(s, (20, 20, 20), (x + 24, y - 2), 3)
    pygame.draw.circle(s, (20, 20, 20), (x + 48, y - 2), 3)
    pygame.draw.ellipse(s, (60, 20, 20), (x + 25, y + 18, 34, 14))
    pygame.draw.polygon(s, (255, 255, 255),
                        [(x + 28, y + 20), (x + 34, y + 20), (x + 31, y + 28)])
    pygame.draw.polygon(s, (255, 255, 255),
                        [(x + 44, y + 20), (x + 50, y + 20), (x + 47, y + 28)])


def draw_bear(s, x, y, t=0.0):
    bob = math.sin(t * 1.2) * 3
    y = int(y + bob)
    pygame.draw.ellipse(s, (150, 100, 60),
                        pygame.Rect(x - 70, y - 10, 140, 110))
    pygame.draw.ellipse(s, (85, 50, 25),
                        pygame.Rect(x - 70, y - 10, 140, 110), 4)
    pygame.draw.circle(s, (170, 115, 70), (x + 35, y - 25), 42)
    pygame.draw.circle(s, (85, 50, 25), (x + 35, y - 25), 42, 3)
    pygame.draw.circle(s, (170, 115, 70), (x + 6, y - 55), 16)
    pygame.draw.circle(s, (85, 50, 25), (x + 6, y - 55), 16, 3)
    pygame.draw.circle(s, (170, 115, 70), (x + 64, y - 55), 16)
    pygame.draw.circle(s, (85, 50, 25), (x + 64, y - 55), 16, 3)
    pygame.draw.ellipse(s, (220, 180, 140), (x + 12, y - 14, 46, 34))
    pygame.draw.ellipse(s, (85, 50, 25), (x + 12, y - 14, 46, 34), 2)
    pygame.draw.circle(s, (20, 20, 20), (x + 22, y - 26), 4)
    pygame.draw.circle(s, (20, 20, 20), (x + 48, y - 26), 4)
    pygame.draw.circle(s, (30, 15, 10), (x + 35, y - 6), 5)
    pygame.draw.arc(s, (60, 30, 15),
                    pygame.Rect(x + 24, y + 4, 22, 12), 3.5, 6.0, 3)


def draw_fox(s, x, y, t=0.0):
    bob = math.sin(t * 2.0) * 3
    y = int(y + bob)
    pygame.draw.ellipse(s, (240, 130, 50), pygame.Rect(x - 55, y, 110, 70))
    pygame.draw.ellipse(s, (170, 70, 20),
                        pygame.Rect(x - 55, y, 110, 70), 3)
    pygame.draw.ellipse(s, (240, 130, 50), pygame.Rect(x - 100, y + 5, 60, 40))
    pygame.draw.ellipse(s, (255, 250, 240),
                        pygame.Rect(x - 100, y + 5, 26, 40))
    pygame.draw.ellipse(s, (170, 70, 20),
                        pygame.Rect(x - 100, y + 5, 60, 40), 3)
    pygame.draw.circle(s, (250, 145, 60), (x + 35, y + 5), 32)
    pygame.draw.circle(s, (170, 70, 20), (x + 35, y + 5), 32, 3)
    pygame.draw.polygon(s, (250, 145, 60),
                        [(x + 12, y - 20), (x + 22, y - 55), (x + 34, y - 22)])
    pygame.draw.polygon(s, (170, 70, 20),
                        [(x + 12, y - 20), (x + 22, y - 55), (x + 34, y - 22)], 3)
    pygame.draw.polygon(s, (250, 145, 60),
                        [(x + 38, y - 20), (x + 50, y - 55), (x + 62, y - 22)])
    pygame.draw.polygon(s, (170, 70, 20),
                        [(x + 38, y - 20), (x + 50, y - 55), (x + 62, y - 22)], 3)
    pygame.draw.circle(s, (255, 255, 255), (x + 24, y), 7)
    pygame.draw.circle(s, (255, 255, 255), (x + 46, y), 7)
    pygame.draw.circle(s, (20, 20, 20), (x + 24, y), 3)
    pygame.draw.circle(s, (20, 20, 20), (x + 46, y), 3)
    pygame.draw.circle(s, (30, 20, 20), (x + 60, y + 10), 5)
    pygame.draw.arc(s, (30, 20, 20),
                    pygame.Rect(x + 42, y + 10, 22, 12), 3.3, 6.0, 2)

# ============================================================
#  СТРАНИЦЫ
# ============================================================

def draw_page_1(surface, t):
    for y in range(ILLUST_RECT.top, ILLUST_RECT.top + 380, 4):
        k = (y - ILLUST_RECT.top) / 380
        c = (int(140 + 60 * k), int(200 + 40 * k), int(245 - 20 * k))
        pygame.draw.rect(surface, c, (0, y, WIDTH, 4))
    draw_sun(surface, WIDTH - 130, ILLUST_RECT.top + 90, 46, t)
    draw_cloud(surface, 120 + int(20 * math.sin(t * 0.4)),
               ILLUST_RECT.top + 80, 34)
    draw_cloud(surface, 420 + int(30 * math.sin(t * 0.5 + 1)),
               ILLUST_RECT.top + 60, 28)
    draw_cloud(surface, 720 + int(25 * math.sin(t * 0.45 + 2)),
               ILLUST_RECT.top + 100, 32)
    gy = ILLUST_RECT.top + 380
    draw_ground(surface, gy)
    draw_house(surface, WIDTH // 2 - 140, gy - 170, 280, 170)
    draw_stove(surface, 130, gy - 150, t)
    draw_starik(surface, WIDTH - 230, gy - 90, t)
    draw_babushka(surface, 300, gy - 130, t)
    kx = WIDTH // 2 + 5
    ky = gy - 105
    draw_kolobok(surface, kx, ky, 28, t)
    return {
        'kolobok': (kx - 32, ky - 32, 64, 64),
        'babushka': (300 - 70, gy - 130 - 55, 140, 210),
        'starik': (WIDTH - 230 - 75, gy - 90 - 55, 150, 210),
        'stove': (130 - 85, gy - 150 - 90, 170, 250),
        'okoshko': (WIDTH // 2 - 45, gy - 170 + 50, 90, 70),
    }


def draw_page_2(surface, t):
    for y in range(ILLUST_RECT.top, ILLUST_RECT.top + 360, 4):
        k = (y - ILLUST_RECT.top) / 360
        c = (int(150 + 50 * k), int(205 + 35 * k), int(245 - 25 * k))
        pygame.draw.rect(surface, c, (0, y, WIDTH, 4))
    draw_sun(surface, 140, ILLUST_RECT.top + 90, 46, t)
    draw_cloud(surface, WIDTH - 220 + int(20 * math.sin(t * 0.5)),
               ILLUST_RECT.top + 70, 30)
    draw_cloud(surface, WIDTH - 480 + int(30 * math.sin(t * 0.4 + 1)),
               ILLUST_RECT.top + 110, 26)
    draw_tree(surface, 60, ILLUST_RECT.top + 360, 0.9)
    draw_tree(surface, 180, ILLUST_RECT.top + 360, 0.7,
              color_crown=(110, 190, 110))
    draw_tree(surface, WIDTH - 90, ILLUST_RECT.top + 360, 1.0)
    draw_tree(surface, WIDTH - 200, ILLUST_RECT.top + 360, 0.75,
              color_crown=(90, 180, 90))
    gy = ILLUST_RECT.top + 360
    draw_ground(surface, gy)
    draw_bush(surface, 260, gy + 90, 0.9)
    draw_bush(surface, WIDTH - 300, gy + 110, 1.0)
    for i in range(0, WIDTH, 8):
        y = gy + 120 + int(30 * math.sin(i / 130))
        pygame.draw.rect(surface, (215, 185, 130), (i, y - 45, 10, 90))
        pygame.draw.rect(surface, (185, 155, 105), (i, y - 45, 10, 90), 1)
    kx = 220 + int(40 * math.sin(t * 2.0))
    ky = gy + 90 + int(8 * math.sin(t * 4.0))
    draw_kolobok(surface, kx, ky, 32, t)
    zx = WIDTH - 320
    zy = gy + 60
    draw_zayats(surface, zx, zy, t)
    return {
        'kolobok': (kx - 38, ky - 38, 76, 76),
        'zayats': (zx - 55, zy - 75, 130, 160),
        'tree1': (60 - 70, gy - 180, 140, 200),
        'tree2': (WIDTH - 90 - 70, gy - 200, 140, 220),
    }


def draw_page_3(surface, t):
    for y in range(ILLUST_RECT.top, ILLUST_RECT.top + 360, 4):
        k = (y - ILLUST_RECT.top) / 360
        c = (int(120 + 40 * k), int(170 + 40 * k), int(230 - 20 * k))
        pygame.draw.rect(surface, c, (0, y, WIDTH, 4))
    draw_sun(surface, WIDTH - 150, ILLUST_RECT.top + 100, 42, t)
    draw_cloud(surface, 200, ILLUST_RECT.top + 80, 30)
    draw_cloud(surface, 560, ILLUST_RECT.top + 120, 26)
    for x, s in [(50, 0.9), (140, 0.75), (WIDTH - 100, 1.0),
                 (WIDTH - 200, 0.8)]:
        draw_tree(surface, x, ILLUST_RECT.top + 360, s,
                  color_crown=(70, 150, 70))
    gy = ILLUST_RECT.top + 360
    draw_ground(surface, gy)
    draw_bush(surface, 100, gy + 100, 1.0, color=(70, 150, 80))
    draw_bush(surface, WIDTH - 120, gy + 110, 0.9, color=(70, 150, 80))
    draw_wolf(surface, 210, gy + 80, t)
    draw_bear(surface, 520, gy + 40, t)
    draw_fox(surface, WIDTH - 260, gy + 90, t)
    kx = 360
    ky = gy + 130
    draw_kolobok(surface, kx, ky, 28, t, sad=True)
    return {
        'wolf': (210 - 60, gy + 80 - 60, 130, 130),
        'bear': (520 - 80, gy + 40 - 65, 180, 180),
        'fox': (WIDTH - 260 - 60, gy + 90 - 60, 140, 140),
        'kolobok': (kx - 34, ky - 34, 68, 68),
    }


PAGES = [
    {
        'text': ("Жили-были старик со старухой. Вот и говорит старик старухе: "
                 "— Испеки-ка ты, бабушка, Колобка. По амбару помела, "
                 "по сусекам поскребла — и испекла Колобка румяного. "
                 "Положила его на окошко студить."),
        'draw': draw_page_1,
        'particle': 'spark',
    },
    {
        'text': ("Полежал Колобок, полежал — да и покатился: с окошка на лавку, "
                 "с лавки на пол, по полу — да к дверям, через порог — "
                 "и на улицу. Катится по дорожке, а навстречу ему Заяц: "
                 "— Колобок, Колобок! Я тебя съем!"),
        'draw': draw_page_2,
        'particle': 'leaf',
    },
    {
        'text': ("Покатился Колобок дальше. Навстречу ему серый Волк, "
                 "потом — косолапый Медведь. А потом встретил Колобок "
                 "хитрую Лису. Лиса говорит: «Сядь ко мне на носик, "
                 "да пропой ещё разок!» — ам! — и съела Колобка."),
        'draw': draw_page_3,
        'particle': 'firefly',
    },
]

# ============================================================
#  РЕПЛИКИ И ЗВУКИ ОБЪЕКТОВ
# ============================================================

HOTSPOT_SOUNDS = {
    ('page0', 'kolobok'):  ('kolobok_melody', (255, 230, 120), 'Колобок',
                            "Я румяный Колобок!"),
    ('page0', 'babushka'): ('puff',           (255, 180, 200), 'Бабушка',
                            "Испекла я Колобка..."),
    ('page0', 'starik'):   ('creak',          (180, 200, 255), 'Дедушка',
                            "Ох, испеки, бабушка!"),
    ('page0', 'stove'):    ('puff',           (255, 160, 100), 'Печка',
                            "Фыр-фыр-фыр!"),
    ('page0', 'okoshko'):  ('chime',          (200, 230, 255), 'Окошко',
                            "Дзынь-дзынь!"),
    ('page1', 'kolobok'):  ('roll',           (255, 230, 120), 'Катится!',
                            "Катится, катится!"),
    ('page1', 'zayats'):   ('jump',           (200, 220, 255), 'Зайчик',
                            "Колобок, я тебя съем!"),
    ('page1', 'tree1'):    ('rustle',         (160, 230, 160), 'Ш-ш-ш',
                            "Ш-ш-ш..."),
    ('page1', 'tree2'):    ('rustle',         (160, 230, 160), 'Ш-ш-ш',
                            "Ш-ш-ш..."),
    ('page2', 'wolf'):     ('growl',          (200, 200, 220), 'Волк',
                            "Колобок, я тебя съем!"),
    ('page2', 'bear'):     ('bear',           (200, 160, 120), 'Медведь',
                            "Колобок, я тебя съем!"),
    ('page2', 'fox'):      ('yip',            (255, 180, 120), 'Лиса',
                            "Сядь ко мне на носик!"),
    ('page2', 'kolobok'):  ('sad_note',       (255, 200, 120), 'Ам...',
                            "Ой, не надо!"),
}

# ============================================================
#  СОСТОЯНИЕ
# ============================================================

current_page = 0
prev_page = None
transition_t0 = 0
TRANSITION_MS = 420

effects = []
bubbles = []
particles = []
particle_pool_t0 = 0
narration_auto_played = set()

# ============================================================
#  ВСПОМОГАТЕЛЬНОЕ
# ============================================================

def spawn_effect(x, y, color, label=None, char=None):
    effects.append([x, y, pygame.time.get_ticks(), color, label, char])


def spawn_bubble(x, y, text):
    bubbles.append([x, y, pygame.time.get_ticks(), text])


def find_hotspot(mx, my, hotspots):
    if not hotspots:
        return None
    for key, rect in reversed(list(hotspots.items())):
        if pygame.Rect(rect).collidepoint(mx, my):
            return key
    return None


def particle_color(kind):
    if kind == 'spark':
        return random.choice([(255, 230, 140), (255, 200, 100), (255, 250, 200)])
    if kind == 'leaf':
        return random.choice([(150, 220, 130), (110, 190, 100),
                              (180, 230, 150), (200, 240, 120)])
    return random.choice([(255, 250, 160), (200, 255, 160), (255, 220, 130)])


def spawn_particle(kind):
    x = random.randint(0, WIDTH)
    if kind == 'spark':
        y = random.randint(ILLUST_RECT.top, ILLUST_RECT.top + 100)
        vy = random.uniform(0.5, 1.2)
        vx = random.uniform(-0.3, 0.3)
    elif kind == 'leaf':
        y = random.randint(ILLUST_RECT.top, ILLUST_RECT.top + 60)
        vy = random.uniform(0.7, 1.6)
        vx = random.uniform(-0.8, -0.3)
    else:
        y = random.randint(ILLUST_RECT.top + 200, ILLUST_RECT.top + 500)
        vy = random.uniform(-0.6, -0.2)
        vx = random.uniform(-0.5, 0.5)
    size = random.randint(3, 6) if kind != 'spark' else random.randint(2, 5)
    particles.append([x, y, vy, vx, size, particle_color(kind),
                      pygame.time.get_ticks(), random.randint(3000, 6000)])


def update_particles(kind, now):
    global particle_pool_t0
    if now - particle_pool_t0 > 220:
        particle_pool_t0 = now
        if len(particles) < 50:
            spawn_particle(kind)
            if random.random() < 0.4:
                spawn_particle(kind)
    for p in particles[:]:
        if now - p[6] > p[7] or p[1] > HEIGHT + 20 or p[1] < ILLUST_RECT.top - 20:
            particles.remove(p)
            continue
        p[0] += p[3]
        p[1] += p[2]
        if kind == 'leaf':
            p[3] += math.sin((now + p[0]) / 400) * 0.02
        if kind == 'firefly':
            p[3] += math.sin((now + p[0] * 2) / 300) * 0.03


def draw_particles(surface, kind, now):
    for p in particles:
        x, y, _, _, size, color, born, life = p
        t = (now - born) / life
        alpha = int(255 * min(1, 3 * (1 - t)))
        s = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, alpha), (size * 2, size * 2), size)
        if kind == 'spark':
            pygame.draw.circle(s, (*color, alpha // 3),
                               (size * 2, size * 2), size * 2, 1)
        surface.blit(s, (x - size * 2, y - size * 2))

# ============================================================
#  ОТРИСОВКА UI
# ============================================================

def draw_top_bar(surface, page_idx, total, playing_voice):
    pygame.draw.rect(surface, (40, 28, 76), (0, 0, WIDTH, TOP_H))
    pygame.draw.line(surface, (255, 220, 120), (0, TOP_H), (WIDTH, TOP_H), 3)

    title = font_title.render("Колобок", True, (255, 240, 200))
    shadow = font_title.render("Колобок", True, (60, 30, 80))
    surface.blit(shadow, (32, 22))
    surface.blit(title, (30, 20))

    for rect, label, base in [
        (BTN_PREV, "◀ Назад",   (110, 180, 240)),
        (BTN_READ, "🔊 Прочитать",
                    (100, 220, 130) if playing_voice else (140, 110, 230)),
        (BTN_NEXT, "Вперёд ▶",  (110, 180, 240)),
    ]:
        mx, my = pygame.mouse.get_pos()
        hovered = rect.collidepoint(mx, my)
        c = tuple(min(255, x + 30) for x in base) if hovered else base
        sh = tuple(max(0, x - 70) for x in c)
        pygame.draw.rect(surface, sh, rect.move(0, 4), border_radius=12)
        pygame.draw.rect(surface, c, rect, border_radius=12)
        pygame.draw.rect(surface, (255, 255, 255), rect, 2, border_radius=12)
        txt = font_btn.render(label, True, (30, 20, 50))
        surface.blit(txt, (rect.centerx - txt.get_width() // 2,
                           rect.centery - txt.get_height() // 2))

    mx, my = pygame.mouse.get_pos()
    hovered = BTN_MUTE.collidepoint(mx, my)
    base = (180, 60, 70) if not SOUND_ENABLED else (110, 200, 140)
    c = tuple(min(255, x + 30) for x in base) if hovered else base
    pygame.draw.rect(surface, c, BTN_MUTE, border_radius=10)
    pygame.draw.rect(surface, (255, 255, 255), BTN_MUTE, 2, border_radius=10)
    icon = "🔇" if not SOUND_ENABLED else "🔊"
    img = font_btn.render(icon, True, (30, 20, 50))
    surface.blit(img, (BTN_MUTE.centerx - img.get_width() // 2,
                       BTN_MUTE.centery - img.get_height() // 2))

    dot_r = 6
    total_w = total * (dot_r * 2 + 8) - 8
    start_x = WIDTH // 2 - total_w // 2
    for i in range(total):
        cx = start_x + i * (dot_r * 2 + 8) + dot_r
        cy = TOP_H - 10
        col = (255, 220, 120) if i == page_idx else (110, 95, 150)
        pygame.draw.circle(surface, col, (cx, cy), dot_r)


def draw_text_panel(surface, page_idx):
    pygame.draw.rect(surface, (28, 18, 55), TEXT_RECT)
    pygame.draw.line(surface, (255, 220, 120),
                     (TEXT_RECT.left, TEXT_RECT.top),
                     (TEXT_RECT.right, TEXT_RECT.top), 3)

    pad = 26
    max_w = TEXT_RECT.width - 2 * pad - 200

    active_word_index = -1
    if (voice_channel and voice_channel.get_busy()
            and narration_word_timings):
        elapsed = pygame.time.get_ticks() - narration_start_ms
        for i, (_, st, en) in enumerate(narration_word_timings):
            if st <= elapsed <= en:
                active_word_index = i
                break

    words = [w for (w, _, _) in narration_word_timings] \
        if narration_word_timings else PAGES[page_idx]['text'].split()

    x = TEXT_RECT.left + pad
    y = TEXT_RECT.top + 22
    line_h = font_body.get_linesize() + 4
    space_w = font_body.size(' ')[0]

    i = 0
    while i < len(words):
        w = words[i]
        w_w = font_body.size(w)[0]
        if x + w_w > TEXT_RECT.left + pad + max_w:
            x = TEXT_RECT.left + pad
            y += line_h
        is_active = (i == active_word_index)
        if is_active:
            pad_x, pad_y = 6, 2
            hl = pygame.Rect(x - pad_x, y - pad_y,
                             w_w + pad_x * 2, font_body.get_height() + pad_y * 2)
            pygame.draw.rect(surface, (255, 215, 100), hl, border_radius=8)
            color = (50, 20, 30)
        else:
            color = (240, 235, 220)
        img = font_body.render(w, True, color)
        surface.blit(img, (x, y))
        x += w_w + space_w
        i += 1

    hx = TEXT_RECT.right - 190
    hy = TEXT_RECT.top + 22
    for line in ["Нажми на героев —",
                 "они заговорят!",
                 "",
                 "← → листать",
                 "1-3 страница",
                 "Пробел — пауза",
                 "M — звук вкл/выкл"]:
        t = font_small.render(line, True, (195, 185, 225))
        surface.blit(t, (hx, hy))
        hy += t.get_height() + 3

    if voice_ready.is_set() and voice_cache:
        col = (140, 230, 140)
    elif not voice_ready.is_set():
        col = (255, 200, 120)
    else:
        col = (230, 130, 130)
    pygame.draw.circle(surface, col, (hx + 7, hy + 12), 6)
    st = font_small.render(voice_status, True, (200, 195, 225))
    surface.blit(st, (hx + 18, hy + 4))


def draw_hotspot_highlight(surface, rect, color, t):
    pulse = 0.5 + 0.5 * math.sin(t * 6)
    alpha = int(60 + 90 * pulse)
    r = pygame.Rect(rect)
    s = pygame.Surface((r.w + 22, r.h + 22), pygame.SRCALPHA)
    pygame.draw.rect(s, (*color, alpha), s.get_rect(),
                     width=5, border_radius=22)
    surface.blit(s, (r.x - 11, r.y - 11))


def draw_effects(surface, now):
    for x, y, t0, color, label, char in effects:
        t = (now - t0) / 950
        if t > 1:
            continue
        r = int(20 + 95 * t)
        alpha = int(180 * (1 - t))
        size = r * 2 + 6
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, alpha), (size // 2, size // 2), r, 6)
        surface.blit(s, (x - size // 2, y - size // 2))
        if char:
            img = font_label.render(char, True, (255, 255, 255))
        elif label:
            img = font_label.render(label, True, (255, 255, 255))
        else:
            img = font_label.render(random.choice(["♪", "♫", "♬"]),
                                    True, (255, 240, 180))
        img.set_alpha(int(255 * (1 - t)))
        cy = y - 60 * t
        surface.blit(img, (x - img.get_width() // 2,
                           cy - img.get_height() // 2))


def draw_bubbles(surface, now):
    for x, y, t0, text in bubbles:
        t = (now - t0) / 2600
        if t >= 1:
            continue
        alpha = 255 if t < 0.85 else int(255 * (1 - (t - 0.85) / 0.15))
        img = font_bub.render(text, True, (50, 30, 70))
        pad = 16
        bw = img.get_width() + pad * 2
        bh = img.get_height() + pad
        bx = x - bw // 2
        by = y - 100 - bh
        bx = max(10, min(WIDTH - bw - 10, bx))
        by = max(ILLUST_RECT.top + 10, by)

        bubble_surf = pygame.Surface((bw, bh + 22), pygame.SRCALPHA)
        pygame.draw.rect(bubble_surf, (255, 250, 240, alpha),
                         (0, 0, bw, bh), border_radius=22)
        pygame.draw.rect(bubble_surf, (200, 170, 90, alpha),
                         (0, 0, bw, bh), 3, border_radius=22)
        tx = bw // 2
        pts = [(tx - 14, bh - 2), (tx + 14, bh - 2), (tx, bh + 20)]
        pygame.draw.polygon(bubble_surf, (255, 250, 240, alpha), pts)
        pygame.draw.polygon(bubble_surf, (200, 170, 90, alpha), pts, 3)
        surface.blit(bubble_surf, (bx, by))
        img.set_alpha(alpha)
        surface.blit(img, (bx + pad, by + pad // 2))

# ============================================================
#  ЛОГИКА
# ============================================================

def trigger_hotspot(page_idx, key, mx, my):
    entry = HOTSPOT_SOUNDS.get((f'page{page_idx}', key))
    if not entry:
        return
    sfx_name, color, label, phrase = entry
    if SOUND_ENABLED:
        snd = SFX.get(sfx_name)
        if snd:
            snd.play()
    spawn_effect(mx, my, color, label)
    spawn_bubble(mx, my - 40, phrase)


def go_to_page(new_idx, now):
    global current_page, prev_page, transition_t0
    if new_idx == current_page:
        return
    prev_page = current_page
    current_page = new_idx
    transition_t0 = now
    if SOUND_ENABLED:
        SFX['whoosh'].play()
        if voice_channel:
            voice_channel.stop()

# ============================================================
#  ГЛАВНЫЙ ЦИКЛ
# ============================================================

def main():
    global prev_page, transition_t0

    threading.Thread(target=generate_voice,
                     args=(PAGES,), daemon=True).start()

    set_sound_enabled(True)

    page_data = {'hotspots': {}}

    running = True
    while running:
        now = pygame.time.get_ticks()
        t = now / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if BTN_PREV.collidepoint(mx, my):
                    go_to_page((current_page - 1) % len(PAGES), now)
                elif BTN_NEXT.collidepoint(mx, my):
                    go_to_page((current_page + 1) % len(PAGES), now)
                elif BTN_READ.collidepoint(mx, my):
                    play_voice(current_page)
                elif BTN_MUTE.collidepoint(mx, my):
                    set_sound_enabled(not SOUND_ENABLED)
                else:
                    key = find_hotspot(mx, my, page_data.get('hotspots'))
                    if key:
                        trigger_hotspot(current_page, key, mx, my)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_LEFT:
                    go_to_page((current_page - 1) % len(PAGES), now)
                elif event.key == pygame.K_RIGHT:
                    go_to_page((current_page + 1) % len(PAGES), now)
                elif event.key == pygame.K_r:
                    play_voice(current_page)
                elif event.key == pygame.K_m:
                    set_sound_enabled(not SOUND_ENABLED)
                elif event.key == pygame.K_SPACE:
                    if voice_channel and voice_channel.get_busy():
                        voice_channel.pause()
                    elif voice_channel:
                        voice_channel.unpause()
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    idx = event.key - pygame.K_1
                    if idx < len(PAGES):
                        go_to_page(idx, now)

        # автоозвучка при первой готовности
        if (current_page not in narration_auto_played
                and voice_ready.is_set()
                and current_page in voice_cache
                and SOUND_ENABLED):
            play_voice(current_page)
            narration_auto_played.add(current_page)

        # приглушение музыки во время речи
        if SOUND_ENABLED and MUSIC_CHANNEL.get_busy():
            if voice_channel and voice_channel.get_busy():
                MUSIC_CHANNEL.set_volume(0.12)
            else:
                MUSIC_CHANNEL.set_volume(0.45)

        # ---- отрисовка ----
        screen.fill((18, 12, 36))

        clip = screen.get_clip()
        screen.set_clip(ILLUST_RECT)

        transition_progress = 1.0
        if prev_page is not None and prev_page != current_page:
            tp = (now - transition_t0) / TRANSITION_MS
            if tp >= 1:
                prev_page = None
                transition_progress = 1.0
            else:
                transition_progress = tp

        if prev_page is not None and prev_page != current_page:
            screen_old = pygame.Surface((WIDTH, ILLUST_RECT.height))
            screen_new = pygame.Surface((WIDTH, ILLUST_RECT.height))
            PAGES[prev_page]['draw'](screen_old, t)
            PAGES[current_page]['draw'](screen_new, t)
            dx_old = int(-WIDTH * transition_progress)
            dx_new = int(WIDTH * (1 - transition_progress))
            screen.blit(screen_old, (dx_old, ILLUST_RECT.top))
            screen.blit(screen_new, (dx_new, ILLUST_RECT.top))
            page_data = {'hotspots': {}}
        else:
            page_data = {
                'hotspots': PAGES[current_page]['draw'](screen, t)
            }

        update_particles(PAGES[current_page]['particle'], now)
        draw_particles(screen, PAGES[current_page]['particle'], now)

        mx, my = pygame.mouse.get_pos()
        key = find_hotspot(mx, my, page_data.get('hotspots'))
        if key:
            rect = page_data['hotspots'][key]
            color = (255, 240, 180)
            for k, entry in HOTSPOT_SOUNDS.items():
                if k[0] == f'page{current_page}' and k[1] == key:
                    color = entry[1]
                    break
            draw_hotspot_highlight(screen, rect, color, t)

        screen.set_clip(clip)

        playing_voice = bool(voice_channel and voice_channel.get_busy())
        draw_top_bar(screen, current_page, len(PAGES), playing_voice)
        draw_text_panel(screen, current_page)
        draw_effects(screen, now)
        draw_bubbles(screen, now)

        effects[:] = [e for e in effects if now - e[2] < 950]
        bubbles[:] = [b for b in bubbles if now - b[2] < 2600]

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()