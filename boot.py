"""
boot.py — ESP32 LED 屏幕台灯固件入口
集成三大控制通道：触摸按键 + Web 服务器 + 蓝牙 BLE
使用 uasyncio 并发调度
"""

import uasyncio
import time
import network
from machine import Pin

import LED
import effects
import web_server
import ble_control

# ==================== WiFi 连接 ====================
WIFI_SSID = "ESP32-APS"
WIFI_PASS = "33336666"


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print(f"连接 WiFi: {WIFI_SSID}...")
        wlan.connect(WIFI_SSID, WIFI_PASS)
        for _ in range(30):
            if wlan.isconnected():
                break
            time.sleep(0.5)
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f"WiFi 已连接, IP: {ip}")
        return ip
    else:
        print("WiFi 连接失败，继续运行（Web 不可用）")
        return None

# ==================== 硬件初始状态 ====================
LED.cold_LED.duty_u16(0)
LED.warm_LED.duty_u16(0)
for i in range(LED.NUM_LEDS):
    LED.neo[i] = (0, 0, 0)
LED.neo.write()

# ==================== 触摸按键 ====================
last_time = 0
touch_flag = False
touch_state = 0


def touch_handler(pin):
    global last_time, touch_flag, touch_state
    now = time.ticks_ms()
    if time.ticks_diff(now, last_time) < 200:
        return
    last_time = now
    touch_flag = True
    touch_state += 1


LED.switch.irq(trigger=Pin.IRQ_FALLING, handler=touch_handler)


async def touch_monitor():
    """异步任务：监控触摸标志并切换灯光模式"""
    global touch_flag, touch_state

    while True:
        if touch_flag:
            touch_flag = False
            s = LED.state

            if touch_state == 1:
                s.mode = "warm"
                s.power = True
                s.brightness = 80
                s.warm_level = 100
                s.cold_level = 0
                print("TOUCH: 暖光模式")

            elif touch_state == 2:
                s.mode = "cold"
                s.power = True
                s.brightness = 80
                s.warm_level = 0
                s.cold_level = 100
                print("TOUCH: 冷光模式")

            elif touch_state == 3:
                s.mode = "mixed"
                s.power = True
                s.brightness = 80
                s.warm_level = 100
                s.cold_level = 100
                print("TOUCH: 混合光模式")

            elif touch_state == 4:
                s.mode = "rgb"
                s.power = True
                s.apply_preset(0)
                s.set_rgb(255, 0, 0)
                print("TOUCH: RGB 模式")

            else:
                s.mode = "off"
                s.power = False
                touch_state = 0
                print("TOUCH: 全部关闭")

        await uasyncio.sleep_ms(50)


# ==================== LED 状态更新循环 ====================
async def led_update_loop():
    """持续更新 PWM 输出和 RGB 效果"""
    while True:
        await LED.state.update()


# ==================== 主入口 ====================
async def main():
    print("LED 屏幕台灯启动中...")

    # 连接 WiFi
    ip = connect_wifi()

    # 初始化 BLE
    try:
        ble_control.init_ble()
    except Exception as e:
        print(f"BLE 初始化失败: {e}")

    # 启动 Web 服务器
    try:
        await web_server.start_server()
    except Exception as e:
        print(f"Web 服务器启动失败: {e}")

    # 创建并发任务
    tasks = [
        uasyncio.create_task(led_update_loop()),
        uasyncio.create_task(touch_monitor()),
    ]

    # BLE 同步任务（如果 BLE 初始化成功）
    try:
        tasks.append(uasyncio.create_task(ble_control.sync_characteristics()))
    except Exception:
        pass

    print("所有服务已启动")
    if ip:
        print(f"  - Web 地址：http://{ip}/")
    else:
        print("  - Web 地址：WiFi 未连接，不可用")
    print("  - 触摸按键：短按切换模式")
    print("  - 蓝牙名称：LED-Desk-Lamp")

    await uasyncio.gather(*tasks)


try:
    uasyncio.run(main())
except KeyboardInterrupt:
    print("关机中...")
    LED.cold_LED.duty_u16(0)
    LED.warm_LED.duty_u16(0)
    for i in range(LED.NUM_LEDS):
        LED.neo[i] = (0, 0, 0)
    LED.neo.write()
