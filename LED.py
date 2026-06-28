"""
LED 核心驱动模块 — ESP32 屏幕台灯
- 冷暖 PWM 控制 (GPIO10/GPIO20)
- WS2811 RGB 控制 (GPIO8, 12芯片)
- 触摸按键 (GPIO9)
- LEDState 统一状态管理，供 web/蓝牙/触摸三方访问
"""

from machine import Pin, PWM
import neopixel
import time
import effects

# ==================== 硬件初始化 ====================
cold_LED = PWM(Pin(20))
cold_LED.freq(1000)
warm_LED = PWM(Pin(10))
warm_LED.freq(1000)
switch = Pin(9, Pin.IN, Pin.PULL_UP)

# WS2811: 12 芯片
RGB_PIN = Pin(8)
NUM_LEDS = 12
neo = neopixel.NeoPixel(RGB_PIN, NUM_LEDS)


# ==================== LED 全局状态 ====================
class LEDState:
    def __init__(self):
        self.power = False
        self.brightness = 80
        self.warm_level = 100
        self.cold_level = 100
        self.rgb_r = 255
        self.rgb_g = 0
        self.rgb_b = 0
        self.preset_index = 0
        self.mode = "off"

        self._effect = effects.EffectStatic(255, 0, 0)
        self._last_tick = time.ticks_ms()

    def apply_preset(self, index):
        if 0 <= index < len(effects.EFFECTS):
            self.preset_index = index
            cls = effects.EFFECTS[index][1]
            self._effect = cls()
            if hasattr(self._effect, "set_color"):
                self._effect.set_color(self.rgb_r, self.rgb_g, self.rgb_b)
            if hasattr(self._effect, "set_colors"):
                self._effect.set_colors(self.rgb_r, self.rgb_g, self.rgb_b, 0, 0, 255)

    def set_rgb(self, r, g, b):
        self.rgb_r = max(0, min(255, r))
        self.rgb_g = max(0, min(255, g))
        self.rgb_b = max(0, min(255, b))
        if hasattr(self._effect, "set_color"):
            self._effect.set_color(self.rgb_r, self.rgb_g, self.rgb_b)

    def update_pwm(self):
        if self.power and self.mode != "rgb" and self.mode != "off":
            b = self.brightness / 100.0
            w = int(65535 * (self.warm_level / 100.0) * b)
            c = int(65535 * (self.cold_level / 100.0) * b)
            if self.mode == "warm":
                c = 0
            elif self.mode == "cold":
                w = 0
        else:
            w = 0
            c = 0
        warm_LED.duty_u16(w)
        cold_LED.duty_u16(c)

    async def update(self):
        now = time.ticks_ms()
        dt = time.ticks_diff(now, self._last_tick)
        self._last_tick = now

        self.update_pwm()

        if self.power and self.mode == "rgb":
            self._effect.update(neo, dt)
        else:
            for i in range(NUM_LEDS):
                neo[i] = (0, 0, 0)
            neo.write()

        import uasyncio
        await uasyncio.sleep_ms(20)


state = LEDState()


# ==================== 底层驱动函数（保留兼容） ====================

def RGB():
    state.mode = "rgb"
    state.power = True
    state.apply_preset(0)
    state.set_rgb(255, 0, 0)


def breathe():
    for i in range(0, 65536, 256):
        cold_LED.duty_u16(i)
        warm_LED.duty_u16(i)
        time.sleep(0.01)
    for i in range(65535, -1, -256):
        cold_LED.duty_u16(i)
        warm_LED.duty_u16(i)
        time.sleep(0.01)
    cold_LED.duty_u16(0)
    warm_LED.duty_u16(0)


def Open_LED(color, light=80, speed=256, warm=65535, cold=65535):
    real_light = int(65535 * (light / 100))
    steps = max(1, real_light // speed)
    if color == 0:
        for i in range(steps + 1):
            w = int(real_light * i / steps)
            warm_LED.duty_u16(w)
            time.sleep(0.01)
    elif color == 1:
        for i in range(steps + 1):
            c = int(real_light * i / steps)
            cold_LED.duty_u16(c)
            time.sleep(0.01)
    elif color == 2:
        for i in range(steps + 1):
            w = int(warm * (i / steps))
            c = int(cold * (i / steps))
            warm_LED.duty_u16(w)
            cold_LED.duty_u16(c)
            time.sleep(0.01)


def Close_LED(color, speed=-256):
    if color == 0:
        for i in range(warm_LED.duty_u16(), -1, speed):
            warm_LED.duty_u16(i)
            time.sleep(0.01)
        warm_LED.duty_u16(0)
    elif color == 1:
        for i in range(cold_LED.duty_u16(), -1, speed):
            cold_LED.duty_u16(i)
            time.sleep(0.01)
        cold_LED.duty_u16(0)
    elif color == 2:
        steps = 100
        for i in range(steps, -1, -1):
            w = int(warm_LED.duty_u16() * i / steps)
            c = int(cold_LED.duty_u16() * i / steps)
            time.sleep(0.01)
        cold_LED.duty_u16(0)
        warm_LED.duty_u16(0)


def Open_LED_F(color, light=80):
    real_light = int(65536 * (light / 100))
    if color == 0:
        warm_LED.duty_u16(real_light)
    elif color == 1:
        cold_LED.duty_u16(real_light)


def Close_LED_F(color):
    if color == 0:
        warm_LED.duty_u16(0)
    elif color == 1:
        cold_LED.duty_u16(0)


def Set_Light(color, light, fast=0):
    real_light = int(65536 * (light / 100))
    if color == 0:
        led = warm_LED
        current_light = warm_LED.duty_u16()
    elif color == 1:
        led = cold_LED
        current_light = cold_LED.duty_u16()
    else:
        return

    if fast:
        led.duty_u16(real_light)
    else:
        step = 1024 if real_light > current_light else -1024
        for i in range(current_light, real_light, step):
            led.duty_u16(i)
            time.sleep(0.01)
        led.duty_u16(real_light)
