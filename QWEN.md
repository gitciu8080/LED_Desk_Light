# LED屏幕台灯 (LED Screen Desk Lamp)

基于 ESP32 的 MicroPython 屏幕台灯固件项目，支持冷暖双色温 PWM 调光、WS2811 RGB 灯带、**触摸/Web/蓝牙三通道控制**。

## 项目概述

- **平台:** ESP32 (MicroPython 1.20+, 需支持 `uasyncio` 和 `bluetooth`)
- **入口文件:** `boot.py` — ESP32 上电自动执行，启动 asyncio 事件循环
- **控制方式:**
  - **触摸按键** — TP233 短按循环切换灯光模式
  - **Web 网页** — 局域网 HTTP 访问，滑块/色盘/预设全参数控制
  - **蓝牙 BLE** — 手机/电脑连接 `LED-Desk-Lamp` 直接读写特征值
- **灯珠类型:** 暖光 LED (PWM)、冷光 LED (PWM)、WS2811 RGB (12 芯片 × 3 灯珠/芯片 = 36 灯珠)

## 架构

```
boot.py              # asyncio 入口，启动三大任务
├── LED.py           # 核心驱动 + LEDState 统一状态管理
├── effects.py       # 10 种 RGB 预设效果
├── web_server.py    # HTTP 服务器 + 嵌入式网页 + REST API
├── ble_control.py   # BLE 外设（GATT 服务）
└── Port.md          # 引脚映射
```

三者通过 `LED.state` (LEDState 单例) 实现状态同步，任一通道修改后其他通道即时可见。

---

## 硬件引脚映射

| 功能 | GPIO | 说明 |
|------|------|------|
| 暖光 LED | GPIO10 | PWM 调光，频率 1000Hz |
| 冷光 LED | GPIO20 | PWM 调光，频率 1000Hz |
| WS2811 RGB | GPIO8 | 12 个芯片，每芯片控制 3 个灯珠，共 36 颗灯珠 |
| 触摸传感器 | GPIO9 | TP233，内部上拉，下降沿触发 |

详见 `Port.md`。

---

## 灯光模式（触摸切换）

| 触摸次数 | 模式 | 说明 |
|----------|------|------|
| 1 | 暖光 | 仅暖光，亮度 80% |
| 2 | 冷光 | 仅冷光，亮度 80% |
| 3 | 混合光 | 暖光 + 冷光，亮度 80% |
| 4 | RGB | WS2811 静态红色 |
| 5+ | 全关 | 重置，回到初始状态 |

触摸防抖：200ms。

---

## 模块文档

### LED.py — 核心驱动

**LEDState 类（全局单例 `LED.state`）：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `power` | bool | 总开关 |
| `brightness` | int (0–100) | 亮度百分比 |
| `warm_level` | int (0–100) | 暖光强度 |
| `cold_level` | int (0–100) | 冷光强度 |
| `rgb_r/g/b` | int (0–255) | RGB 颜色 |
| `preset_index` | int (0–9) | 当前 RGB 预设编号 |
| `mode` | str | "off"/"warm"/"cold"/"mixed"/"rgb" |

**LEDState 方法：**

| 方法 | 说明 |
|------|------|
| `apply_preset(index)` | 切换 RGB 预设效果 |
| `set_rgb(r, g, b)` | 设置 RGB 颜色并同步到当前效果 |
| `update_pwm()` | 将亮度/色温写入 PWM 硬件 |
| `async update()` | 每帧调用：更新 PWM + 渲染 RGB 效果 |

**底层函数（保留兼容）：** `Open_LED()`, `Close_LED()`, `Open_LED_F()`, `Close_LED_F()`, `Set_Light()`, `RGB()`, `breathe()`

**全局对象：** `cold_LED` (PWM), `warm_LED` (PWM), `switch` (触摸 Pin), `neo` (NeoPixel, 12 芯片)

### effects.py — 10 种 RGB 预设

所有效果类通过 `update(np, dt_ms)` 驱动帧更新：

| # | 类名 | 效果 | 可调参数 |
|---|------|------|----------|
| 1 | `EffectStatic` | 静态单色 | RGB 颜色 |
| 2 | `EffectChase` | 流水灯 | 颜色、速度 |
| 3 | `EffectBreathe` | 呼吸灯 | 颜色、周期 |
| 4 | `EffectRainbow` | 彩虹循环 | 速度 |
| 5 | `EffectRainbowRunning` | 彩虹流水 | 速度 |
| 6 | `EffectColorWipe` | 渐变交替 | 颜色、速度 |
| 7 | `EffectMeteor` | 流星 | 颜色、速度、拖尾长度 |
| 8 | `EffectStrobe` | 闪烁 | 颜色、间隔 |
| 9 | `EffectTwoColorGradient` | 双色渐变 | 颜色1、颜色2、速度 |
| 10 | `EffectParty` | 派对灯 | 切换间隔 |

