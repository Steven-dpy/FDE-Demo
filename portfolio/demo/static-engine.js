/*!
 * Nook · 浏览器端规则引擎（静态演示版）
 * ------------------------------------------------------------------
 * 为什么会有这个文件：
 *   GitHub Pages 只能跑静态资源，没有 Python 进程。
 *   而 Nook 的检索/编排层是**规则实现、不依赖 LLM**，所以可以原样移植到浏览器，
 *   得到一个真正能交互、零服务器的演示版 —— 而不是预录好的假对话。
 *
 * 代价：同一套规则维护了两份实现（Python / JS）。
 *   这是有意的取舍 —— 见 portfolio/index.html「关键设计决策」第 04 条。
 *   两份实现的一致性由 tools/conformance.mjs 做交叉验证。
 *
 * 与 app/concierge.py + app/catalog.py + app/money.py 一一对应。
 */
(function (root) {
  'use strict';

  var USD_CNY = 7.20;

  /* ==================== 货币（对应 money.py） ==================== */
  var money = {
    toUsd: function (a, lang) { return lang === 'zh' ? a / USD_CNY : a; },
    fmt: function (usd, lang) {
      if (lang === 'zh') return 'US$' + Math.round(usd).toLocaleString('en-US')
        + ' ≈ ¥' + Math.round(usd * USD_CNY).toLocaleString('en-US');
      return 'US$' + Math.round(usd).toLocaleString('en-US');
    },
    fmtShort: function (usd, lang) {
      if (lang === 'zh') return '¥' + Math.round(usd * USD_CNY).toLocaleString('en-US');
      return 'US$' + Math.round(usd).toLocaleString('en-US');
    },
    note: function (lang) {
      return lang === 'zh'
        ? '参考汇率 1 美元 ≈ ' + USD_CNY.toFixed(2) + ' 元人民币，实际以结算为准'
        : 'Reference rate: 1 USD ≈ ' + USD_CNY.toFixed(2) + ' CNY. Final amount at checkout.';
    }
  };

  /* ==================== 别名表（对应 catalog.ALIASES） ==================== */
  var ALIASES = {
    '沙发': 'sofa', '长椅': 'sofa', '单人椅': 'armchair', '扶手椅': 'armchair',
    '休闲椅': 'armchair', '单人沙发': 'armchair', '三人沙发': 'sofa',
    '茶几': 'coffee table', '边几': 'coffee table', '餐桌': 'dining table',
    '饭桌': 'dining table', '餐椅': 'dining chair', '椅子': 'dining chair',
    '床架': 'bed', '双人床': 'bed', '床': 'bed', '衣柜': 'wardrobe', '衣橱': 'wardrobe',
    '书架': 'bookshelf', '书柜': 'bookshelf', '置物架': 'bookshelf',
    '书桌': 'desk', '办公桌': 'desk', '工作台': 'desk',
    '落地灯': 'floor lamp', '台灯': 'table lamp', '灯': 'lamp',
    '地毯': 'rug', '地垫': 'rug', '收纳': 'storage', '储物': 'storage', '柜子': 'cabinet',
    '户外': 'outdoor', '阳台': 'outdoor', '庭院': 'outdoor', '露台': 'outdoor',
    '小户型': 'small space', '小空间': 'small space', '地方小': 'small space',
    '看书': 'reading', '阅读': 'reading', '读书': 'reading',
    '办公': 'work from home', '居家办公': 'work from home', '在家上班': 'work from home',
    '宠物': 'pet', '猫': 'pet', '狗': 'pet',
    '孩子': 'family', '小孩': 'family', '一家人': 'family',
    '好打理': 'easy to clean', '好清洁': 'easy to clean',
    '北欧': 'scandinavian', '日式': 'japandi', '侘寂': 'japandi',
    '极简': 'minimalist', '简约': 'minimalist', '中古': 'mid-century', '复古': 'mid-century',
    '工业': 'industrial', '工业风': 'industrial', '海岸': 'coastal', '波西米亚': 'boho',
    '橡木': 'oak', '胡桃木': 'walnut', '白蜡木': 'ash', '实木': 'solid oak',
    '真皮': 'leather', '牛皮': 'leather', '皮': 'leather',
    '布': 'fabric', '绒': 'velvet', '羊羔绒': 'boucle', '藤': 'rattan', '藤编': 'rattan',
    '大理石': 'marble', '玻璃': 'glass',
    '客厅': 'living room', '卧室': 'bedroom', '餐厅': 'dining room',
    '书房': 'home office', '玄关': 'hallway', '走廊': 'hallway'
  };

  var STYLE_ZH = { scandinavian: '北欧', japandi: '日式北欧', mid_century: '中古',
    minimalist: '极简', industrial: '工业', coastal: '海岸', boho: '波西米亚', modern: '现代' };
  var MAT_ZH = { oak: '实木橡木', walnut: '胡桃木', ash: '白蜡木', birch: '桦木多层板',
    metal: '粉末喷涂钢', linen: '水洗亚麻', boucle: '羊羔绒', velvet: '天鹅绒',
    leather: '头层牛皮', fabric: '混纺面料', rattan: '天然藤编', wool: '手工羊毛',
    marble: '哑光大理石', ceramic: '釉面陶瓷', glass: '钢化玻璃' };
  var TAG_ZH = { small_space: '占地紧凑，小空间放得下', family: '加固结构，适合有孩子的家庭',
    reading: '为长时间窝着看书设计', wfh: '按整天办公的强度设计',
    pet_friendly: '表面一擦就净，宠物友好', low_maintenance: '日常打理只需一块湿布',
    statement_piece: '能撑起整个空间', storage_heavy: '收纳量大',
    outdoor_safe: '耐晒耐雨', easy_assembly: '免工具，二十分钟能装好' };
  var RELAX = { zh: { max_width: '尺寸上限', material: '材质', style: '风格', tags: '特殊需求' },
                en: { max_width: 'size limit', material: 'material', style: 'style', tags: 'special requirement' } };
  var SOFT_ORDER = ['max_width', 'material', 'style', 'tags'];

  /* ==================== 抽取规则（对应 concierge 的模式表） ==================== */
  var CATEGORY_PATTERNS = [
    ['armchair', ['单人沙发', '单人椅', '扶手椅', '休闲椅', 'armchair', 'accent chair']],
    ['sofa', ['三人沙发', '沙发', 'sofa', 'couch']],
    ['coffee_table', ['茶几', '边几', 'coffee table', 'side table']],
    ['dining_table', ['餐桌', '饭桌', 'dining table']],
    ['dining_chair', ['餐椅', 'dining chair']],
    ['wardrobe', ['衣柜', '衣橱', 'wardrobe']],
    ['bookshelf', ['书架', '书柜', '置物架', 'bookshelf', 'bookcase']],
    ['desk', ['书桌', '办公桌', '工作台', 'desk']],
    ['floor_lamp', ['落地灯', 'floor lamp']],
    ['table_lamp', ['台灯', 'table lamp']],
    ['rug', ['地毯', '地垫', 'rug', 'carpet']],
    ['storage', ['收纳柜', '储物柜', '边柜', '床头柜', 'storage', 'cabinet', 'sideboard']],
    ['outdoor', ['户外家具', 'patio', 'outdoor furniture']],
    ['bed', ['床架', '双人床', '床', 'bed frame', 'bed']]
  ];
  var ROOM_PATTERNS = [
    ['living_room', ['客厅', '起居室', 'living room', 'lounge']],
    ['bedroom', ['卧室', '睡房', 'bedroom']],
    ['dining_room', ['餐厅', 'dining room']],
    ['home_office', ['书房', 'home office', 'study', 'work from home', '远程办公']],
    ['outdoor', ['阳台', '庭院', '露台', 'balcony', 'patio']],
    ['hallway', ['玄关', '走廊', 'hallway', 'entryway']]
  ];
  var STYLE_PATTERNS = [
    ['scandinavian', ['北欧', 'scandinavian']], ['japandi', ['日式', '侘寂', 'japandi']],
    ['mid_century', ['中古', '复古', 'mid-century', 'mid century']],
    ['minimalist', ['极简', '简约', 'minimalist']], ['industrial', ['工业', 'industrial']],
    ['coastal', ['海岸', 'coastal']], ['boho', ['波西米亚', 'boho']]
  ];
  var MATERIAL_PATTERNS = [
    ['oak', ['橡木', 'oak']], ['walnut', ['胡桃木', 'walnut']], ['ash', ['白蜡木', 'ash']],
    ['leather', ['真皮', '牛皮', 'leather']], ['velvet', ['天鹅绒', 'velvet']],
    ['boucle', ['羊羔绒', 'boucle']], ['fabric', ['布艺', 'fabric']],
    ['rattan', ['藤编', '藤', 'rattan']], ['marble', ['大理石', 'marble']],
    ['metal', ['金属', 'metal']]
  ];
  var TAG_PATTERNS = [
    ['small_space', ['小户型', '小空间', '地方小', '空间不大', '租房', 'small apartment', 'studio', 'tight space']],
    ['pet_friendly', ['宠物', '猫', '狗', 'pet']],
    ['family', ['孩子', '小孩', '一家人', '家庭', 'family', 'kids']],
    ['wfh', ['居家办公', '在家办公', 'work from home', 'wfh']],
    ['storage_heavy', ['收纳', '储物', 'storage']],
    ['easy_assembly', ['免安装', '好装', 'easy to assemble']]
  ];

  var CN_DIGITS = { '零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5,
    '六': 6, '七': 7, '八': 8, '九': 9 };
  var CN_UNITS = { '十': 10, '百': 100, '千': 1000, '万': 10000 };
  var CN_CHARS = '零一二两三四五六七八九十百千万';

  var BUDGET_RES = [
    /(?:预算|budget|不超过|under|below|within|less than|以内|左右|大概)\D{0,8}(\d[\d,]*)\s*(?:元|块|美金|美元|usd|dollars)?/i,
    /[$￥¥]\s*(\d[\d,]*)\s*(?:usd|dollars)?/i,
    /(\d[\d,]*)\s*(?:元|块|usd|dollars)\s*(?:以内|以下|左右)?/i,
    /(\d[\d,]*)\s*(?:元|块|美金|美元|usd|dollars)/i,
    /(\d[\d,]*)\s*(?:元|块)?\s*的?\s*(?:预算|budget)/i
  ];
  var CN_BUDGET_RES = [
    new RegExp('(?:预算|大概|差不多|不超过|最多)\\D{0,4}?([' + CN_CHARS + ']{1,8})'),
    new RegExp('([' + CN_CHARS + ']{1,8})\\s*(?:元|块钱|块)'),
    new RegExp('([' + CN_CHARS + ']{1,8})\\s*(?:左右|以内|以下|上下)'),
    new RegExp('([' + CN_CHARS + ']{1,8})\\s*(?:元|块)?\\s*的?\\s*预算')
  ];
  var WIDTH_RES = [
    /(?:宽度?|width|不超过|不宽于|no wider than)\D{0,8}(\d{2,3})\s*(?:cm|厘米|公分)?/i,
    /(\d{2,3})\s*(?:cm|厘米|公分)\s*(?:以内|以下|宽)/i
  ];
  var SEATS_RE = /(\d)\s*(?:人|座|seater|seat)/i;
  var OUT_OF_SCOPE = ['手机', '电脑', '笔记本', '耳机', '衣服', '鞋', '食品', '化妆品',
    'iphone', 'laptop', 'headphone', 'clothes', 'shoes', 'grocery'];

  var LOOKS = {
    reading_corner: {
      kw: ['阅读角', '看书', '读书', '窝着', '读书角', 'reading nook', 'reading corner',
        'book corner', 'curl up', 'read', 'reading', 'cozy corner', 'cosy corner'],
      cats: ['armchair', 'floor_lamp', 'coffee_table', 'rug'],
      title: { zh: '一个阅读角', en: 'a reading corner' },
      why: { zh: '阅读角是成套才成立的：一把能坐一小时的椅子、一盏从肩后照过来的灯，再加一个能放下杯子的台面。',
             en: 'A reading corner only works as a set: somewhere you can sit for an hour, light coming over your shoulder, and a surface to put a cup down.' }
    },
    home_office: {
      kw: ['居家办公', '在家办公', '书房', '工作区', 'work from home', 'home office', 'remote work'],
      cats: ['desk', 'bookshelf', 'table_lamp'],
      title: { zh: '一个居家办公区', en: 'a home office' },
      why: { zh: '光有桌子只算一半。你还需要放参考资料的地方，以及不反光的照明。',
             en: 'A desk is only half of it. You need somewhere for the reference books and light that does not reflect off the screen.' }
    },
    family_living: {
      kw: ['一家人', '有孩子', '小孩', '家庭', 'family', 'kids', '有娃'],
      cats: ['sofa', 'rug', 'storage'],
      title: { zh: '一个有孩子的客厅', en: 'a family living room' },
      why: { zh: '家里有孩子，优先级就变了：经得起天天折腾的家具、摔一下不疼的地面，还有一伸手就能收东西的柜子。',
             en: 'With kids in the house the priorities change: things that survive daily use, a floor that is soft to fall on, and storage you can reach in one motion.' }
    },
    small_apartment: {
      kw: ['小户型', '小空间', '地方小', '空间不大', '租房', 'small apartment', 'studio', 'tiny'],
      cats: ['sofa', 'coffee_table', 'storage'], tags: ['small_space'],
      title: { zh: '小户型', en: 'a small apartment' },
      why: { zh: '小户型里，占地比任何参数都重要。',
             en: 'In a small flat, footprint matters more than anything else on the spec sheet.' }
    },
    balcony: {
      kw: ['阳台', '露台', '庭院', 'balcony', 'patio', 'outdoor space'],
      cats: ['outdoor', 'floor_lamp', 'rug'],
      title: { zh: '一个阳台角落', en: 'a balcony setup' },
      why: { zh: '户外家具先得扛得住天气，舒适度是第二个问题。',
             en: 'Outdoor pieces have to survive weather first; comfort is the second question.' }
    }
  };

  /* ==================== 文本工具（对应 catalog.tokenize / expand_aliases） ==================== */
  function tokenize(text) {
    text = (text || '').toLowerCase();
    var out = [], m;
    var latin = text.match(/[a-z0-9]+/g) || [];
    for (var i = 0; i < latin.length; i++) if (latin[i].length > 1) out.push(latin[i]);
    var runs = text.match(/[\u4e00-\u9fff]+/g) || [];
    for (var r = 0; r < runs.length; r++) {
      var run = runs[r];
      for (var j = 0; j < run.length; j++) {
        out.push(run[j]);
        if (j < run.length - 1) out.push(run.substr(j, 2));
      }
    }
    return out;
  }

  function expandAliases(q) {
    q = (q || '').toLowerCase();
    var extra = [];
    for (var k in ALIASES) if (ALIASES.hasOwnProperty(k) && q.indexOf(k) >= 0) extra.push(ALIASES[k]);
    return q + ' ' + extra.join(' ');
  }

  function matchAny(text, patterns) {
    var t = text.toLowerCase(), out = [];
    for (var i = 0; i < patterns.length; i++) {
      for (var j = 0; j < patterns[i][1].length; j++) {
        if (t.indexOf(patterns[i][1][j]) >= 0) { out.push(patterns[i][0]); break; }
      }
    }
    return out;
  }

  /* 中文口语数字：「两千五」→ 2500、「一万五」→ 15000（结尾裸数字取上一单位的 1/10） */
  function cn2num(s) {
    if (!s) return null;
    var total = 0, section = 0, number = 0, lastUnit = 0;
    for (var i = 0; i < s.length; i++) {
      var ch = s[i];
      if (CN_DIGITS.hasOwnProperty(ch)) { number = CN_DIGITS[ch]; }
      else if (CN_UNITS.hasOwnProperty(ch)) {
        var u = CN_UNITS[ch];
        if (u === 10000) { section = (section + number) * u; total += section; section = 0; }
        else { section += (number || 1) * u; }
        number = 0; lastUnit = u;
      } else return null;
    }
    if (number) section += (lastUnit >= 10) ? number * (lastUnit / 10) : number;
    return total + section;
  }

  function num(s) { return parseInt(String(s).replace(/,/g, ''), 10); }

  /* ==================== 抽取（对应 concierge.extract） ==================== */
  function extract(text) {
    var t = text.toLowerCase(), slots = {};
    var cats = matchAny(t, CATEGORY_PATTERNS); if (cats.length) slots.category = cats;
    var rooms = matchAny(t, ROOM_PATTERNS);
    if (!rooms.length && /办公|工作/.test(t)) rooms = ['home_office'];
    if (rooms.length) slots.room = rooms;
    var st = matchAny(t, STYLE_PATTERNS); if (st.length) slots.style = st;
    var mt = matchAny(t, MATERIAL_PATTERNS); if (mt.length) slots.material = mt;
    var tg = matchAny(t, TAG_PATTERNS); if (tg.length) slots.tags = tg;

    var i, m, v;
    for (i = 0; i < BUDGET_RES.length; i++) {
      m = t.match(BUDGET_RES[i]);
      if (m) { v = num(m[1]); if (v >= 20 && v <= 200000) { slots.price_max = v; break; } }
    }
    if (slots.price_max === undefined) {
      for (i = 0; i < CN_BUDGET_RES.length; i++) {
        m = t.match(CN_BUDGET_RES[i]);
        if (m) { v = cn2num(m[1]); if (v && v >= 20 && v <= 200000) { slots.price_max = v; break; } }
      }
    }
    for (i = 0; i < WIDTH_RES.length; i++) {
      m = t.match(WIDTH_RES[i]);
      if (m) { v = num(m[1]); if (v >= 30 && v <= 400) { slots.max_width = v; break; } }
    }
    m = t.match(SEATS_RE); if (m) slots.seats_min = parseInt(m[1], 10);
    return slots;
  }

  /* 拉丁关键词按词边界，CJK 用子串 —— 否则 read 会命中 already */
  function detectLook(text) {
    var t = text.toLowerCase();
    for (var key in LOOKS) {
      if (!LOOKS.hasOwnProperty(key)) continue;
      var kws = LOOKS[key].kw;
      for (var i = 0; i < kws.length; i++) {
        var k = kws[i];
        if (/^[\x00-\x7F]+$/.test(k)) {
          if (new RegExp('\\b' + k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b').test(t)) return key;
        } else if (t.indexOf(k) >= 0) return key;
      }
    }
    return null;
  }

  /* ==================== 商品库 + 检索（对应 catalog.Catalog） ==================== */
  function Catalog(products) {
    this.products = products;
    this.bySku = {};
    this.idx = {};
    this.df = {};
    var n = products.length, i, t, toks;
    for (i = 0; i < n; i++) {
      var p = products[i];
      this.bySku[p.sku] = p;
      var title = [p.name.en, p.name.zh, p.category_en, p.category_zh].join(' ');
      var body = [p.description.en, p.description.zh, p.style, p.material,
        p.material_accent, p.color, p.room, p.tags.join(' ')].join(' ');
      var tc = {}, bc = {}, seen = {};
      toks = tokenize(title);
      for (var a = 0; a < toks.length; a++) { tc[toks[a]] = (tc[toks[a]] || 0) + 1; seen[toks[a]] = 1; }
      toks = tokenize(body);
      for (var b = 0; b < toks.length; b++) { bc[toks[b]] = (bc[toks[b]] || 0) + 1; seen[toks[b]] = 1; }
      this.idx[p.sku] = [tc, bc];
      for (t in seen) if (seen.hasOwnProperty(t)) this.df[t] = (this.df[t] || 0) + 1;
    }
    this.defaultIdf = Math.log(1 + n);
    this.idf = {};
    for (t in this.df) if (this.df.hasOwnProperty(t)) this.idf[t] = Math.log(1 + n / (1 + this.df[t]));
  }

  Catalog.prototype.passes = function (p, f) {
    if (f.category && f.category.indexOf(p.category) < 0) return false;
    if (f.room && f.room.indexOf(p.room) < 0) return false;
    if (f.price_min != null && p.price < f.price_min) return false;
    if (f.price_max != null && p.price > f.price_max) return false;
    if (f.style && f.style.indexOf(p.style) < 0) return false;
    if (f.material && f.material.indexOf(p.material) < 0) return false;
    if (f.max_width != null && p.dimensions.w > f.max_width) return false;
    if (f.max_depth != null && p.dimensions.d > f.max_depth) return false;
    if (f.seats_min != null && (p.seats || 0) < f.seats_min) return false;
    if (f.tags && f.tags.length) {
      var hit = false;
      for (var i = 0; i < f.tags.length; i++) if (p.tags.indexOf(f.tags[i]) >= 0) { hit = true; break; }
      if (!hit) return false;
    }
    if (f.in_stock !== false && p.stock <= 0) return false;
    return true;
  };

  Catalog.prototype.score = function (p, qset) {
    var pair = this.idx[p.sku], tc = pair[0], bc = pair[1], s = 0;
    for (var t in qset) {
      if (!qset.hasOwnProperty(t)) continue;
      var w = this.idf.hasOwnProperty(t) ? this.idf[t] : this.defaultIdf;
      if (tc.hasOwnProperty(t)) s += 3.0 * w;
      else if (bc.hasOwnProperty(t)) s += 1.0 * w;
    }
    s += 0.05 * p.rating + 0.15 * Math.log1p(p.review_count);
    if (p.stock > 0) s += 0.30;
    return s;
  };

  Catalog.prototype.search = function (query, filters, limit) {
    limit = limit || 6;
    var f = {}, k;
    for (k in (filters || {})) {
      var v = filters[k];
      if (v !== null && v !== undefined && v !== '' && !(Array.isArray(v) && !v.length)) f[k] = v;
    }
    var qset = {}, toks = tokenize(expandAliases(query));
    for (var i = 0; i < toks.length; i++) qset[toks[i]] = 1;

    var relaxed = [], hits = [], matched = 0;
    for (var attempt = 0; attempt <= SOFT_ORDER.length; attempt++) {
      hits = [];
      for (var j = 0; j < this.products.length; j++) {
        if (this.passes(this.products[j], f)) hits.push(this.products[j]);
      }
      matched = hits.length;
      var hasSoft = false;
      for (var s = 0; s < SOFT_ORDER.length; s++) if (f.hasOwnProperty(SOFT_ORDER[s])) { hasSoft = true; break; }
      if (hits.length || !hasSoft) break;
      for (var s2 = 0; s2 < SOFT_ORDER.length; s2++) {
        if (f.hasOwnProperty(SOFT_ORDER[s2])) { delete f[SOFT_ORDER[s2]]; relaxed.push(SOFT_ORDER[s2]); break; }
      }
    }

    var qlen = Object.keys(qset).length;
    var scored = hits.map(function (p) { return [this.score(p, qset), p]; }, this);
    if (qlen) scored.sort(function (a, b) { return (b[0] - a[0]) || (a[1].sku < b[1].sku ? -1 : 1); });
    else scored.sort(function (a, b) {
      var x = b[1].rating * Math.log1p(b[1].review_count) - a[1].rating * Math.log1p(a[1].review_count);
      return x || (a[1].sku < b[1].sku ? -1 : 1);
    });

    if (qlen && scored.length) {
      var top = scored[0][0];
      scored = scored.filter(function (x) { return x[0] > top * 0.45; });
    }
    return {
      results: scored.slice(0, limit).map(function (x) { return x[1]; }),
      meta: { matched: matched, relaxed: relaxed }
    };
  };

  Catalog.prototype.categoryAvgPrice = function (cat) {
    var xs = this.products.filter(function (p) { return p.category === cat; })
      .map(function (p) { return p.price; });
    return xs.length ? xs.reduce(function (a, b) { return a + b; }, 0) / xs.length : 500;
  };

  /* ==================== 会话（对应 concierge.Session） ==================== */
  function Session(cat, lang) {
    this.cat = cat;
    this.lang = (lang === 'en') ? 'en' : 'zh';
    this.slots = {};
    this.asked = {};
    this.turns = 0;
    this.budgetRaw = null;
  }

  Session.prototype.merge = function (nw) {
    for (var k in nw) {
      if (!nw.hasOwnProperty(k)) continue;
      var v = nw[k];
      if (Array.isArray(v)) {
        var cur = this.slots[k] || [], set = {};
        for (var i = 0; i < cur.length; i++) set[cur[i]] = 1;
        for (var j = 0; j < v.length; j++) set[v[j]] = 1;
        this.slots[k] = Object.keys(set).sort();
      } else if (k === 'price_max' || k === 'max_width') {
        this.slots[k] = (this.slots[k] == null) ? v : Math.min(this.slots[k], v);
      } else if (k === 'seats_min') {
        this.slots[k] = Math.max(this.slots[k] || 0, v);
      } else this.slots[k] = v;
    }
  };

  Session.prototype.filters = function (extra) {
    var s = this.slots;
    var f = { category: s.category, room: s.room, style: s.style, material: s.material,
      tags: s.tags, price_max: s.price_max, max_width: s.max_width,
      seats_min: s.seats_min, in_stock: true };
    if (extra) for (var k in extra) if (extra.hasOwnProperty(k)) f[k] = extra[k];
    return f;
  };

  Session.prototype.budgetLabel = function () {
    if (this.budgetRaw != null) {
      return this.lang === 'zh'
        ? '¥' + this.budgetRaw.toLocaleString('en-US')
        : 'US$' + this.budgetRaw.toLocaleString('en-US');
    }
    return money.fmtShort(this.slots.price_max || 0, this.lang);
  };

  Session.prototype.reason = function (p) {
    if (this.lang === 'en') {
      var bits = [p.style.replace(/_/g, '-') + ' style', p.material + ' body'];
      if (p.tags.length) bits.push(p.tags[0].replace(/_/g, ' '));
      var se = bits.join(', ') + '.';
      se += ' Ships in ' + p.lead_time_days + ' days, ' + p.stock + ' in stock.';
      if (this.slots.price_max) se += ' Within your ' + this.budgetLabel() + ' budget.';
      return se;
    }
    var s = (STYLE_ZH[p.style] || p.style) + '风格、' + (MAT_ZH[p.material] || p.material) + '主体';
    if (p.tags.length) s += '；' + (TAG_ZH[p.tags[0]] || p.tags[0]);
    s += '。' + p.stock + ' 件现货，' + p.lead_time_days + ' 天可发';
    if (this.slots.price_max) s += '，在你 ' + this.budgetLabel() + ' 的预算内';
    return s + '。';
  };

  Session.prototype.slim = function (p) {
    var lang = this.lang;
    return {
      sku: p.sku,
      name: p.name[lang],
      category: p.category,
      category_label: lang === 'zh' ? p.category_zh : p.category_en,
      description: p.description[lang],
      price: p.price,
      price_display: money.fmt(p.price, lang),
      price_local: money.fmtShort(p.price, lang),
      image: p.image,
      dimensions: p.dimensions,
      rating: p.rating,
      review_count: p.review_count,
      stock: p.stock,
      lead_time_days: p.lead_time_days,
      reason: this.reason(p)
    };
  };

  Session.prototype.bundle = function (key) {
    var cfg = LOOKS[key], cats = cfg.cats.slice(0, 3), budget = this.slots.price_max;
    var base = this.filters();
    delete base.category; delete base.price_max;
    if (cfg.tags) base.tags = (base.tags || []).concat(cfg.tags);
    var picks = [], used = 0, self = this;
    if (budget) {
      var avgs = {}, tot = 0;
      cats.forEach(function (c) { avgs[c] = self.cat.categoryAvgPrice(c); tot += avgs[c]; });
      cats.forEach(function (c) {
        var share = Math.max(60, Math.floor((budget - used) * avgs[c] / tot));
        var f = {}; for (var k in base) if (base.hasOwnProperty(k)) f[k] = base[k];
        f.category = [c]; f.price_max = share;
        var r = self.cat.search('', f, 1);
        if (r.results.length) { picks.push(r.results[0]); used += r.results[0].price; }
      });
    } else {
      cats.forEach(function (c) {
        var f = {}; for (var k in base) if (base.hasOwnProperty(k)) f[k] = base[k];
        f.category = [c];
        var r = self.cat.search('', f, 1);
        if (r.results.length) picks.push(r.results[0]);
      });
    }
    if (!picks.length) return null;
    var total = budget ? used : picks.reduce(function (a, p) { return a + p.price; }, 0);
    return { picks: picks, bundle: { key: key, title: cfg.title[this.lang], why: cfg.why[this.lang],
      total: total, total_display: money.fmt(total, this.lang) } };
  };

  Session.prototype.respond = function (text) {
    this.turns++;
    var nw = extract(text);
    if (nw.price_max !== undefined) {
      this.budgetRaw = nw.price_max;
      nw.price_max = Math.max(1, Math.floor(money.toUsd(nw.price_max, this.lang)));
    }
    this.merge(nw);
    var look = detectLook(text) || this.slots.look;
    if (look) this.slots.look = look;

    var lang = this.lang, i;
    for (i = 0; i < OUT_OF_SCOPE.length; i++) {
      if (text.toLowerCase().indexOf(OUT_OF_SCOPE[i]) >= 0) {
        return { text: lang === 'en'
          ? "I can only help with what Fern & Oak actually sells — sofas, tables, storage, lighting, rugs and outdoor pieces. I can't help with that one."
          : '我只能帮你从 Fern & Oak 的商品里挑家具——沙发、桌子、收纳、灯具、地毯和户外家具。这个我确实帮不上，就不乱推荐了。',
          products: [], bundle: null, ask: null, meta: { intent: 'out_of_scope' } };
      }
    }

    var anchor = this.slots.category || this.slots.look || this.slots.room;
    if (!anchor) {
      if (!this.asked.room && this.turns <= 2) {
        this.asked.room = 1;
        var q = lang === 'en' ? 'Which room are you furnishing?'
          : '你想布置哪个空间？（客厅 / 卧室 / 餐厅 / 书房 / 阳台）';
        return { text: lang === 'en' ? "Sure — let's narrow it down." : '好的，先缩小一下范围。',
          products: [], bundle: null, ask: q, meta: { intent: 'clarify_room' } };
      }
      return { text: lang === 'en'
        ? "I couldn't find anything in the catalogue that matches. Tell me the room or the kind of piece, and I'll try again."
        : '按这个我没在商品里找到对应的东西。你说一下是哪个空间、或者想要哪一类家具，我再找一次。',
        products: [], bundle: null, ask: null, meta: { intent: 'no_anchor' } };
    }

    if (this.slots.look) {
      var bd = this.bundle(this.slots.look);
      if (bd) {
        var head, ask = null;
        if (lang === 'en') {
          head = "Then you're building " + bd.bundle.title + '. ' + bd.bundle.why
            + " Here's a set that works together — about " + bd.bundle.total_display + ' total.';
        } else {
          head = '那你要的是' + bd.bundle.title + '。' + bd.bundle.why
            + '下面这套是配得上的，合计约 ' + bd.bundle.total_display + '。';
        }
        if (!this.slots.price_max && !this.asked.budget) {
          this.asked.budget = 1;
          ask = lang === 'en' ? "What's your budget for the set?"
            : '这套你大概想花多少？说人民币就行，我按预算重新配。';
          head += ' ' + ask;
        }
        return { text: head, products: bd.picks.map(this.slim, this),
          bundle: bd.bundle, ask: ask, meta: { intent: 'bundle', look: this.slots.look } };
      }
    }

    var r = this.cat.search(text, this.filters(), 5);
    if (!r.results.length) r = this.cat.search('', this.filters(), 5);
    if (!r.results.length) {
      return { text: lang === 'en'
        ? "Nothing in the catalogue fits those conditions. Which one matters most — price, size, or style? I'll re-search."
        : '按这些条件，商品里没有合适的。你最在意哪一条——价格、尺寸还是风格？我重新找。',
        products: [], bundle: null, ask: null, meta: { intent: 'no_result' } };
    }

    var prods = r.results.map(this.slim, this);
    var h = lang === 'en' ? 'Here are ' + prods.length + ' that fit.' : '找到 ' + prods.length + ' 件合适的。';
    if (r.meta.relaxed.length) {
      var names = r.meta.relaxed.map(function (k) { return RELAX[lang][k]; }).join(lang === 'zh' ? '、' : ', ');
      h += lang === 'en' ? ' I had to relax your ' + names + ' to find them.'
        : '为了有结果，我放宽了「' + names + '」。';
    }
    var ask2 = null;
    if (!this.slots.price_max && !this.asked.budget && this.turns <= 3) {
      this.asked.budget = 1;
      ask2 = lang === 'en' ? "What's your budget?" : '预算大概多少？人民币就行，我按预算再筛一遍。';
      h += ' ' + ask2;
    }
    return { text: h, products: prods, bundle: null, ask: ask2,
      meta: { intent: 'recommend', matched: r.meta.matched, relaxed: r.meta.relaxed } };
  };

  /* ==================== 对外接口 ==================== */
  var ENGINE = {
    ready: false,
    catalog: null,
    sessions: {},
    USD_CNY: USD_CNY,
    money: money,
    init: function (products) {
      this.catalog = new Catalog(products);
      this.ready = true;
      return this;
    },
    config: function () {
      return {
        brand: { name: 'Fern & Oak', tagline: { zh: '为真实生活做的家具', en: 'Furniture made for actual living' } },
        widget: {
          launcher: { zh: '问问 Nook', en: 'Ask Nook' },
          title: { zh: 'Nook · 导购助手', en: 'Nook · Shopping Concierge' },
          opening: {
            zh: '你好，我是 Nook。你不用想好要买什么——告诉我你想在哪个房间、想解决什么事就行，比如「我想弄个能窝着看书的地方」。',
            en: "Hi, I'm Nook. You don't need to know what you want yet — just tell me the room and what you're trying to solve."
          },
          quick_replies: {
            zh: ['我想弄个能窝着看书的地方', '客厅想换套沙发', '小户型怎么选收纳'],
            en: ['a corner to curl up and read', 'a new sofa for the living room', 'storage ideas for a small flat']
          },
          accent: '#2f6f4e'
        },
        fx: { usd_cny: USD_CNY, note: { zh: money.note('zh'), en: money.note('en') } }
      };
    },
    products: function (lang, category, limit) {
      var c = this.catalog, pool = c.products.filter(function (p) {
        return !category || p.category === category;
      });
      pool = pool.slice().sort(function (a, b) {
        var x = b.rating * Math.sqrt(b.review_count) - a.rating * Math.sqrt(a.review_count);
        return x || (a.sku < b.sku ? -1 : 1);
      });
      var self = this;
      return pool.slice(0, limit || 48).map(function (p) {
        var s = new Session(c, lang);
        return s.slim(p);
      });
    },
    chat: function (payload) {
      var lang = payload.lang === 'en' ? 'en' : 'zh';
      var sid = payload.session_id || 'local';
      var s = this.sessions[sid];
      if (!s || s.lang !== lang) { s = new Session(this.catalog, lang); this.sessions[sid] = s; }
      var r = s.respond(payload.message || '');
      return { session_id: sid, lang: lang, text: r.text, products: r.products,
        bundle: r.bundle, ask: r.ask, meta: r.meta };
    }
  };

  root.NookEngine = ENGINE;
})(typeof window !== 'undefined' ? window : globalThis);
