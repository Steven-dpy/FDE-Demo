# -*- coding: utf-8 -*-
"""Nook · HTTP 服务（零依赖，Python 标准库实现）

路由
  GET  /                     店铺页
  GET  /<静态文件>             web/ 目录
  GET  /api/config            店铺与 Nook 配置（店主可改的部分）
  GET  /api/products          商品列表 ?lang=&category=&q=&limit=
  GET  /api/products/<sku>    商品详情
  POST /api/chat              {session_id, message, lang} → 回复

生产环境把 api_* 换成 FastAPI 路由即可 —— 业务逻辑（catalog / concierge）
完全不用动，这个文件只负责 HTTP 与序列化。
"""
from __future__ import annotations

import json
import mimetypes
import pathlib
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import money
from catalog import get_catalog
from concierge import Session

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB = ROOT / "web"

_LOCK = threading.Lock()
_SESSIONS: dict[str, Session] = {}

# ---------------------------------------------------------------- 店主可配置项
CONFIG = {
    "brand": {
        "name": "Fern & Oak",
        "tagline": {"zh": "为真实生活做的家具", "en": "Furniture made for actual living"},
    },
    "widget": {
        "launcher": {"zh": "问问 Nook", "en": "Ask Nook"},
        "title": {"zh": "Nook · 导购助手", "en": "Nook · Shopping Concierge"},
        "opening": {
            "zh": "你好，我是 Nook。你不用想好要买什么——告诉我你想在哪个房间、"
                  "想解决什么事就行，比如「我想弄个能窝着看书的地方」。",
            "en": "Hi, I'm Nook. You don't need to know what you want yet — just tell me "
                  "the room and what you're trying to solve. Try: \"a corner to curl up and read\".",
        },
        "quick_replies": {
            "zh": ["我想弄个能窝着看书的地方", "客厅想换套沙发", "小户型怎么选收纳"],
            "en": ["a corner to curl up and read", "a new sofa for the living room",
                   "storage ideas for a small flat"],
        },
        "accent": "#2f6f4e",
    },
    "fx": {"usd_cny": money.USD_CNY,
           "note": {"zh": f"参考汇率 1 美元 ≈ {money.USD_CNY:.2f} 元人民币，实际以结算为准",
                    "en": f"Reference rate: 1 USD ≈ {money.USD_CNY:.2f} CNY. Final amount at checkout."}},
}


# ---------------------------------------------------------------- 序列化
def slim(p: dict, lang: str) -> dict:
    return {
        "sku": p["sku"],
        "name": p["name"][lang],
        "name_en": p["name"]["en"],
        "category": p["category"],
        "category_label": p["category_zh"] if lang == "zh" else p["category_en"],
        "description": p["description"][lang],
        "price": p["price"],
        "price_display": money.fmt(p["price"], lang),
        "price_local": money.fmt_short(p["price"], lang),
        "image": p["image"],
        "dimensions": p["dimensions"],
        "rating": p["rating"],
        "review_count": p["review_count"],
        "stock": p["stock"],
        "lead_time_days": p["lead_time_days"],
        "style": p["style"],
        "material": p["material"],
        "color": p["color"],
        "tags": p["tags"],
    }


def _session(sid: str, lang: str) -> Session:
    with _LOCK:
        s = _SESSIONS.get(sid)
        if s is None or s.lang != lang:
            s = Session(lang=lang)
            _SESSIONS[sid] = s
        return s


# ---------------------------------------------------------------- HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "Nook/0.1"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):        # 安静点
        pass

    # ---------- 工具
    def _send(self, body: bytes, ctype: str, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, obj, code: int = 200):
        self._send(json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8", code)

    @staticmethod
    def _lang(qs) -> str:
        return "en" if (qs.get("lang", ["zh"])[0] == "en") else "zh"

    # ---------- GET
    def do_GET(self):
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        if u.path == "/api/config":
            return self._json(CONFIG)
        if u.path == "/api/products":
            return self.api_products(qs)
        if u.path.startswith("/api/products/"):
            return self.api_product(u.path.rsplit("/", 1)[-1], self._lang(qs))
        if u.path == "/api/health":
            return self._json({"ok": True, "skus": len(get_catalog().products)})
        return self.static(u.path)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        u = urlparse(self.path)
        if u.path != "/api/chat":
            return self._json({"error": "not found"}, 404)
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            return self._json({"error": "invalid json"}, 400)
        return self.api_chat(data)

    # ---------- API
    def api_products(self, qs):
        lang = self._lang(qs)
        limit = int(qs.get("limit", ["24"])[0])
        cat = qs.get("category", [""])[0]
        q = qs.get("q", [""])[0]
        c = get_catalog()
        if q:
            res, meta = c.search(q, {"category": [cat] if cat else None}, limit=limit)
        else:
            pool = [p for p in c.products if (not cat or p["category"] == cat)]
            pool.sort(key=lambda p: (-(p["rating"] * (p["review_count"] ** 0.5)), p["sku"]))
            res, meta = pool[:limit], {"matched": len(pool), "relaxed": []}
        return self._json({
            "lang": lang,
            "count": len(res),
            "matched": meta.get("matched"),
            "products": [slim(p, lang) for p in res],
            "fx": CONFIG["fx"],
        })

    def api_product(self, sku, lang):
        p = get_catalog().by_sku.get(sku)
        if not p:
            return self._json({"error": "not found", "sku": sku}, 404)
        return self._json(slim(p, lang))

    def api_chat(self, data):
        msg = (data.get("message") or "").strip()
        lang = "en" if data.get("lang") == "en" else "zh"
        sid = data.get("session_id") or uuid.uuid4().hex
        if not msg:
            return self._json({"error": "empty message"}, 400)

        s = _session(sid, lang)
        with _LOCK:
            r = s.respond(msg)

        return self._json({
            "session_id": sid,
            "lang": lang,
            "text": r["text"],
            "products": r["products"],
            "bundle": r["bundle"],
            "ask": r["ask"],
            "meta": r["meta"],
        })

    # ---------- 静态
    def static(self, path):
        rel = "store.html" if path in ("/", "/index.html") else path.lstrip("/")
        f = (WEB / rel).resolve()
        if not str(f).startswith(str(WEB.resolve())) or not f.is_file():
            return self._send(b"not found", "text/plain; charset=utf-8", 404)
        ctype = mimetypes.guess_type(str(f))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript",):
            ctype += "; charset=utf-8"
        self._send(f.read_bytes(), ctype)


class Server(ThreadingHTTPServer):
    """浏览器/客户端提前断开连接是常态，不该刷一屏 traceback。
    真实错误仍然照常打印。"""
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        import sys as _sys
        et, _, _ = _sys.exc_info()
        if et and issubclass(et, (ConnectionResetError, ConnectionAbortedError,
                                  BrokenPipeError, TimeoutError)):
            return
        super().handle_error(request, client_address)


def serve(host="127.0.0.1", port=8770):
    httpd = Server((host, port), Handler)
    print(f"Nook serving on http://{host}:{port}   (Ctrl+C to stop)")
    print(f"  store : http://{host}:{port}/")
    print(f"  embed : http://{host}:{port}/embed.html")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    import sys
    serve(port=int(sys.argv[1]) if len(sys.argv) > 1 else 8770)
