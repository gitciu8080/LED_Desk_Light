"""
RGB WS2811 预设效果库 — 10 种灯效
每个效果是一个类，通过 update(np, dt_ms) 驱动帧更新。
np 是 neopixel.NeoPixel 实例，dt_ms 是距上次调用的毫秒数。
"""

import time
import random

NUM_LEDS = 12


def _hsv_to_rgb(h, s, v):
    """HSV → RGB，h/s/v 范围 0.0–1.0，返回 (r,g,b) 0–255"""
    if s == 0:
        r = g = b = int(v * 255)
        return r, g, b
    h = h * 6.0
    i = int(h)
    f = h - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i = i % 6
    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    return int(r * 255), int(g * 255), int(b * 255)


def _wheel(pos):
    """色轮：输入 0–255，返回 (r,g,b)"""
    pos = pos % 256
    if pos < 85:
        return pos * 3, 255 - pos * 3, 0
    elif pos < 170:
        pos -= 85
        return 255 - pos * 3, 0, pos * 3
    else:
        pos -= 170
        return 0, pos * 3, 255 - pos * 3


# ==================== 效果 1：静态单色 ====================
class EffectStatic:
    def __init__(self, r=255, g=100, b=50):
        self.r = r
        self.g = g
        self.b = b

    def update(self, np, dt_ms):
        for i in range(NUM_LEDS):
            np[i] = (self.r, self.g, self.b)
        np.write()

    def set_color(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b


# ==================== 效果 2：流水灯 ====================
class EffectChase:
    def __init__(self, r=255, g=0, b=0, speed=80):
        self.r = r
        self.g = g
        self.b = b
        self.speed = speed  # 毫秒/步
        self.pos = 0
        self.accum = 0

    def update(self, np, dt_ms):
        self.accum += dt_ms
        while self.accum >= self.speed:
            self.accum -= self.speed
            self.pos = (self.pos + 1) % NUM_LEDS

        for i in range(NUM_LEDS):
            if i == self.pos:
                np[i] = (self.r, self.g, self.b)
            else:
                np[i] = (0, 0, 0)
        np.write()

    def set_color(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b


# ==================== 效果 3：呼吸灯 ====================
class EffectBreathe:
    def __init__(self, r=255, g=80, b=40, period=3000):
        self.r = r
        self.g = g
        self.b = b
        self.period = period  # 完整呼吸周期（毫秒）
        self.phase = 0

    def update(self, np, dt_ms):
        self.phase += dt_ms
        # 正弦波 0→1→0
        import math
        factor = (math.sin(self.phase * 2 * 3.14159 / self.period - 3.14159 / 2) + 1) / 2
        fr = int(self.r * factor)
        fg = int(self.g * factor)
        fb = int(self.b * factor)
        for i in range(NUM_LEDS):
            np[i] = (fr, fg, fb)
        np.write()

    def set_color(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b


# ==================== 效果 4：彩虹循环 ====================
class EffectRainbow:
    def __init__(self, speed=15):
        self.speed = speed  # 数值越大越快
        self.offset = 0

    def update(self, np, dt_ms):
        step = int(self.speed * dt_ms / 16)
        self.offset = (self.offset + step) % 256
        for i in range(NUM_LEDS):
            hue = (i * 256 // NUM_LEDS + self.offset) % 256
            np[i] = _wheel(hue)
        np.write()


# ==================== 效果 5：彩虹流水 ====================
class EffectRainbowRunning:
    def __init__(self, speed=20):
        self.speed = speed
        self.offset = 0

    def update(self, np, dt_ms):
        step = int(self.speed * dt_ms / 16)
        self.offset = (self.offset + step) % 256
        for i in range(NUM_LEDS):
            hue = (i * 256 // NUM_LEDS + self.offset) % 256
            np[i] = _wheel(hue)
        np.write()


# ==================== 效果 6：渐变交替（Color Wipe） ====================
class EffectColorWipe:
    def __init__(self, r=255, g=0, b=0, speed=60):
        self.r = r
        self.g = g
        self.b = b
        self.speed = speed
        self.pos = 0
        self.accum = 0
        self.direction = 1

    def update(self, np, dt_ms):
        self.accum += dt_ms
        while self.accum >= self.speed:
            self.accum -= self.speed
            self.pos += self.direction
            if self.pos >= NUM_LEDS:
                self.pos = NUM_LEDS - 2
                self.direction = -1
            elif self.pos < 0:
                self.pos = 1
                self.direction = 1

        for i in range(NUM_LEDS):
            if i <= self.pos and self.direction == 1:
                np[i] = (self.r, self.g, self.b)
            elif i >= self.pos and self.direction == -1:
                np[i] = (self.r, self.g, self.b)
            else:
                np[i] = (0, 0, 0)
        np.write()

    def set_color(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b


# ==================== 效果 7：流星 ====================
class EffectMeteor:
    def __init__(self, r=255, g=255, b=255, speed=70, tail=3):
        self.r = r
        self.g = g
        self.b = b
        self.speed = speed
        self.tail = min(tail, NUM_LEDS)
        self.pos = 0
        self.accum = 0

    def update(self, np, dt_ms):
        self.accum += dt_ms
        while self.accum >= self.speed:
            self.accum -= self.speed
            self.pos = (self.pos + 1) % (NUM_LEDS + self.tail)

        for i in range(NUM_LEDS):
            dist = (self.pos - i) % (NUM_LEDS + self.tail)
            if dist < self.tail:
                factor = 1.0 - dist / self.tail
                np[i] = (
                    int(self.r * factor),
                    int(self.g * factor),
                    int(self.b * factor),
                )
            else:
                np[i] = (0, 0, 0)
        np.write()

    def set_color(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b


# ==================== 效果 8：闪烁 ====================
class EffectStrobe:
    def __init__(self, r=255, g=255, b=255, interval=200):
        self.r = r
        self.g = g
        self.b = b
        self.interval = interval
        self.accum = 0
        self.on = True

    def update(self, np, dt_ms):
        self.accum += dt_ms
        while self.accum >= self.interval:
            self.accum -= self.interval
            self.on = not self.on

        color = (self.r, self.g, self.b) if self.on else (0, 0, 0)
        for i in range(NUM_LEDS):
            np[i] = color
        np.write()

    def set_color(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b


# ==================== 效果 9：双色渐变 ====================
class EffectTwoColorGradient:
    def __init__(self, r1=255, g1=0, b1=0, r2=0, g2=0, b2=255, speed=10):
        self.r1, self.g1, self.b1 = r1, g1, b1
        self.r2, self.g2, self.b2 = r2, g2, b2
        self.speed = speed
        self.offset = 0

    def update(self, np, dt_ms):
        step = int(self.speed * dt_ms / 16)
        self.offset = (self.offset + step) % 256
        for i in range(NUM_LEDS):
            t = ((i * 256 // NUM_LEDS + self.offset) % 256) / 255.0
            r = int(self.r1 + (self.r2 - self.r1) * t)
            g = int(self.g1 + (self.g2 - self.g1) * t)
            b = int(self.b1 + (self.b2 - self.b1) * t)
            np[i] = (r, g, b)
        np.write()

    def set_colors(self, r1, g1, b1, r2, g2, b2):
        self.r1, self.g1, self.b1 = r1, g1, b1
        self.r2, self.g2, self.b2 = r2, g2, b2


# ==================== 效果 10：派对灯 ====================
class EffectParty:
    def __init__(self, interval=150):
        self.interval = interval
        self.accum = 0

    def update(self, np, dt_ms):
        self.accum += dt_ms
        while self.accum >= self.interval:
            self.accum -= self.interval
            for i in range(NUM_LEDS):
                hue = random.random()
                r, g, b = _hsv_to_rgb(hue, 1.0, 1.0)
                np[i] = (r, g, b)

        np.write()


# ==================== 效果注册表 ====================
EFFECTS = [
    ("静态单色", EffectStatic),
    ("流水灯", EffectChase),
    ("呼吸灯", EffectBreathe),
    ("彩虹循环", EffectRainbow),
    ("彩虹流水", EffectRainbowRunning),
    ("渐变交替", EffectColorWipe),
    ("流星", EffectMeteor),
    ("闪烁", EffectStrobe),
    ("双色渐变", EffectTwoColorGradient),
    ("派对灯", EffectParty),
]
