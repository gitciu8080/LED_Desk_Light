# LED 屏幕台灯

基于 ESP32 的 MicroPython 屏幕台灯固件，支持 **冷暖双色温 PWM 调光**、**WS2811 RGB 灯带**，通过 **触摸 / Web / 蓝牙 BLE** 三通道控制。

<img src="https://img.shields.io/badge/platform-ESP32-blue" alt="ESP32">
<img src="https://img.shields.io/badge/language-MicroPython-green" alt="MicroPython">
<img src="https://img.shields.io/badge/BLE-LED--Desk--Lamp-orange" alt="BLE">

## 功能特性

- **触摸按键** — TP233 短按循环切换 5 种灯光模式（暖光 / 冷光 / 混合光 / RGB / 全关）
- **Web 网页** — 局域网 HTTP 访问，内嵌单页控制面板（亮度、色温、RGB 色盘、10 种预设）
- **蓝牙 BLE** — 手机 / 电脑直连 `LED-Desk-Lamp`，读写 GATT 特征值实时控制
- **10 种 RGB 效果** — 静态、流水灯、呼吸灯、彩虹循环、流星、派对灯等

## 硬件引脚

| 功能 | GPIO | 说明 |
|------|------|------|
| 暖光 LED | GPIO10 | PWM 调光，1000Hz |
| 冷光 LED | GPIO20 | PWM 调光，1000Hz |
| WS2811 RGB | GPIO8 | 12 芯片 × 3 灯珠 = 36 灯珠 |
| 触摸传感器 | GPIO9 | TP233，内部上拉，下降沿触发 |

## 项目结构

```
├── boot.py          # 固件入口，asyncio 事件循环，WiFi 连接
├── LED.py           # 核心驱动 + LEDState 统一状态管理
├── effects.py       # 10 种 RGB 预设效果
├── web_server.py    # HTTP 服务器 + 内嵌精简网页 + REST API
├── ble_control.py   # BLE 蓝牙外设（GATT 服务）
├── index.html       # 完整版液态玻璃主题 Web 界面（开发/预览用）
├── Port.md          # 引脚映射速查
└── README.md        # 本文件
```

## 灯光模式（触摸切换）

| 次数 | 模式 | 说明 |
|------|------|------|
| 1 | 暖光 | 仅暖光，亮度 80% |
| 2 | 冷光 | 仅冷光，亮度 80% |
| 3 | 混合光 | 暖 + 冷，亮度 80% |
| 4 | RGB | 静态红色 |
| 5+ | 全关 | 回到初始状态 |

## Web API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 内嵌控制面板网页 |
| GET | `/api/state` | 返回当前状态 JSON |
| POST | `/api/state` | 批量更新状态（JSON body 或 form） |
| POST | `/api/set` | 更新状态（form 参数） |

支持的 POST 参数：`power`, `brightness`, `warm`, `cold`, `rgbR`, `rgbG`, `rgbB`, `mode`, `preset`

## BLE 特征值

服务 UUID：`12345678-1234-5678-1234-56789abcdef0`

| 特征值 | UUID (后缀) | 格式 | 说明 |
|--------|-------------|------|------|
| Power | `...def1` | uint8 (0/1) | 总开关 |
| Brightness | `...def2` | uint8 (0–100) | 亮度 |
| Warm | `...def3` | uint8 (0–100) | 暖光强度 |
| Cold | `...def4` | uint8 (0–100) | 冷光强度 |
| RGB | `...def5` | 3 bytes (R,G,B) | RGB 颜色 |
| Preset | `...def6` | uint8 (0–9) | 预设编号 |

所有特征值 Read + Write，写操作即时生效。

## 部署

### 前置条件

- ESP32 已烧录 MicroPython 固件（需 `uasyncio`、`bluetooth`、`neopixel`）
- 串口工具：[mpremote](https://pypi.org/project/mpremote/)

### 上传文件

```bash
mpremote connect COMx fs cp boot.py :boot.py fs cp LED.py :LED.py fs cp effects.py :effects.py fs cp web_server.py :web_server.py fs cp ble_control.py :ble_control.py
```

### REPL / 重启

```bash
mpremote connect COMx repl
mpremote connect COMx reset
```

## 架构

三者通过 `LED.state`（LEDState 单例）实现状态同步，任一通道修改后其他通道即时可见。

```
boot.py              # asyncio 入口，启动四大任务
├── LED.py           # 核心驱动 + LEDState 统一状态管理
├── effects.py       # 10 种 RGB 预设效果
├── web_server.py    # HTTP 服务器 + 嵌入式网页 + REST API
└── ble_control.py   # BLE 外设（GATT 服务）
```

asyncio 并发任务：

| 任务 | 周期 | 说明 |
|------|------|------|
| `led_update_loop()` | 20ms | 更新 PWM 输出 + 渲染 RGB 效果 |
| `touch_monitor()` | 50ms | 检查触摸标志并切换模式 |
| `sync_characteristics()` | 1s | 同步 LED.state 到 BLE 特征值 |
| `start_server()` | 事件驱动 | HTTP 异步服务器 |

