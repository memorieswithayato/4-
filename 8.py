import tkinter as tk
import math
import struct
import random

# ---------------- АУДИО ----------------
AUDIO = False
try:
    import pygame
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    AUDIO = True
except Exception as e:
    print("Аудио не инициализировано:", e)

SR = 44100

def make_sound(freq, duration=0.55, volume=0.35):
    """Генерирует мягкий музыкальный тон с обертонами."""
    if not AUDIO:
        return None
    n = int(SR * duration)
    data = bytearray()
    attack, release = 0.01, 0.35
    for i in range(n):
        t = i / SR
        if t < attack:
            env = t / attack
        elif t > duration - release:
            env = max(0.0, (duration - t) / release)
        else:
            env = 1.0
        s = (math.sin(2 * math.pi * freq * t)
             + 0.25 * math.sin(2 * math.pi * freq * 2 * t)
             + 0.10 * math.sin(2 * math.pi * freq * 3 * t))
        v = int(volume * env * 14000 * s / 1.35)
        v = max(-32768, min(32767, v))
        data.extend(struct.pack('<hh', v, v))
    return pygame.mixer.Sound(buffer=bytes(data))

def make_win_sound():
    """Мажорный аккорд-арпеджио."""
    if not AUDIO:
        return None
    duration, n = 1.5, int(SR * 1.5)
    freqs = [523.25, 659.25, 783.99, 1046.50]
    data = bytearray()
    for i in range(n):
        t = i / SR
        s = 0.0
        for j, f in enumerate(freqs):
            start = j * 0.10
            if t < start:
                continue
            lt = t - start
            env = min(1.0, lt * 50) * max(0.0, min(1.0, (duration - t) * 1.5))
            s += env * math.sin(2 * math.pi * f * lt)
        v = int(0.22 * 14000 * s / 4)
        v = max(-32768, min(32767, v))
        data.extend(struct.pack('<hh', v, v))
    return pygame.mixer.Sound(buffer=bytes(data))

def make_error_sound():
    """Короткий низкий «бз-з»."""
    if not AUDIO:
        return None
    duration, n = 0.22, int(SR * 0.22)
    data = bytearray()
    for i in range(n):
        t = i / SR
        env = max(0.0, 1 - t / duration)
        s = math.sin(2 * math.pi * 140 * t) * (1 + 0.6 * math.sin(2 * math.pi * 28 * t))
        v = int(0.22 * env * 12000 * s)
        v = max(-32768, min(32767, v))
        data.extend(struct.pack('<hh', v, v))
    return pygame.mixer.Sound(buffer=bytes(data))

# ---------------- КОНСТАНТЫ ----------------
NOTE_NAMES = ['C', 'D', 'E', 'F', 'G', 'A', 'B', 'C', 'D']
FREQS = [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25, 587.33]
COLORS = ['#FF6B6B', '#FFA94D', '#FFD43B', '#69DB7C', '#38D9A9',
          '#4DABF7', '#9775FA', '#F783AC', '#FF9F43']

