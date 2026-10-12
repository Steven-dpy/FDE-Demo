# -*- coding: utf-8 -*-
"""把 Nook 打包成可托管在 GitHub Pages 的纯静态演示版

为什么要这个脚本：
    服务端版（app/server.py）和静态版的**前端源码是同一份**（web/ 目录）。
    静态版只是换了一个数据访问实现（浏览器端引擎）并改了几处路径。
    所以这里做的是组装，不是复制粘贴 —— 避免两份代码各自漂移。

产出：portfolio/demo/
    ├── index.html          店铺页（静态模式）
    ├── embed.html          嵌入演示（静态模式）
    ├── store.css / store.js
    ├── nook-api.js         统一数据层
    ├── nook-widget.js      可嵌入 widget
    ├── static-engine.js    浏览器端规则引擎
    └── products.json       240 SKU

用法：  python tools/build_static.py
"""
from __future__ import annotations

import pathlib
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
OUT = ROOT / "portfolio" / "demo"

COPY = ["store.css", "store.js", "nook-api.js", "nook-widget.js", "static-engine.js"]
PAGES = ["store.html", "embed.html"]

# 在 nook-api.js 之前插入引擎引导代码
BOOT = """<script src="static-engine.js"></script>
<script>
  /* 静态演示版：先把商品库取回来初始化引擎，再放行页面查询。
     nook-api.js 里的 whenReady() 会等这个事件。 */
  fetch('products.json')
    .then(function (r) { return r.json(); })
    .then(function (p) {
      window.NookEngine.init(p);
      window.dispatchEvent(new Event('nook:engine-ready'));
    })
    .catch(function () {
      document.body.insertAdjacentHTML('afterbegin',
        '<p style="padding:14px;background:#fdeaea;color:#c62828">'
        + '商品库加载失败，请通过 HTTP 访问（本地直接双击打开 file:// 会被浏览器拦截）。</p>');
    });
</script>
"""

BANNER = """<div style="background:#eaf2ec;border-bottom:1px solid #cfe0d4;color:#245739;
     padding:9px 30px;font-size:12.5px;font-family:system-ui,sans-serif">
  静态演示版 · 全部逻辑在浏览器里运行，没有后端服务 ·
  <a href="../index.html" style="color:#245739">← 返回作品集</a>
</div>
"""


def build_page(src: pathlib.Path, dst: pathlib.Path, banner: bool):
    html = src.read_text(encoding="utf-8")

    # 绝对路径改为相对（静态站点可能部署在子路径下）
    for f in ["store.css", "store.js", "nook-api.js", "nook-widget.js"]:
        html = html.replace('src="/%s"' % f, 'src="%s"' % f)
        html = html.replace('href="/%s"' % f, 'href="%s"' % f)

    if "<body>" not in html:
        raise SystemExit("未找到 <body>，%s 结构变了？" % src.name)

    # 引擎引导放在最前：products.json 先取回来，其余脚本通过 whenReady() 等它
    html = html.replace("<body>", "<body>\n" + BOOT, 1)

    if banner:
        html = html.replace("<body>", "<body>\n" + BANNER, 1)

    html = html.replace("<title>", "<title>[静态版] ", 1)
    dst.write_text(html, encoding="utf-8")
    return len(html)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    for name in COPY:
        shutil.copy2(WEB / name, OUT / name)

    shutil.copy2(ROOT / "data" / "products.json", OUT / "products.json")

    print("静态演示版打包完成 → portfolio/demo/")
    for name in COPY:
        print("  %-20s %6.1f KB" % (name, (OUT / name).stat().st_size / 1024))
    print("  %-20s %6.1f KB" % ("products.json", (OUT / "products.json").stat().st_size / 1024))
    for i, name in enumerate(PAGES):
        n = build_page(WEB / name, OUT / ("index.html" if name == "store.html" else name),
                       banner=(name == "store.html"))
        print("  %-20s %6.1f KB" % (("index.html" if name == "store.html" else name), n / 1024))
    print()
    print("本地预览：  cd portfolio/demo && python -m http.server 8780")
    print("发布：      把 portfolio/ 整个推到 GitHub Pages 即可")


if __name__ == "__main__":
    main()
