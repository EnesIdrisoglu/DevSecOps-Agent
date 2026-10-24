"""DevSecOps Agent için bağımlılıksız web chat arayüzü."""

from __future__ import annotations

import json
import argparse
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ..agents.supervisor import SupervisorAgent
from ..tools.database import DEFAULT_DB_PATH
from ..database.seed import seed


HOST = "127.0.0.1"
PORT = 8080


PAGE = """<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DevSecOps Copilot</title>
  <style>
    :root { color-scheme: dark; --bg:#08111f; --panel:#101d31; --line:#223454; --muted:#93a4be; --accent:#59d3b4; }
    * { box-sizing:border-box } body { margin:0; font-family:Inter,ui-sans-serif,system-ui,sans-serif; background:radial-gradient(circle at 80% 0,#163357 0,#08111f 42%); color:#edf4ff; min-height:100vh }
    .shell { width:min(1100px,100%); margin:auto; padding:28px 18px; display:grid; grid-template-columns:270px 1fr; gap:18px; min-height:100vh }
    aside,.chat { background:rgba(16,29,49,.9); border:1px solid var(--line); border-radius:18px; box-shadow:0 20px 60px #0004 }
    aside { padding:22px; display:flex; flex-direction:column } .brand { display:flex; gap:12px; align-items:center; margin-bottom:35px }
    .logo { width:40px;height:40px;border-radius:12px;background:linear-gradient(135deg,#59d3b4,#4c8dff); display:grid;place-items:center;color:#06121d;font-weight:900 }
    h1 { font-size:19px;margin:0 } .eyebrow { color:var(--accent);font-size:11px;letter-spacing:.14em;text-transform:uppercase;font-weight:700 }
    .side-title { color:var(--muted);font-size:12px;margin:0 0 10px } .suggestion { width:100%; text-align:left; border:1px solid var(--line); background:#0c182a;color:#d9e7fa;padding:12px;border-radius:11px;margin:5px 0;cursor:pointer }
    .suggestion:hover { border-color:var(--accent) } .safe { margin-top:auto;color:var(--muted);font-size:12px;line-height:1.6;border-top:1px solid var(--line);padding-top:16px }
    .chat { display:flex; flex-direction:column; overflow:hidden; min-height:650px } .top { padding:22px 25px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center }
    .status { color:var(--accent);font-size:12px } .messages { flex:1;padding:25px;overflow:auto;display:flex;flex-direction:column;gap:16px }
    .message { max-width:82%;padding:14px 16px;border-radius:14px;line-height:1.55;white-space:pre-wrap;font-size:14px } .bot { background:#172943;border:1px solid #284363;align-self:flex-start }.user { background:#237e77;align-self:flex-end }
    .empty { margin:auto;text-align:center;color:var(--muted);max-width:430px }.empty h2 { color:#edf4ff;font-size:25px;margin:10px 0 }.empty p { line-height:1.6 }
    form { display:flex;gap:10px;padding:17px;border-top:1px solid var(--line);background:#0c182a } input { flex:1;background:#101f35;border:1px solid #2b4367;border-radius:12px;color:#fff;padding:14px;font-size:14px;outline:none } input:focus { border-color:var(--accent) }
    button.send { border:0;border-radius:12px;background:var(--accent);color:#06121d;font-weight:800;padding:0 20px;cursor:pointer } button:disabled { opacity:.55;cursor:wait }
    @media(max-width:760px) { .shell { display:block;padding:10px } aside { margin-bottom:10px } .safe { display:none } .chat { min-height:calc(100vh - 180px) } }
  </style>
</head>
<body><main class="shell">
  <aside><div class="brand"><div class="logo">✓</div><div><div class="eyebrow">Security intelligence</div><h1>DevSecOps Copilot</h1></div></div>
    <p class="side-title">Hızlı sorular</p>
    <button class="suggestion">payments projesi release'e uygun mu?</button>
    <button class="suggestion">payments son job neden başarısız?</button>
    <button class="suggestion">payments karne durumu nedir?</button>
    <p class="safe">Salt-okunur analiz<br>Release kararları otomatik değiştirilmez.<br>Yanıtlar platform kanıtlarına dayanır.</p>
  </aside>
  <section class="chat"><header class="top"><div><div class="eyebrow">AI assistant</div><strong>Güvenlik operasyonlarınıza sorun</strong></div><span class="status">● çevrimiçi</span></header>
    <div id="messages" class="messages"><div class="empty" id="empty"><div class="logo" style="margin:auto">✦</div><h2>Bugün neyi inceleyelim?</h2><p>Tarama sonuçları, release riskleri, karne hedefleri veya başarısız job'lar hakkında soru sorun.</p></div></div>
    <form id="form"><input id="question" autocomplete="off" placeholder="Örn. payments release'e uygun mu?"/><button class="send" type="submit">Gönder</button></form>
  </section>
</main>
<script>
const messages=document.querySelector('#messages'), empty=document.querySelector('#empty'), input=document.querySelector('#question'), form=document.querySelector('#form'), send=document.querySelector('.send');
document.querySelectorAll('.suggestion').forEach(b=>b.onclick=()=>{input.value=b.textContent;form.requestSubmit()});
function add(text,kind){ if(empty) empty.remove(); const el=document.createElement('div'); el.className='message '+kind; el.textContent=text; messages.appendChild(el); messages.scrollTop=messages.scrollHeight; }
const sessionId=localStorage.getItem('devsecops_session')||crypto.randomUUID();localStorage.setItem('devsecops_session',sessionId);
form.onsubmit=async e=>{e.preventDefault(); const q=input.value.trim();if(!q)return;add(q,'user');input.value='';send.disabled=true;send.textContent='...';try{const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,session_id:sessionId})});const d=await r.json();add(d.answer||d.error||'Yanıt alınamadı.','bot')}catch(err){add('Sunucuya bağlanılamadı. Web uygulamasının çalıştığını kontrol edin.','bot')}finally{send.disabled=false;send.textContent='Gönder';input.focus()}};
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    agent = SupervisorAgent()

    def _send(self, payload: str, content_type: str = "text/html; charset=utf-8", status: int = 200) -> None:
        data = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            self._send(PAGE)
        elif self.path == "/health":
            self._send(json.dumps({"status": "ok"}), "application/json")
        else:
            self._send("Bulunamadı", status=404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/chat":
            self._send(json.dumps({"error": "Endpoint bulunamadı."}), "application/json", 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length))
            question = str(body.get("question", "")).strip()
            session_id = str(body.get("session_id", "default"))
            if not question:
                raise ValueError("Soru boş olamaz.")
            self._send(json.dumps({"answer": self.agent.answer(question, thread_id=session_id)}, ensure_ascii=False), "application/json")
        except (ValueError, json.JSONDecodeError) as exc:
            self._send(json.dumps({"error": str(exc)}, ensure_ascii=False), "application/json", 400)
        except Exception as exc:
            self._send(json.dumps({"error": f"Agent akışı çalıştırılamadı: {type(exc).__name__}: {exc}"}, ensure_ascii=False), "application/json", 502)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[web] {self.address_string()} - {format % args}")


def run(host: str = HOST, port: int = PORT) -> None:
    if not DEFAULT_DB_PATH.exists():
        seed(DEFAULT_DB_PATH)
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"DevSecOps Copilot: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSunucu durduruldu.")
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DevSecOps Copilot web sunucusu")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    try:
        run(args.host, args.port)
    except OSError as exc:
        if getattr(exc, "errno", None) == 48:
            print(f"{args.host}:{args.port} portu kullanımda. --port ile farklı bir port seçin.")
        raise