# ---------------- ИГРА ----------------
class MusicalPuzzle:
    GRID = 3
    CELL = 130
    PAD = 8
    CANVAS_W = 820
    CANVAS_H = 720

    def __init__(self, root):
        self.root = root
        root.title("Музыкальный пазл")
        root.configure(bg='#0f0f23')
        root.resizable(False, False)
        root.geometry(f"{self.CANVAS_W}x{self.CANVAS_H}+80+40")

        self.canvas = tk.Canvas(root, width=self.CANVAS_W, height=self.CANVAS_H,
                                bg='#0f0f23', highlightthickness=0)
        self.canvas.pack()

        self.grid_w = self.GRID * self.CELL
        self.grid_x = (self.CANVAS_W - self.grid_w) // 2
        self.grid_y = 110

        # Звуки
        self.sounds = {}
        self.win_sound = self.error_sound = None
        if AUDIO:
            for name, f in zip(NOTE_NAMES, FREQS):
                self.sounds[name] = make_sound(f)
            self.win_sound = make_win_sound()
            self.error_sound = make_error_sound()

        self.pieces = []
        self.slots = []
        self.dragging = None
        self.drag_offset = (0, 0)
        self.won = False
        self.confetti = []

        self.draw_decorations()
        self.draw_header()
        self.setup_grid()
        self.setup_tray()
        self.bind_events()

    # ---------- Рисование ----------
    def draw_decorations(self):
        for _ in range(50):
            x = random.randint(0, self.CANVAS_W)
            y = random.randint(0, self.CANVAS_H)
            r = random.choice([1, 1, 2])
            c = random.choice(['#2a2a4e', '#3a3a5e', '#4a4a7e'])
            self.canvas.create_oval(x, y, x + r, y + r, fill=c, outline='')

    def draw_header(self):
        self.canvas.create_text(self.CANVAS_W // 2, 35,
                                text="🎵 Музыкальный пазл 🎵",
                                fill='#FFD93D',
                                font=('Comic Sans MS', 28, 'bold'))
        self.canvas.create_text(self.CANVAS_W // 2, 78,
                                text="Перетащи плитку в квадрат такого же цвета",
                                fill='#A8B2D1', font=('Comic Sans MS', 13))

    def _dim_color(self, hex_color, factor=0.32):
        hex_color = hex_color.lstrip('#')
        r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        br, bg_, bb = 0x15, 0x15, 0x2e
        nr = int(r * factor + br * (1 - factor))
        ng = int(g * factor + bg_ * (1 - factor))
        nb = int(b * factor + bb * (1 - factor))
        return f'#{nr:02x}{ng:02x}{nb:02x}'

    def setup_grid(self):
        for r in range(self.GRID):
            for c in range(self.GRID):
                idx = r * self.GRID + c
                x = self.grid_x + c * self.CELL
                y = self.grid_y + r * self.CELL
                color = COLORS[idx]
                note = NOTE_NAMES[idx]
                self.canvas.create_rectangle(
                    x + self.PAD, y + self.PAD,
                    x + self.CELL - self.PAD, y + self.CELL - self.PAD,
                    outline=color, width=4, dash=(8, 6), fill='#15152e')
                hint_id = self.canvas.create_text(
                    x + self.CELL / 2, y + self.CELL / 2,
                    text=note, fill=self._dim_color(color),
                    font=('Comic Sans MS', 34, 'bold'))
                self.slots.append({
                    'x': x, 'y': y, 'color': color, 'note': note,
                    'filled': False, 'hint_id': hint_id
                })

    def setup_tray(self):
        piece_size, gap = 78, 4
        total = 9 * piece_size + 8 * gap
        start_x = (self.CANVAS_W - total) // 2
        tray_y = self.CANVAS_H - piece_size - 30

        self.canvas.create_rectangle(
            start_x - 18, tray_y - 18,
            start_x + total + 18, tray_y + piece_size + 18,
            outline='#3a3a5e', width=2, fill='#151530')

        shuffled = list(range(9))
        random.shuffle(shuffled)
        for i, idx in enumerate(shuffled):
            x = start_x + i * (piece_size + gap)
            self.create_piece(x, tray_y, piece_size, COLORS[idx], NOTE_NAMES[idx])

    def create_piece(self, x, y, size, color, note):
        tag = f"piece{len(self.pieces)}"
        # Тень
        self.canvas.create_rectangle(x + 3, y + 3, x + size + 3, y + size + 3,
                                     fill='#000000', outline='', tags=(tag,))
        # Сама плитка
        self.canvas.create_rectangle(x, y, x + size, y + size,
                                     fill=color, outline='#ffffff', width=3,
                                     tags=(tag,))
        # Нота
        self.canvas.create_text(x + size / 2, y + size / 2, text=note,
                                fill='#ffffff',
                                font=('Comic Sans MS', 24, 'bold'),
                                tags=(tag,))
        self.pieces.append({
            'x': x, 'y': y, 'size': size,
            'color': color, 'note': note,
            'home': (x, y), 'tag': tag, 'placed': False
        })

    # ---------- События ----------
    def bind_events(self):
        self.canvas.bind('<Button-1>', self.on_down)
        self.canvas.bind('<B1-Motion>', self.on_move)
        self.canvas.bind('<ButtonRelease-1>', self.on_up)

    def on_down(self, event):
        if self.won:
            return
        items = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        for item in reversed(items):
            for tag in self.canvas.gettags(item):
                if tag.startswith('piece'):
                    piece = self.pieces[int(tag[5:])]
                    if piece['placed']:
                        return
                    self.dragging = piece
                    self.drag_offset = (event.x - piece['x'], event.y - piece['y'])
                    self.canvas.tag_raise(tag)
                    return

    def on_move(self, event):
        if not self.dragging:
            return
        p = self.dragging
        nx = event.x - self.drag_offset[0]
        ny = event.y - self.drag_offset[1]
        self.canvas.move(p['tag'], nx - p['x'], ny - p['y'])
        p['x'], p['y'] = nx, ny

    def on_up(self, event):
        if not self.dragging:
            return
        p = self.dragging
        self.dragging = None
        cx = p['x'] + p['size'] / 2
        cy = p['y'] + p['size'] / 2

        for slot in self.slots:
            sx = slot['x'] + self.CELL / 2
            sy = slot['y'] + self.CELL / 2
            if abs(cx - sx) < self.CELL * 0.55 and abs(cy - sy) < self.CELL * 0.55:
                if not slot['filled'] and slot['color'] == p['color']:
                    self.place_piece(p, slot)
                else:
                    self.error_feedback(p)
                return
        self.return_home(p)

    # ---------- Логика ----------
    def place_piece(self, p, slot):
        self.canvas.delete(slot['hint_id'])
        tx = slot['x'] + (self.CELL - p['size']) / 2
        ty = slot['y'] + (self.CELL - p['size']) / 2
        self.canvas.move(p['tag'], tx - p['x'], ty - p['y'])
        p['x'], p['y'] = tx, ty
        p['placed'] = True
        slot['filled'] = True

        self.play_note(p['note'])
        self.flash_slot(slot)

        if all(s['filled'] for s in self.slots):
            self.won = True
            self.root.after(800, self.win)

    def play_note(self, note):
        if AUDIO and note in self.sounds:
            try:
                self.sounds[note].play()
            except Exception:
                pass

    def flash_slot(self, slot):
        x1 = slot['x'] + self.PAD
        y1 = slot['y'] + self.PAD
        x2 = slot['x'] + self.CELL - self.PAD
        y2 = slot['y'] + self.CELL - self.PAD
        rect = self.canvas.create_rectangle(x1, y1, x2, y2,
                                            outline='#ffffff', width=5)
        def step(i=0):
            if i > 8:
                try: self.canvas.delete(rect)
                except Exception: pass
                return
            try:
                self.canvas.coords(rect, x1 + i*2, y1 + i*2, x2 - i*2, y2 - i*2)
            except Exception:
                return
            self.root.after(30, lambda: step(i + 1))
        step()

    def error_feedback(self, p):
        if AUDIO and self.error_sound:
            try: self.error_sound.play()
            except Exception: pass
        def shake(i=0):
            if i >= 6:
                self.return_home(p)
                return
            dx = 10 if i % 2 == 0 else -20
            try:
                self.canvas.move(p['tag'], dx, 0)
                p['x'] += dx
            except Exception:
                return
            self.root.after(35, lambda: shake(i + 1))
        shake()

    def return_home(self, p):
        tx, ty = p['home']
        steps = 10
        def step(i=0):
            if i >= steps:
                try:
                    self.canvas.move(p['tag'], tx - p['x'], ty - p['y'])
                    p['x'], p['y'] = tx, ty
                except Exception: pass
                return
            dx = (tx - p['x']) / (steps - i)
            dy = (ty - p['y']) / (steps - i)
            try:
                self.canvas.move(p['tag'], dx, dy)
                p['x'] += dx
                p['y'] += dy
            except Exception:
                return
            self.root.after(20, lambda: step(i + 1))
        step()

    # ---------- Победа ----------
    def win(self):
        if AUDIO and self.win_sound:
            try: self.win_sound.play()
            except Exception: pass

        # Конфетти
        for _ in range(70):
            x = random.randint(0, self.CANVAS_W)
            y = random.randint(-120, 0)
            r = random.randint(4, 9)
            c = random.choice(COLORS)
            item = self.canvas.create_oval(x, y, x + r*2, y + r*2,
                                            fill=c, outline='')
            self.confetti.append([item, random.uniform(2, 6), y])
        self.animate_confetti()

        # Окно победы
        self.canvas.create_rectangle(
            self.CANVAS_W/2 - 290, self.CANVAS_H/2 - 115,
            self.CANVAS_W/2 + 290, self.CANVAS_H/2 + 115,
            fill='#1a1a3e', outline='#FFD93D', width=6)
        self.canvas.create_text(self.CANVAS_W/2, self.CANVAS_H/2 - 45,
                                text="🎉 МОЛОДЕЦ! 🎉", fill='#FFD93D',
                                font=('Comic Sans MS', 40, 'bold'))
        self.canvas.create_text(self.CANVAS_W/2, self.CANVAS_H/2 + 15,
                                text="Ты собрал всю мелодию!",
                                fill='#ffffff', font=('Comic Sans MS', 18))
        self.canvas.create_text(self.CANVAS_W/2, self.CANVAS_H/2 + 60,
                                text="Нажми, чтобы играть снова",
                                fill='#A8B2D1', font=('Comic Sans MS', 14))

        self.play_melody()

        self.canvas.bind('<Button-1>', self.restart)
        self.canvas.bind('<B1-Motion>', lambda e: None)
        self.canvas.bind('<ButtonRelease-1>', lambda e: None)

    def animate_confetti(self):
        if not self.confetti:
            return
        alive = []
        for item, speed, y in self.confetti:
            y += speed
            try:
                self.canvas.move(item, 0, speed)
            except Exception:
                continue
            if y < self.CANVAS_H + 20:
                alive.append([item, speed, y])
            else:
                try: self.canvas.delete(item)
                except Exception: pass
        self.confetti = alive
        if alive:
            self.root.after(30, self.animate_confetti)

    def play_melody(self):
        for i, note in enumerate(NOTE_NAMES):
            self.root.after(200 + i * 280, lambda n=note: self.play_note(n))

    # ---------- Перезапуск ----------
    def restart(self, event=None):
        self.canvas.delete('all')
        self.pieces, self.slots, self.confetti = [], [], []
        self.dragging = None
        self.won = False
        self.draw_decorations()
        self.draw_header()
        self.setup_grid()
        self.setup_tray()
        self.bind_events()


def main():
    root = tk.Tk()
    MusicalPuzzle(root)
    root.mainloop()


if __name__ == '__main__':
    main()