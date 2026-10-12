/*!
 * Nook · 可嵌入 AI 导购 widget
 * ------------------------------------------------------------------
 * 客户接入方式（真的只有这一行）：
 *   <script src="https://your-cdn/nook-widget.js"
 *           data-api="/api" data-lang="zh" data-accent="#2f6f4e"></script>
 *
 * 设计要点：
 *  - Shadow DOM 隔离样式：绝不污染客户站点的 CSS，也不被客户站点污染
 *  - 不依赖任何框架，不产生全局变量污染（只暴露 window.Nook 一个句柄）
 *  - 加购通过自定义事件 nook:add-to-cart 通知宿主页面，与页面解耦
 */
(function () {
  'use strict';

  var me = document.currentScript;
  if (!me) {
    var all = document.getElementsByTagName('script');
    for (var i = all.length - 1; i >= 0; i--) {
      if (all[i].src && all[i].src.indexOf('nook-widget') >= 0) { me = all[i]; break; }
    }
  }
  if (!me || me.dataset.nookLoaded) { return; }
  me.dataset.nookLoaded = '1';

  var API = me.dataset.api || '/api';
  var ACCENT = me.dataset.accent || '#2f6f4e';
  var BRAND = me.dataset.brand || '';
  var lang = me.dataset.lang || document.documentElement.lang || 'zh';
  if (lang.indexOf('zh') !== 0) { lang = 'en'; } else { lang = 'zh'; }

  var T = {
    zh: { send: '发送', ph: '说说你想在哪个房间、想解决什么…', reset: '重新开始',
          add: '加入购物车', added: '已加入 ✓', thinking: 'Nook 正在想…' },
    en: { send: 'Send', ph: 'Which room, and what are you trying to solve?', reset: 'Start over',
          add: 'Add to cart', added: 'Added ✓', thinking: 'Nook is thinking…' }
  };

  var sid = null;
  var open = false;
  var busy = false;
  var booted = false;

  /* 如果宿主页面没有单独引入 nook-api.js，widget 自己按同目录把它拉起来。
     这样"客户只需要一行 script"才是真的 —— 而不是悄悄要求两行。 */
  var apiReady = new Promise(function (res) {
    if (window.NookAPI) { res(); return; }
    var s = document.createElement('script');
    s.src = me.src.replace(/[^/]*$/, 'nook-api.js');
    s.onload = res;
    s.onerror = res;      // 失败也让后续流程走完，报错由各自的 catch 处理
    document.head.appendChild(s);
  });

  /* ---------------- 工具 ---------------- */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function uid() {
    if (window.crypto && crypto.randomUUID) { return crypto.randomUUID().replace(/-/g, ''); }
    return 'n' + Math.random().toString(36).slice(2) + Date.now().toString(36);
  }
  /* 图片挂了也要有东西撑住版面，不能让客户站点出现白洞 */
  function ph(text) {
    var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160">'
      + '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
      + '<stop offset="0" stop-color="#e8ece6"/><stop offset="1" stop-color="#cfd8ce"/>'
      + '</linearGradient></defs><rect width="160" height="160" fill="url(#g)"/>'
      + '<text x="80" y="84" text-anchor="middle" font-family="sans-serif" font-size="11"'
      + ' fill="#61705f">' + esc(text).slice(0, 16) + '</text></svg>';
    return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
  }

  /* ---------------- Shadow DOM ---------------- */
  var host = document.createElement('div');
  host.setAttribute('data-nook', '');
  host.style.cssText = 'position:fixed;right:20px;bottom:20px;z-index:2147483000;'
    + 'width:0;height:0;';
  var sh = host.attachShadow({ mode: 'open' });

  sh.innerHTML = ''
    + '<style>'
    + ':host{all:initial}'
    + '*{box-sizing:border-box;font-family:"Microsoft YaHei","PingFang SC",'
    + '"Hiragino Sans GB",system-ui,-apple-system,"Segoe UI",sans-serif}'
    + '.launcher{position:absolute;right:0;bottom:0;display:flex;align-items:center;gap:9px;'
    + 'background:' + ACCENT + ';color:#fff;border:0;border-radius:26px;padding:12px 19px 12px 14px;'
    + 'font-size:14px;font-weight:700;cursor:pointer;white-space:nowrap;'
    + 'box-shadow:0 4px 10px rgba(0,0,0,.16),0 12px 30px rgba(0,0,0,.18);transition:transform .16s}'
    + '.launcher:hover{transform:translateY(-2px)}'
    + '.launcher .dot{width:24px;height:24px;border-radius:50%;background:rgba(255,255,255,.22);'
    + 'display:grid;place-items:center;font-size:13px}'
    + '.panel{position:absolute;right:0;bottom:62px;width:382px;height:min(604px,72vh);'
    + 'background:#fff;border-radius:17px;display:flex;flex-direction:column;overflow:hidden;'
    + 'box-shadow:0 8px 24px rgba(0,0,0,.14),0 26px 60px rgba(0,0,0,.2);'
    + 'border:1px solid #e6e8e3;opacity:0;transform:translateY(10px) scale(.98);'
    + 'pointer-events:none;transition:opacity .17s,transform .17s}'
    + '.panel.on{opacity:1;transform:none;pointer-events:auto}'
    + '.hd{display:flex;align-items:center;gap:10px;padding:13px 15px;background:' + ACCENT + ';color:#fff}'
    + '.hd .av{width:29px;height:29px;border-radius:50%;background:rgba(255,255,255,.22);'
    + 'display:grid;place-items:center;font-size:14px;flex:0 0 auto}'
    + '.hd .tt{font-size:14px;font-weight:700;line-height:1.25}'
    + '.hd .ss{font-size:11px;opacity:.8}'
    + '.hd .x{margin-left:auto;background:transparent;border:0;color:#fff;font-size:19px;'
    + 'cursor:pointer;opacity:.85;padding:2px 5px;line-height:1}'
    + '.hd .x:hover{opacity:1}'
    + '.log{flex:1;overflow-y:auto;padding:15px 14px 6px;background:#fbfbf9;scroll-behavior:smooth}'
    + '.msg{display:flex;margin-bottom:12px}'
    + '.msg.u{justify-content:flex-end}'
    + '.bub{max-width:86%;padding:10px 13px;border-radius:13px;font-size:13.5px;line-height:1.65;'
    + 'white-space:pre-wrap;word-break:break-word}'
    + '.msg.b .bub{background:#fff;border:1px solid #e8eae5;border-bottom-left-radius:4px;color:#1d211c}'
    + '.msg.u .bub{background:' + ACCENT + ';color:#fff;border-bottom-right-radius:4px}'
    + '.typing{display:flex;gap:4px;padding:4px 2px}'
    + '.typing i{width:6px;height:6px;border-radius:50%;background:#b6c0b4;animation:b 1s infinite}'
    + '.typing i:nth-child(2){animation-delay:.15s}.typing i:nth-child(3){animation-delay:.3s}'
    + '@keyframes b{0%,60%,100%{opacity:.3;transform:translateY(0)}30%{opacity:1;transform:translateY(-3px)}}'
    + '.bundle{margin:2px 0 11px;padding:9px 12px;border-radius:11px;background:#eef4ef;'
    + 'border:1px solid #d3e2d7;font-size:12px;color:#28513a;line-height:1.6}'
    + '.bundle b{font-size:12.5px}'
    + '.pc{background:#fff;border:1px solid #e8eae5;border-radius:12px;padding:9px;'
    + 'margin:0 0 9px;display:flex;gap:11px;align-items:flex-start}'
    + '.pc img{width:64px;height:64px;border-radius:9px;object-fit:cover;flex:0 0 auto;background:#e8ece6}'
    + '.pc .bd{min-width:0;flex:1}'
    + '.pc .nm{font-size:13px;font-weight:700;line-height:1.35;margin-bottom:3px}'
    + '.pc .rz{font-size:11.5px;color:#6b7268;line-height:1.55;margin-bottom:6px}'
    + '.pc .rw{display:flex;align-items:center;gap:8px;flex-wrap:wrap}'
    + '.pc .pr{font-size:13px;font-weight:800;letter-spacing:-.2px}'
    + '.pc .ad{border:1px solid ' + ACCENT + ';background:transparent;color:' + ACCENT + ';'
    + 'font-size:11.5px;padding:4px 10px;border-radius:8px;cursor:pointer;white-space:nowrap}'
    + '.pc .ad:hover{background:' + ACCENT + ';color:#fff}'
    + '.pc .ad.done{background:' + ACCENT + ';color:#fff}'
    + '.chips{padding:0 14px 8px;display:flex;gap:7px;flex-wrap:wrap;background:#fbfbf9}'
    + '.chips button{border:1px solid #dfe4dd;background:#fff;color:#41504a;font-size:12px;'
    + 'padding:6px 11px;border-radius:16px;cursor:pointer}'
    + '.chips button:hover{border-color:' + ACCENT + ';color:' + ACCENT + '}'
    + '.cp{display:flex;gap:8px;padding:11px 14px;border-top:1px solid #eceee9;background:#fff}'
    + '.cp input{flex:1;border:1px solid #e2e5df;border-radius:10px;padding:10px 12px;font-size:13.5px;'
    + 'outline:none;background:#fbfbf9;color:#1d211c;min-width:0}'
    + '.cp input:focus{border-color:' + ACCENT + ';background:#fff}'
    + '.cp button{background:' + ACCENT + ';border:0;color:#fff;border-radius:10px;padding:0 16px;'
    + 'font-size:13.5px;font-weight:700;cursor:pointer;white-space:nowrap}'
    + '.cp button:disabled{opacity:.45;cursor:default}'
    + '.fxnote{font-size:10.5px;color:#98a099;padding:0 14px 9px;background:#fff;text-align:center}'
    + '@media (max-width:560px){'
    + '.panel{position:fixed;left:0;right:0;bottom:0;top:0;width:auto;height:auto;'
    + 'border-radius:0;border:0}'
    + '.launcher{right:14px;bottom:14px}'
    + '}'
    + '</style>'
    + '<button class="launcher" part="launcher"><span class="dot">◈</span>'
    + '<span class="lt"></span></button>'
    + '<section class="panel" role="dialog" aria-label="Nook">'
    + '<div class="hd"><div class="av">◈</div>'
    + '<div><div class="tt"></div><div class="ss"></div></div>'
    + '<button class="x" title="close">×</button></div>'
    + '<div class="log"></div>'
    + '<div class="chips"></div>'
    + '<form class="cp"><input type="text" autocomplete="off"><button type="submit"></button></form>'
    + '<div class="fxnote"></div>'
    + '</section>';

  var $ = function (s) { return sh.querySelector(s); };
  var launcher = $('.launcher'), panel = $('.panel'), log = $('.log');
  var chips = $('.chips'), form = $('.cp'), input = $('.cp input'), send = $('.cp button');

  document.body.appendChild(host);

  /* ---------------- 文案 ---------------- */
  var cfg = null;
  function txt(node, s) { if (node) { node.textContent = s; } }

  function applyLang() {
    var t = T[lang];
    txt($('.lt'), (cfg && cfg.widget.launcher[lang]) || (lang === 'zh' ? '问问 Nook' : 'Ask Nook'));
    txt($('.hd .tt'), (cfg && cfg.widget.title[lang]) || 'Nook');
    txt($('.hd .ss'), BRAND || (cfg ? cfg.brand.name : ''));
    txt(send, t.send);
    input.placeholder = t.ph;
    txt($('.fxnote'), (cfg && cfg.fx.note[lang]) || '');
    if (cfg) {
      chips.innerHTML = '';
      cfg.widget.quick_replies[lang].forEach(function (q) {
        var b = document.createElement('button');
        b.type = 'button';
        b.textContent = q;
        b.onclick = function () { ask(q); };
        chips.appendChild(b);
      });
    }
  }

  /* ---------------- 渲染 ---------------- */
  function bubble(role, text) {
    var m = document.createElement('div');
    m.className = 'msg ' + role;
    var b = document.createElement('div');
    b.className = 'bub';
    b.textContent = text || '';
    m.appendChild(b);
    log.appendChild(m);
    log.scrollTop = log.scrollHeight;
    return b;
  }

  function productCard(p) {
    var el = document.createElement('div');
    el.className = 'pc';
    el.innerHTML = '<img alt=""><div class="bd">'
      + '<div class="nm">' + esc(p.name) + '</div>'
      + '<div class="rz">' + esc(p.reason) + '</div>'
      + '<div class="rw"><span class="pr">' + esc(p.price_display) + '</span>'
      + '<button class="ad">' + T[lang].add + '</button></div></div>';
    var img = el.querySelector('img');
    img.src = p.image;
    img.onerror = function () { img.onerror = null; img.src = ph(p.name); };
    var btn = el.querySelector('.ad');
    btn.onclick = function () {
      btn.textContent = T[lang].added;
      btn.classList.add('done');
      window.dispatchEvent(new CustomEvent('nook:add-to-cart', { detail: p, bubbles: true }));
      setTimeout(function () { btn.textContent = T[lang].add; btn.classList.remove('done'); }, 1500);
    };
    return el;
  }

  function renderReply(r) {
    if (r.bundle) {
      var b = document.createElement('div');
      b.className = 'bundle';
      b.innerHTML = '<b>' + esc(r.bundle.title) + '</b> · 合计 ' + esc(r.bundle.total_display || '');
      log.appendChild(b);
    }
    if (r.products && r.products.length) {
      r.products.forEach(function (p) { log.appendChild(productCard(p)); });
    }
    log.scrollTop = log.scrollHeight;
  }

  /* ---------------- 对话 ---------------- */
  function ask(text) {
    if (busy || !text) { return; }
    busy = true;
    send.disabled = true;
    input.value = '';
    bubble('u', text);

    var holder = document.createElement('div');
    holder.className = 'msg b';
    holder.innerHTML = '<div class="bub"><div class="typing"><i></i><i></i><i></i></div></div>';
    log.appendChild(holder);
    log.scrollTop = log.scrollHeight;

    apiReady
      .then(function () {
        return NookAPI.chat({ session_id: sid, message: text, lang: lang });
      })
      .then(function (r) {
        holder.remove();
        if (r.session_id) { sid = r.session_id; }
        if (r.error) { bubble('b', lang === 'zh' ? '服务暂时不可用，稍后再试。' : 'Service unavailable.'); return; }
        bubble('b', r.text);
        renderReply(r);
      })
      .catch(function () {
        holder.remove();
        bubble('b', lang === 'zh' ? '连接失败，检查服务是否在运行。' : 'Connection failed.');
      })
      .then(function () { busy = false; send.disabled = false; input.focus(); });
  }

  function greeting(text) {
    bubble('b', text || (lang === 'zh'
      ? '你好，我是 Nook。你不用想好要买什么——告诉我你想在哪个房间、想解决什么事就行。'
      : "Hi, I'm Nook. You don't need to know what you want yet — tell me the room and the problem."));
  }

  function boot() {
    if (booted) { return; }
    booted = true;
    apiReady
      .then(function () { return NookAPI.config(); })
      .then(function (c) { cfg = c; applyLang(); greeting(c.widget.opening[lang]); })
      .catch(function () { applyLang(); greeting(null); });
  }

  /* ---------------- 交互 ---------------- */
  launcher.onclick = function () {
    open = !open;
    panel.classList.toggle('on', open);
    if (open) { boot(); setTimeout(function () { input.focus(); }, 120); }
  };
  $('.hd .x').onclick = function () { open = false; panel.classList.remove('on'); };
  form.onsubmit = function (e) { e.preventDefault(); ask(input.value.trim()); };
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && open) { open = false; panel.classList.remove('on'); }
  });

  applyLang();

  /* 对外只暴露一个句柄，供宿主页面切换语言 */
  window.Nook = {
    open: function () { if (!open) { launcher.click(); } },
    close: function () { open = false; panel.classList.remove('on'); },
    setLang: function (l) { lang = (l === 'en') ? 'en' : 'zh'; applyLang(); },
    ask: ask,
    get sessionId() { return sid; }
  };
})();
