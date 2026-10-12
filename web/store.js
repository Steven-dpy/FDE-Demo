/* Fern & Oak 店铺页逻辑：拉商品、分类、切换语言、购物车计数 */
(function () {
  var lang = localStorage.getItem('fo-lang') || 'zh';
  var cat = '';
  var cache = {};

  var grid = document.getElementById('grid');
  var cats = document.getElementById('cats');
  var fx = document.getElementById('fx');
  var fxf = document.getElementById('fxf');
  var cartn = document.getElementById('cartn');
  var cart = 0;

  var L = {
    zh: { all: '全部', add: '加入购物车', left: '件现货', days: '天可发', loading: '正在载入…' },
    en: { all: 'All', add: 'Add to cart', left: 'in stock', days: 'days', loading: 'Loading…' }
  };

  var CAT_ZH = {
    sofa: '沙发', armchair: '单椅', coffee_table: '茶几', dining_table: '餐桌',
    dining_chair: '餐椅', bed: '床架', wardrobe: '衣柜', bookshelf: '书架',
    desk: '书桌', floor_lamp: '落地灯', table_lamp: '台灯', rug: '地毯',
    storage: '收纳', outdoor: '户外'
  };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  /* 图片加载失败时用一张同色系占位图，保证页面永远不留白洞 */
  function placeholder(text) {
    var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300">'
      + '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
      + '<stop offset="0" stop-color="#e6e9e2"/><stop offset="1" stop-color="#ccd6cb"/>'
      + '</linearGradient></defs><rect width="300" height="300" fill="url(#g)"/>'
      + '<text x="150" y="156" text-anchor="middle" font-family="sans-serif" font-size="15"'
      + ' fill="#5f6b60">' + esc(text).slice(0, 22) + '</text></svg>';
    return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
  }

  function skeleton() {
    grid.innerHTML = '';
    for (var i = 0; i < 8; i++) {
      var d = document.createElement('div');
      d.className = 'skel';
      grid.appendChild(d);
    }
  }

  function renderCats(list) {
    var t = L[lang];
    var html = '<button class="chip' + (cat === '' ? ' on' : '') + '" data-c="' + '">' + t.all + '</button>';
    list.forEach(function (c) {
      var label = lang === 'zh' ? (CAT_ZH[c] || c) : c.replace(/_/g, ' ');
      html += '<button class="chip' + (cat === c ? ' on' : '') + '" data-c="' + esc(c) + '">'
        + esc(label) + ' <span style="opacity:.55">' + (cache[c] || '') + '</span></button>';
    });
    cats.innerHTML = html;
    Array.prototype.forEach.call(cats.querySelectorAll('.chip'), function (b) {
      b.onclick = function () { cat = b.dataset.c; load(); };
    });
  }

  function card(p) {
    var t = L[lang];
    var d = p.dimensions;
    var el = document.createElement('article');
    el.className = 'card';
    el.innerHTML =
      '<div class="thumb"><img loading="lazy" alt="' + esc(p.name) + '"></div>'
      + '<div class="info">'
      + '<div class="cat">' + esc(p.category_label) + '</div>'
      + '<div class="nm">' + esc(p.name) + '</div>'
      + '<div class="dsc">' + esc(p.description) + '</div>'
      + '<div class="pr">' + esc(p.price_display) + '</div>'
      + '<div class="meta"><span>' + d.w + '×' + d.d + '×' + d.h + 'cm</span>'
      + '<span>★' + p.rating + ' (' + p.review_count + ')</span></div>'
      + '<div class="meta"><span>' + p.stock + ' ' + t.left + '</span>'
      + '<span>' + p.lead_time_days + ' ' + t.days + '</span></div>'
      + '<button class="add">' + t.add + '</button>'
      + '</div>';
    var img = el.querySelector('img');
    img.src = p.image;
    img.onerror = function () { img.onerror = null; img.src = placeholder(p.name); };
    el.querySelector('.add').onclick = function () {
      cart++; cartn.textContent = cart;
      this.textContent = lang === 'zh' ? '已加入 ✓' : 'Added ✓';
      var self = this;
      setTimeout(function () { self.textContent = t.add; }, 1300);
    };
    return el;
  }

  function load() {
    skeleton();
    NookAPI.products(lang, cat, 48)
      .then(function (data) {
        fx.textContent = data.fx.note[lang];
        fxf.textContent = data.fx.note[lang];
        grid.innerHTML = '';
        data.products.forEach(function (p) { grid.appendChild(card(p)); });

        // 分类计数必须用**全量**数据算，否则 chip 上的数字是错的
        return NookAPI.products(lang, '', 300)
          .then(function (all) {
            var counts = {};
            all.products.forEach(function (p) {
              counts[p.category] = (counts[p.category] || 0) + 1;
            });
            cache = counts;
            var order = Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a]; });
            var top = order.slice(0, 9);
            if (cat && top.indexOf(cat) < 0) { top.push(cat); }   // 别让当前分类从 chips 里消失
            renderCats(top);
          });
      })
      .catch(function () {
        grid.innerHTML = '<p style="color:#6b7268">载入失败，请刷新。</p>';
      });
  }

  document.getElementById('lang').onclick = function () {
    lang = (lang === 'zh') ? 'en' : 'zh';
    localStorage.setItem('fo-lang', lang);
    this.textContent = (lang === 'zh') ? 'EN' : '中文';
    document.documentElement.lang = lang === 'zh' ? 'zh' : 'en';
    if (window.Nook) { window.Nook.setLang(lang); }
    load();
  };

  Array.prototype.forEach.call(document.querySelectorAll('.nav a'), function (a) {
    a.onclick = function (e) { e.preventDefault(); cat = a.dataset.cat || ''; load(); };
  });

  /* Nook 里加购 → 页头购物车计数联动（widget 与页面通过事件解耦） */
  window.addEventListener('nook:add-to-cart', function (e) {
    cart++;
    cartn.textContent = cart;
  });

  document.getElementById('lang').textContent = (lang === 'zh') ? 'EN' : '中文';
  document.documentElement.lang = lang === 'zh' ? 'zh' : 'en';
  if (window.Nook) { window.Nook.setLang(lang); }
  load();
})();
