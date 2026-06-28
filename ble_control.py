"""
蓝牙 BLE 控制模块 — ESP32 BLE 外设
广播名称: LED-Desk-Lamp
提供亮度、色温、RGB、预设等特征值供手机/电脑连接控制
"""

import bluetooth
import struct
import time
import LED
import effects

# ==================== UUID 定义 ====================
_SERVICE_UUID = bluetooth.UUID(0x180A)  # Device Information
_CUSTOM_SERVICE_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef0")

# 特征值 UUID
_CHAR_POWER = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef1")
_CHAR_BRIGHTNESS = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef2")
_CHAR_WARM = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef3")
_CHAR_COLD = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef4")
_CHAR_RGB = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef5")
_CHAR_PRESET = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef6")

_FLAG_RW = bluetooth.FLAG_READ | bluetooth.FLAG_WRITE | bluetooth.FLAG_WRITE_NO_RESPONSE
_FLAG_NOTIFY = bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY

# 特征值句柄（注册后赋值）
_HANDLES = {}

_ble = None


def _ble_irq(event, data):
    global _HANDLES
    if event == 1:  # _IRQ_CENTRAL_CONNECT
        print("BLE: 已连接")
    elif event == 2:  # _IRQ_CENTRAL_DISCONNECT
        print("BLE: 已断开，重新广播")
        _start_advertising()
    elif event == 3:  # _IRQ_GATTS_WRITE
        conn_handle, attr_handle = data
        value = _ble.gatts_read(attr_handle)
        _on_write(attr_handle, value)


def _on_write(handle, value):
    s = LED.state
    if handle == _HANDLES["power"]:
        s.power = bool(value[0])
    elif handle == _HANDLES["brightness"]:
        s.brightness = max(0, min(100, value[0]))
    elif handle == _HANDLES["warm"]:
        s.warm_level = max(0, min(100, value[0]))
    elif handle == _HANDLES["cold"]:
        s.cold_level = max(0, min(100, value[0]))
    elif handle == _HANDLES["rgb"]:
        if len(value) >= 3:
            s.set_rgb(value[0], value[1], value[2])
    elif handle == _HANDLES["preset"]:
        idx = value[0]
        if 0 <= idx < len(effects.EFFECTS):
            s.mode = "rgb"
            s.power = True
            s.apply_preset(idx)


def _start_advertising():
    _ble.gap_advertise(100000, adv_data=bytearray(
        b"\x02\x01\x06"  # 标志：通用发现 + BR/EDR 不支持
        b"\x0e\x09LED-Desk-Lamp"  # 设备名
    ))


def init_ble():
    """初始化 BLE 并开始广播"""
    global _ble, _HANDLES

    _ble = bluetooth.BLE()
    if not _ble.active():
        _ble.active(True)

    _ble.irq(_ble_irq)

    # 注册服务
    service = (
        _CUSTOM_SERVICE_UUID,
        (
            (_CHAR_POWER, _FLAG_RW),
            (_CHAR_BRIGHTNESS, _FLAG_RW),
            (_CHAR_WARM, _FLAG_RW),
            (_CHAR_COLD, _FLAG_RW),
            (_CHAR_RGB, _FLAG_RW),
            (_CHAR_PRESET, _FLAG_RW),
        ),
    )
    handles = _ble.gatts_register_services((service,))
    _HANDLES = {
        "power": handles[0][0],
        "brightness": handles[0][1],
        "warm": handles[0][2],
        "cold": handles[0][3],
        "rgb": handles[0][4],
        "preset": handles[0][5],
    }

    # 写入初始值
    _ble.gatts_write(_HANDLES["power"], b"\x00")
    _ble.gatts_write(_HANDLES["brightness"], b"\x50")  # 80
    _ble.gatts_write(_HANDLES["warm"], b"\x64")  # 100
    _ble.gatts_write(_HANDLES["cold"], b"\x64")  # 100
    _ble.gatts_write(_HANDLES["rgb"], b"\xff\x00\x00")
    _ble.gatts_write(_HANDLES["preset"], b"\x00")

    _start_advertising()
    print("BLE: 广播已启动 (LED-Desk-Lamp)")


async def sync_characteristics():
    """异步任务：定期将 LED.state 同步到 BLE 特征值"""
    import uasyncio
    while True:
        if _ble and _ble.active() and _HANDLES:
            s = LED.state
            try:
                _ble.gatts_write(_HANDLES["power"], bytes([1 if s.power else 0]))
                _ble.gatts_write(_HANDLES["brightness"], bytes([s.brightness]))
                _ble.gatts_write(_HANDLES["warm"], bytes([s.warm_level]))
                _ble.gatts_write(_HANDLES["cold"], bytes([s.cold_level]))
                _ble.gatts_write(_HANDLES["rgb"], bytes([s.rgb_r, s.rgb_g, s.rgb_b]))
                _ble.gatts_write(_HANDLES["preset"], bytes([s.preset_index]))
            except Exception:
                pass
        await uasyncio.sleep_ms(1000)