`EFFECTS` 列表提供名称和类的注册表。

### web_server.py — Web 服务

- **协议:** HTTP/1.1，基于 `uasyncio.start_server`
- **网页:** 嵌入式 HTML/CSS/JS 单页应用，无需外部资源

**网页控件：**
- 电源开关按钮
- 亮度滑块 (0–100%)
- 冷暖色温双滑块 (0–100%)
- 模式切换按钮（仅暖/仅冷/混合光/RGB）
- RGB 颜色（R/G/B 滑块 + HTML 色盘）
- 10 种预设效果按钮（高亮当前选中）

**API 端点：**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/state` | 返回当前状态 JSON |
| POST | `/api/state` | 批量更新状态（JSON body 或 form） |
| POST | `/api/set` | 更新状态（form 参数） |

支持的 POST 参数：`power`, `brightness`, `warm`, `cold`, `rgbR`, `rgbG`, `rgbB`, `mode`, `preset`

### ble_control.py — 蓝牙控制

- **设备名称:** `LED-Desk-Lamp`
- **服务 UUID:** `12345678-1234-5678-1234-56789abcdef0`

**GATT 特征值：**

| 特征值 | UUID (后缀) | 格式 | 说明 |
|--------|-------------|------|------|
| Power | `...def1` | uint8 (0/1) | 总开关 |
| Brightness | `...def2` | uint8 (0–100) | 亮度 |
| Warm | `...def3` | uint8 (0–100) | 暖光强度 |
| Cold | `...def4` | uint8 (0–100) | 冷光强度 |
| RGB | `...def5` | 3 bytes (R,G,B) | RGB 颜色 |
| Preset | `...def6` | uint8 (0–9) | 预设编号 |

所有特征值为 Read + Write。写操作即时生效，自动同步到 Web 和触摸状态。

**函数：** `init_ble()` 初始化并开始广播，`async sync_characteristics()` 定期将 LED.state 同步到特征值。

### boot.py — 固件入口

使用 `uasyncio` 并发运行：

| 任务 | 说明 |
|------|------|
| `led_update_loop()` | 20ms 周期更新 PWM 和 RGB 效果 |
| `touch_monitor()` | 50ms 周期检查触摸标志并切换模式 |
| `ble_control.sync_characteristics()` | 1s 周期同步状态到 BLE 特征值 |
| `web_server.start_server()` | HTTP 异步服务器（asyncio server） |

---

## 部署与开发

### 前置条件

- MicroPython 固件已烧录到 ESP32（需 `uasyncio`、`bluetooth`、`neopixel`）
- 串口工具: `mpremote`

### 上传文件

```bash
mpremote connect COMx fs cp boot.py :boot.py
mpremote connect COMx fs cp LED.py :LED.py
mpremote connect COMx fs cp effects.py :effects.py
mpremote connect COMx fs cp web_server.py :web_server.py
mpremote connect COMx fs cp ble_control.py :ble_control.py
mpremote connect COMx fs cp Port.md :Port.md
```

### 一键上传

```bash
mpremote connect COMx fs cp boot.py :boot.py fs cp LED.py :LED.py fs cp effects.py :effects.py fs cp web_server.py :web_server.py fs cp ble_control.py :ble_control.py
```

### 进入 REPL / 重启

```bash
mpremote connect COMx repl
mpremote connect COMx reset
```

### 文件结构

```
LED屏幕台灯/
├── boot.py          # 固件入口，asyncio 事件循环
├── LED.py           # 核心驱动 + LEDState 状态管理
├── effects.py       # 10 种 RGB 预设效果
├── web_server.py    # HTTP 服务器 + 嵌入式网页
├── ble_control.py   # BLE 蓝牙控制
├── Port.md          # 引脚映射参考
└── QWEN.md          # 项目说明（本文件）
```

---

## 开发约定

- **状态同步：** 所有控制通道通过 `LED.state` 单例读写，不直接操作 PWM
- **异步：** 使用 `uasyncio` 协程，避免阻塞式 `time.sleep()`；底层驱动保留同步版本供 REPL 调试
- **命名：** 类用 PascalCase（`LEDState`），函数/变量用 snake_case（`set_rgb`, `cold_LED`），模块级常量用大写（`NUM_LEDS`）
- **效果系统：** 每个效果是独立类，通过 `update(np, dt_ms)` 接口驱动，支持 `set_color()` 动态调色
- **Web 页面：** 嵌入式单文件，无外部依赖，前端通过 `/api/state` 轮询获取初始状态，滑动条通过 `/api/set` 实时同步
- MicroPython 标准库：`machine`、`neopixel`、`network`、`socket`、`time`、`uasyncio`、`bluetooth`、`json`、`struct`
