"""
Web 服务器模块 — ESP32 HTTP 服务 (精简版)
"""

import json
import LED
import effects
import gc

# ==================== 预编码响应 ====================

HTML = b"""HTTP/1.1 200 OK\r
Content-Type: text/html; charset=utf-8\r
\r
<!DOCTYPE html><html lang=zh><head><meta charset=UTF-8><meta name=viewport content='width=device-width,initial-scale=1'>
<title>LED台灯</title><style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:sans-serif;background:#1a1a2e;color:#eee;padding:10px}
h1{text-align:center;font-size:1.2em;margin:8px 0;color:#e94560}
.c{background:#16213e;border-radius:10px;padding:10px;margin-bottom:8px}
h2{font-size:.9em;margin-bottom:6px;background:#0f3460;color:#fff;padding:4px 8px;border-radius:4px;display:inline-block}
.r{display:flex;align-items:center;gap:6px;margin:4px 0}
.r label{min-width:40px;font-size:.8em}
.r input[type=range]{flex:1;accent-color:#e94560}
.r span{min-width:32px;text-align:right;font-size:.8em}
button{border:none;border-radius:4px;padding:5px 8px;font-size:.75em;cursor:pointer;background:#0f3460;color:#fff;margin:2px}
button.on{background:#e94560}
button.sel{border:2px solid #e94560}
.pw{text-align:center;margin:8px 0}
.pw button{font-size:1em;padding:8px 30px;border-radius:16px}
#presets{display:flex;flex-wrap:wrap;gap:3px}
</style></head><body>
<h1>LED屏幕台灯</h1>
<div class=pw><button id=pwbtn onclick=tp()>关</button></div>
<div class=c><h2>亮度</h2>
<div class=r><label>亮度</label><input type=range id=br min=0 max=100 value=80 oninput=ch()><span id=brv>80%</span></div></div>
<div class=c><h2>色温</h2>
<div class=r><label>暖光</label><input type=range id=wr min=0 max=100 value=100 oninput=ch()><span id=wrv>100%</span></div>
<div class=r><label>冷光</label><input type=range id=cl min=0 max=100 value=100 oninput=ch()><span id=clv>100%</span></div>
<button onclick=sm('warm')>仅暖光</button><button onclick=sm('cold')>仅冷光</button><button onclick=sm('mixed')>混合光</button></div>
<div class=c><h2>RGB颜色</h2>
<div class=r><label>R</label><input type=range id=rr min=0 max=255 value=255 oninput=ch()><span id=rrv>255</span></div>
<div class=r><label>G</label><input type=range id=rg min=0 max=255 value=0 oninput=ch()><span id=rgv>0</span></div>
<div class=r><label>B</label><input type=range id=rb min=0 max=255 value=0 oninput=ch()><span id=rbv>0</span></div>
<input type=color id=cp value=#ff0000 oninput=ccp()><button onclick=sm('rgb')>RGB模式</button></div>
<div class=c><h2>预设</h2><div id=presets></div></div>
<script>
var ps=['静态单色','流水灯','呼吸灯','彩虹循环','彩虹流水','渐变交替','流星','闪烁','双色渐变','派对灯'];
var pb=document.getElementById('presets');
ps.forEach(function(n,i){var b=document.createElement('button');b.textContent=n;b.onclick=function(){sp(i)};pb.appendChild(b)});
var st={power:0,brightness:80,warm:100,cold:100,rgb_r:255,rgb_g:0,rgb_b:0,mode:'off',preset:0};
function tp(){st.power=st.power?0:1;send()}
function ch(){var x=['brightness','warm','cold'];x.forEach(function(k){var e=document.getElementById(k[0]=='b'?'br':k[0]=='w'?'wr':'cl');if(e)document.getElementById((k[0]=='b'?'br':k[0]=='w'?'wr':'cl')+'v').textContent=e.value+'%'});send()}
function ccp(){var v=document.getElementById('cp').value;document.getElementById('rr').value=parseInt(v.substr(1,2),16);document.getElementById('rg').value=parseInt(v.substr(3,2),16);document.getElementById('rb').value=parseInt(v.substr(5,2),16);document.getElementById('rrv').textContent=document.getElementById('rr').value;document.getElementById('rgv').textContent=document.getElementById('rg').value;document.getElementById('rbv').textContent=document.getElementById('rb').value;send()}
function sm(m){st.mode=m;send()}
function sp(i){fetch('/api/set',{method:'POST',body:'preset='+i}).then(function(r){return r.json()}).then(up)}
function send(){var s='brightness='+document.getElementById('br').value;s+='&warm='+document.getElementById('wr').value;s+='&cold='+document.getElementById('cl').value;s+='&rgbR='+document.getElementById('rr').value;s+='&rgbG='+document.getElementById('rg').value;s+='&rgbB='+document.getElementById('rb').value;s+='&mode='+st.mode;s+='&power='+st.power;s+='&preset='+st.preset;fetch('/api/set',{method:'POST',body:s}).then(function(r){return r.json()}).then(up)}
function up(s){if(!s)return;st=s;document.getElementById('br').value=s.brightness;document.getElementById('brv').textContent=s.brightness+'%';document.getElementById('wr').value=s.warm;document.getElementById('wrv').textContent=s.warm+'%';document.getElementById('cl').value=s.cold;document.getElementById('clv').textContent=s.cold+'%';document.getElementById('rr').value=s.rgb_r;document.getElementById('rrv').textContent=s.rgb_r;document.getElementById('rg').value=s.rgb_g;document.getElementById('rgv').textContent=s.rgb_g;document.getElementById('rb').value=s.rgb_b;document.getElementById('rbv').textContent=s.rgb_b;document.getElementById('cp').value='#'+s.rgb_r.toString(16).padStart(2,'0')+s.rgb_g.toString(16).padStart(2,'0')+s.rgb_b.toString(16).padStart(2,'0');var p=document.getElementById('pwbtn');p.textContent=s.power?'\\u{5f00}':'\\u{5173}';p.className=s.power?'on':'';var bs=pb.children;for(var i=0;i<bs.length;i++)bs[i].className=(i==s.preset)?'sel':''}
fetch('/api/state').then(function(r){return r.json()}).then(up)
</script></body></html>"""

