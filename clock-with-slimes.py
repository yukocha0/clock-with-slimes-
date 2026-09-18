"""clock-with-slimes
"""

import random
import shutil
import sys
import time
from datetime import datetime

# ---------- clock font (5 rows, 5 chars wide) ----------
FONT = {
    "0": ["█████", "█   █", "█   █", "█   █", "█████"],
    "1": ["  █  ", " ██  ", "  █  ", "  █  ", " ███ "],
    "2": ["█████", "    █", "█████", "█    ", "█████"],
    "3": ["█████", "    █", "█████", "    █", "█████"],
    "4": ["█   █", "█   █", "█████", "    █", "    █"],
    "5": ["█████", "█    ", "█████", "    █", "█████"],
    "6": ["█████", "█    ", "█████", "█   █", "█████"],
    "7": ["█████", "    █", "    █", "    █", "    █"],
    "8": ["█████", "█   █", "█████", "█   █", "█████"],
    "9": ["█████", "█   █", "█████", "    █", "█████"],
    ":": ["     ", "  █  ", "     ", "  █  ", "     "],
    " ": ["     ", "     ", "     ", "     ", "     "],
}
CLOCK_H = 5
GAP = "  "
SLIME_HALF = 3   # slime frames are ~7 wide, so half is 3


def render_clock(text):
    rows = [""] * CLOCK_H
    for ch in text:
        glyph = FONT.get(ch, FONT[" "])
        for i in range(CLOCK_H):
            rows[i] += glyph[i] + GAP
    return [r[: -len(GAP)] for r in rows]


# ---------- slime frames (all 7 chars wide) ----------
SLIME_NORMAL = [
    " .---. ",
    "( o o )",
    " `---' ",
]
SLIME_BREATHE = [
    "  ---  ",
    "( o o )",
    " `---' ",
]
SLIME_STRETCH = [
    "  .-.  ",
    " (> <) ",
    " (   ) ",
    "  `-'  ",
]
SLIME_SQUASH = [
    ".-----.",
    "( = = )",
]


class Slime:
    def __init__(self, cols):
        self.x = random.randint(SLIME_HALF, max(SLIME_HALF, cols - SLIME_HALF - 1))
        self.y = 0.0
        self.vy = 0.0
        self.dir = random.choice([-1, 1])
        self.squash_timer = 0
        self.move_timer = random.randint(10, 40)
        self.tick = random.randint(0, 30)   # random phase so they don't sync up

    def clamp(self, cols):
        lo = SLIME_HALF
        hi = max(lo, cols - SLIME_HALF - 1)
        self.x = max(lo, min(hi, self.x))

    def update(self, cols):
        self.tick += 1
        on_ground = self.y <= 0.0 and self.vy <= 0.0

        if on_ground:
            self.y = 0.0
            self.vy = 0.0

            self.move_timer -= 1
            if self.move_timer <= 0:
                if random.random() < 0.6:
                    self.dir = random.choice([-1, 1])
                self.move_timer = random.randint(10, 40)

            if random.random() < 0.18:
                self.x += self.dir

            if random.random() < 0.035:
                self.vy = 2.0 + random.random() * 0.5

        if self.vy != 0.0 or self.y > 0.0:
            self.vy -= 0.6
            self.y += self.vy
            if self.y <= 0.0:
                self.y = 0.0
                self.vy = 0.0
                self.squash_timer = 5

        if self.squash_timer > 0:
            self.squash_timer -= 1

        self.clamp(cols)

    def frames(self):
        if self.squash_timer > 0:
            return SLIME_SQUASH
        if self.y > 0.3:
            return SLIME_STRETCH
        if (self.tick // 5) % 2 == 0:
            return SLIME_NORMAL
        return SLIME_BREATHE

    def y_int(self):
        return int(round(self.y))


# ---------- time-of-day -> slime count ----------
def slime_count(now):
    """0 slimes at 00:00, ~1 more every 2 hours, 12 by late evening."""
    minutes = now.hour * 60 + now.minute
    return max(0, min(12, int((minutes + 60) / 120)))


def render_frame(cols, rows, clock_str, slimes):
    buf = [[" "] * cols for _ in range(rows)]

    # clock
    clock_rows = render_clock(clock_str)
    clock_top = max(1, (rows - CLOCK_H) // 3)
    for i, line in enumerate(clock_rows):
        r = clock_top + i
        if 0 <= r < rows:
            pad = max(0, (cols - len(line)) // 2)
            for j, ch in enumerate(line):
                c = pad + j
                if 0 <= c < cols:
                    buf[r][c] = ch

    # ground
    ground = rows - 1
    for c in range(cols):
        buf[ground][c] = "_"

    # slimes — draw in list order so later slimes sit "in front".
    # A small vertical offset per slime helps overlapping ones stay readable.
    for s in slimes:
        frames = s.frames()
        sh = len(frames)
        yoff = s.y_int()
        for i, line in enumerate(frames):
            r = ground - 1 - (sh - 1 - i) - yoff
            if 0 <= r < rows:
                pad = s.x - len(line) // 2
                for j, ch in enumerate(line):
                    c = pad + j
                    if 0 <= c < cols:
                        buf[r][c] = ch

    return "\n".join("".join(row) for row in buf)


def main():
    fmt = "%H:%M:%S"
    if len(sys.argv) > 1 and sys.argv[1] in ("12", "--12"):
        fmt = "%I:%M:%S"

    sys.stdout.write("\033[?1049h\033[?25l\033[?7l\033[2J")
    sys.stdout.flush()

    slimes = []
    last_size = (0, 0)

    try:
        while True:
            cols, rows = shutil.get_terminal_size((80, 24))
            now = datetime.now()

            if (cols, rows) != last_size:
                last_size = (cols, rows)
                sys.stdout.write("\033[2J")
                for s in slimes:
                    s.clamp(cols)

            # how many slimes should exist right now?
            target = slime_count(now)
            # don't overcrowd a narrow terminal (each slime needs ~6 cols)
            if target > 0:
                target = min(target, max(1, cols // 6))

            if target != len(slimes):
                if target < len(slimes):
                    del slimes[target:]
                else:
                    for _ in range(target - len(slimes)):
                        slimes.append(Slime(cols))

            for s in slimes:
                s.update(cols)

            frame = render_frame(cols, rows, now.strftime(fmt), slimes)
            sys.stdout.write("\033[H" + frame)
            sys.stdout.flush()

            time.sleep(1.0 / 10)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[?7h\033[?25h\033[?1049l")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
