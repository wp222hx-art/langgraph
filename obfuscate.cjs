#!/usr/bin/env node
/**
 * Paydaes ClaimGPT · 前端混淆构建流水线
 * ────────────────────────────────────────────
 * 输入(可读源码):  static/src/*.js
 * 输出(混淆产物):  static/*.js   ← 浏览器实际加载这个
 *
 * 两步:terser 压缩 → javascript-obfuscator 混淆
 * 运行:  node obfuscate.cjs
 */
const fs = require('fs');
const path = require('path');
const { minify } = require('terser');
const JavaScriptObfuscator = require('javascript-obfuscator');

const SRC = path.join(__dirname, 'static', 'src');
const OUT = path.join(__dirname, 'static');

// 文件 → 强度档位
//   high  : 核心业务逻辑(app.js)— 体量大,关闭控制流扁平化避免卡顿,其余全开
//   heavy : 文案/帮助(i18n.js / help.js)— 体量小,可开控制流扁平化
const FILES = [
  { name: 'app.js',  level: 'high'  },
  { name: 'i18n.js', level: 'heavy' },
  { name: 'help.js', level: 'heavy' },
];

// ── 混淆参数:档位配置 ──
function obfOptions(level) {
  const base = {
    compact: true,
    simplify: true,
    // 字符串处理:全部打散进数组 + Base64/RC4 编码
    stringArray: true,
    stringArrayEncoding: ['base64', 'rc4'],
    stringArrayThreshold: 1,
    stringArrayWrappersCount: 3,
    stringArrayWrappersType: 'function',
    stringArrayWrappersParametersMaxCount: 4,
    splitStrings: true,
    splitStringsChunkLength: 8,
    // 标识符乱码化(变量/函数名 → 十六进制)
    identifierNamesGenerator: 'hexadecimal',
    renameGlobals: false,            // 关:避免破坏 window.xxx 全局桥接
    // 数字编码 + 死代码注入
    numbersToExpressions: true,
    transformObjectKeys: true,
    unicodeEscapeSequence: false,    // 关:中文文案保持可编码,体积可控
    // 反调试 / 自我保护
    debugProtection: true,
    debugProtectionInterval: 2000,
    selfDefending: true,
    disableConsoleOutput: true,
  };
  if (level === 'high') {
    // app.js:154KB,控制流扁平化全开会拖慢首屏,折中处理
    return { ...base,
      controlFlowFlattening: true,
      controlFlowFlatteningThreshold: 0.4,
      deadCodeInjection: true,
      deadCodeInjectionThreshold: 0.2,
    };
  }
  // heavy:小文件,可全力压
  return { ...base,
    controlFlowFlattening: true,
    controlFlowFlatteningThreshold: 0.75,
    deadCodeInjection: true,
    deadCodeInjectionThreshold: 0.4,
  };
}

(async () => {
  console.log('🌀 Paydaes ClaimGPT 前端混淆流水线启动\n');
  let totalSrc = 0, totalOut = 0;
  for (const { name, level } of FILES) {
    const srcPath = path.join(SRC, name);
    const outPath = path.join(OUT, name);
    if (!fs.existsSync(srcPath)) {
      console.log(`⚠️  跳过(源码不存在): src/${name}`);
      continue;
    }
    const code = fs.readFileSync(srcPath, 'utf8');
    const srcSize = Buffer.byteLength(code, 'utf8');

    // ── 第一步:terser 压缩(去注释/空白/缩短局部名) ──
    const min = await minify(code, {
      compress: { drop_console: false, passes: 2 },
      mangle: true,
      format: { comments: false },
    });
    if (min.error) throw min.error;

    // ── 第二步:javascript-obfuscator 混淆 ──
    const obf = JavaScriptObfuscator.obfuscate(min.code, obfOptions(level));
    const out = obf.getObfuscatedCode();
    fs.writeFileSync(outPath, out, 'utf8');

    const outSize = Buffer.byteLength(out, 'utf8');
    totalSrc += srcSize; totalOut += outSize;
    console.log(`✅ ${name.padEnd(10)} [${level}]  ${(srcSize/1024).toFixed(1)}KB → ${(outSize/1024).toFixed(1)}KB`);
  }
  console.log(`\n📦 合计  ${(totalSrc/1024).toFixed(1)}KB → ${(totalOut/1024).toFixed(1)}KB`);
  console.log('🔒 混淆完成,产物已写入 static/  (源码保留在 static/src/)');
})().catch(e => { console.error('❌ 混淆失败:', e); process.exit(1); });