HDR_200 = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\n"
HDR_404 = b"HTTP/1.1 404 Not Found\r\nContent-Type: application/json\r\n\r\n"

# ==================== 辅助函数 ====================

def _parse(s):
    d = {}
    if s:
        for p in s.split("&"):
            if "=" in p:
                k, v = p.split("=", 1)
                d[k.strip()] = v.strip()
    return d


def _json_resp(data):
    body = json.dumps(data)
    return HDR_200 + b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body.encode()


def get_state():
    s = LED.state
    return {
        "power": 1 if s.power else 0,
        "brightness": s.brightness,
        "warm": s.warm_level,
        "cold": s.cold_level,
        "rgb_r": s.rgb_r,
        "rgb_g": s.rgb_g,
        "rgb_b": s.rgb_b,
        "mode": s.mode,
        "preset": s.preset_index,
    }


def _apply(params):
    s = LED.state
    if "power" in params:
        s.power = params["power"] in ("1", "true", "True")
    if "brightness" in params:
        s.brightness = max(0, min(100, int(params["brightness"])))
    if "warm" in params:
        s.warm_level = max(0, min(100, int(params["warm"])))
    if "cold" in params:
        s.cold_level = max(0, min(100, int(params["cold"])))
    if "rgbR" in params:
        s.rgb_r = max(0, min(255, int(params["rgbR"])))
    if "rgbG" in params:
        s.rgb_g = max(0, min(255, int(params["rgbG"])))
    if "rgbB" in params:
        s.rgb_b = max(0, min(255, int(params["rgbB"])))
    if "mode" in params:
        s.mode = params["mode"]
    if "preset" in params:
        s.mode = "rgb"
        s.power = True
        s.apply_preset(int(params["preset"]))
    s.set_rgb(s.rgb_r, s.rgb_g, s.rgb_b)


# ==================== HTTP 处理 ====================

async def _client(reader, writer):
    try:
        req = await reader.read(512)
        if not req:
            return
        req = req.decode("utf-8", "ignore")
        gc.collect()

        lines = req.split("\r\n")
        if not lines:
            return

        parts = lines[0].split(" ")
        if len(parts) < 2:
            return
        method = parts[0]
        path = parts[1]

        resp = None

        if path == "/" or path == "/index.html":
            resp = HTML
        elif path == "/api/state":
            if method == "GET":
                resp = _json_resp(get_state())
            elif method == "POST":
                body = req.split("\r\n\r\n", 1)[1] if "\r\n\r\n" in req else ""
                _apply(_parse(body))
                resp = _json_resp(get_state())
        elif path == "/api/set":
            if method == "POST":
                body = req.split("\r\n\r\n", 1)[1] if "\r\n\r\n" in req else ""
                _apply(_parse(body))
                resp = _json_resp(get_state())

        if resp is None:
            resp = HDR_404 + b'{"error":"not found"}'

        await writer.awrite(resp)
        gc.collect()
    except Exception as e:
        print("HTTP ERR:", e)
    finally:
        try:
            await writer.aclose()
        except Exception:
            pass


async def start_server(host="0.0.0.0", port=80):
    import uasyncio
    server = await uasyncio.start_server(_client, host, port, backlog=1)
    print("Web server: %s:%s" % (host, port))
    return server
