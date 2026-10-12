/*!
 * Nook · 统一数据访问层
 * ------------------------------------------------------------------
 * 同一条前端代码，两种运行模式：
 *
 *   服务端模式  →  fetch /api/*           （app/server.py）
 *   静态模式    →  调用 window.NookEngine （GitHub Pages，零服务器）
 *
 * 判据只有一个：window.NookEngine 是否存在、是否 init 完成。
 * 这样 widget 和店铺页都不需要知道自己在哪种模式下运行。
 *
 * 时序：静态模式下 products.json 是异步取回的，页面可能在引擎就绪前就发起查询。
 *      所以所有方法都先过 whenReady() —— 引擎存在但未就绪时挂起，就绪后放行。
 */
(function () {
  'use strict';

  var me = document.currentScript;
  var API = (me && me.dataset && me.dataset.api) || '/api';

  function hasEngine() { return !!window.NookEngine; }
  function isReady() { return hasEngine() && window.NookEngine.ready; }

  function whenReady() {
    if (!hasEngine()) { return Promise.resolve(); }   // 服务端模式：直接放行
    if (isReady()) { return Promise.resolve(); }
    return new Promise(function (res) {
      window.addEventListener('nook:engine-ready', function () { res(); }, { once: true });
    });
  }

  function jget(url) {
    return fetch(url).then(function (r) { return r.json(); });
  }

  window.NookAPI = {
    API: API,
    isStatic: isReady,

    config: function () {
      return whenReady().then(function () {
        if (isReady()) { return window.NookEngine.config(); }
        return jget(API + '/config');
      });
    },

    products: function (lang, category, limit) {
      limit = limit || 48;
      return whenReady().then(function () {
        if (isReady()) {
          var e = window.NookEngine;
          var list = e.products(lang, category, limit);
          return { lang: lang, count: list.length, products: list, fx: e.config().fx };
        }
        var u = API + '/products?lang=' + lang + '&limit=' + limit
          + (category ? '&category=' + encodeURIComponent(category) : '');
        return jget(u);
      });
    },

    chat: function (payload) {
      return whenReady().then(function () {
        if (isReady()) { return window.NookEngine.chat(payload); }
        return fetch(API + '/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        }).then(function (r) { return r.json(); });
      });
    }
  };
})();
