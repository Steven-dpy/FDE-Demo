/*!
 * 跨实现一致性验证 —— 浏览器端（Node 运行）
 * 与 tools/dump_py.py 输出同构的 JSON，用于逐条比对。
 *
 * 用法：  node tools/dump_js.js > .tmp/out_js.json
 *         node tools/dump_js.js portfolio/demo   # 校验打包后的静态版产物
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
// 第二个参数可以指定一个已打包目录（含 static-engine.js + products.json）
const TARGET = process.argv[2] ? path.resolve(process.cwd(), process.argv[2]) : ROOT;

const enginePath = fs.existsSync(path.join(TARGET, 'static-engine.js'))
  ? path.join(TARGET, 'static-engine.js')
  : path.join(ROOT, 'web', 'static-engine.js');
const dataPath = fs.existsSync(path.join(TARGET, 'products.json'))
  ? path.join(TARGET, 'products.json')
  : path.join(ROOT, 'data', 'products.json');

require(enginePath);

const products = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
const queries = JSON.parse(fs.readFileSync(path.join(ROOT, 'tools', 'queries.json'), 'utf8'));

const E = globalThis.NookEngine.init(products);

const out = queries.map(function (q) {
  const sid = 'conf-' + q.id;
  const steps = q.turns.map(function (turn, i) {
    const r = E.chat({ session_id: sid, message: turn, lang: q.lang });
    return {
      step: i + 1,
      intent: r.meta.intent,
      look: r.meta.look || null,
      skus: r.products.map(function (p) { return p.sku; })
    };
  });
  return { id: q.id, lang: q.lang, steps: steps };
});

process.stdout.write(JSON.stringify(out, null, 1));
