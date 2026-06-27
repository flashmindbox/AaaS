// Minimal DOM shim + regex extraction to smoke-test the dyslexia helpers
// in isolation. Not a replacement for real browser testing, but verifies
// that injectDyslexiaStyles/removeDyslexiaStyles toggle the HTML attribute
// and the <style> element, and that localStorage round-trips.
//
// Run:  node apps/widget/tests/dyslexia_smoke.js

const fs = require("fs");
const path = require("path");

const WIDGET = path.resolve(__dirname, "..", "src", "widget.js");
const src = fs.readFileSync(WIDGET, "utf-8");

class FakeEl {
  constructor(tag) {
    this.tag = tag;
    this._id = "";
    this.textContent = "";
    this.children = [];
    this.attrs = {};
    this.parent = null;
  }
  setAttribute(k, v) {
    this.attrs[k] = v;
  }
  removeAttribute(k) {
    delete this.attrs[k];
  }
  getAttribute(k) {
    return this.attrs[k];
  }
  appendChild(c) {
    this.children.push(c);
    c.parent = this;
  }
  remove() {
    if (this.parent) {
      this.parent.children = this.parent.children.filter((c) => c !== this);
    }
  }
}

const byId = {};
const html = new FakeEl("html");
const head = new FakeEl("head");
html.appendChild(head);

const fakeDoc = {
  documentElement: html,
  head,
  getElementById(id) {
    return byId[id] || null;
  },
  createElement(tag) {
    const el = new FakeEl(tag);
    Object.defineProperty(el, "id", {
      get() {
        return this._id || "";
      },
      set(v) {
        this._id = v;
        if (v) byId[v] = this;
      },
    });
    const origRemove = el.remove.bind(el);
    el.remove = () => {
      if (el._id) delete byId[el._id];
      origRemove();
    };
    return el;
  },
};
global.document = fakeDoc;
global.window = {
  localStorage: {
    _s: {},
    getItem(k) {
      return this._s[k] || null;
    },
    setItem(k, v) {
      this._s[k] = v;
    },
    removeItem(k) {
      delete this._s[k];
    },
  },
};

function extractFn(name) {
  const re = new RegExp("function\\s+" + name + "[\\s\\S]*?^  \\}", "m");
  const m = src.match(re);
  if (!m) throw new Error("could not extract " + name);
  return m[0];
}

const cssM = src.match(/const DYSLEXIA_CSS = `[\s\S]*?`;/);
if (!cssM) throw new Error("could not find DYSLEXIA_CSS");

const code =
  "const LS_DYSLEXIA = 'aaas.dyslexia.v1';\n" +
  cssM[0] +
  "\n" +
  extractFn("injectDyslexiaStyles") +
  "\n" +
  extractFn("removeDyslexiaStyles") +
  "\n" +
  extractFn("getStoredFlag") +
  "\n" +
  extractFn("setStoredFlag") +
  "\n" +
  "module.exports = { injectDyslexiaStyles, removeDyslexiaStyles, getStoredFlag, setStoredFlag, LS_DYSLEXIA };";

const mod = { exports: {} };
new Function("module", code)(mod);
const {
  injectDyslexiaStyles,
  removeDyslexiaStyles,
  getStoredFlag,
  setStoredFlag,
  LS_DYSLEXIA,
} = mod.exports;

const results = [];
function check(name, ok) {
  results.push({ name, ok });
  console.log((ok ? "  PASS " : "  FAIL ") + name);
}

injectDyslexiaStyles();
check("html attribute set after inject", html.attrs["data-aaas-dyslexia"] === "true");
check("style element in head after inject", head.children.some((c) => c.id === "__aaas_dyslexia__"));
check("style textContent non-empty", head.children.find((c) => c.id === "__aaas_dyslexia__").textContent.length > 100);

removeDyslexiaStyles();
check("html attribute removed", !("data-aaas-dyslexia" in html.attrs));
check("style element removed from head", !head.children.some((c) => c.id === "__aaas_dyslexia__"));

injectDyslexiaStyles();
injectDyslexiaStyles();
const styleCount = head.children.filter((c) => c.id === "__aaas_dyslexia__").length;
check("double-inject idempotent (exactly one style)", styleCount === 1);

removeDyslexiaStyles();
setStoredFlag(LS_DYSLEXIA, true);
check("flag round-trip: set true -> get true", getStoredFlag(LS_DYSLEXIA) === true);
setStoredFlag(LS_DYSLEXIA, false);
check("flag round-trip: set false -> get false", getStoredFlag(LS_DYSLEXIA) === false);

const fails = results.filter((r) => !r.ok);
console.log("");
console.log(fails.length === 0 ? "OK — all " + results.length + " checks passed" : "FAIL — " + fails.length + " of " + results.length + " failed");
process.exit(fails.length === 0 ? 0 : 1);
