// Minimal DOM shim + regex extraction to smoke-test the reading-ruler
// helpers in isolation (same approach as dyslexia_smoke.js). Verifies
// that enable/disable create and tear down exactly one overlay element
// and that every listener registered on enable is removed on disable
// with the same function reference.
//
// Run:  node apps/widget/tests/ruler_smoke.js

const fs = require("fs");
const path = require("path");

const WIDGET = path.resolve(__dirname, "..", "src", "widget.js");
const src = fs.readFileSync(WIDGET, "utf-8");

class FakeEl {
  constructor(tag) {
    this.tag = tag;
    this.id = "";
    this.style = {};
    this.children = [];
    this.attrs = {};
    this.parent = null;
    this.listeners = [];
  }
  setAttribute(k, v) {
    this.attrs[k] = v;
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
  addEventListener(type, fn) {
    this.listeners.push({ type, fn });
  }
  removeEventListener(type, fn) {
    this.listeners = this.listeners.filter((l) => !(l.type === type && l.fn === fn));
  }
}

const html = new FakeEl("html");
const body = new FakeEl("body");

const docListeners = [];
const fakeDoc = {
  documentElement: html,
  body,
  createElement(tag) {
    return new FakeEl(tag);
  },
  addEventListener(type, fn) {
    docListeners.push({ type, fn });
  },
  removeEventListener(type, fn) {
    for (let i = docListeners.length - 1; i >= 0; i--) {
      if (docListeners[i].type === type && docListeners[i].fn === fn) {
        docListeners.splice(i, 1);
      }
    }
  },
};
global.document = fakeDoc;
global.window = { innerHeight: 800 };
global.requestAnimationFrame = (fn) => {
  fn();
  return 0;
};

function extractFn(name) {
  const re = new RegExp("function\\s+" + name + "[\\s\\S]*?^  \\}", "m");
  const m = src.match(re);
  if (!m) throw new Error("could not extract " + name);
  return m[0];
}

const stateM = src.match(/const RULER_BAND_PX[\s\S]*?let _rulerLeave = null;/);
if (!stateM) throw new Error("could not find ruler state declarations");

const code =
  stateM[0] +
  "\n" +
  extractFn("positionRuler") +
  "\n" +
  extractFn("enableReadingRuler") +
  "\n" +
  extractFn("disableReadingRuler") +
  "\n" +
  "module.exports = { positionRuler, enableReadingRuler, disableReadingRuler, RULER_BAND_PX };";

const mod = { exports: {} };
new Function("module", code)(mod);
const { positionRuler, enableReadingRuler, disableReadingRuler } = mod.exports;

const results = [];
function check(name, ok) {
  results.push({ name, ok });
  console.log((ok ? "  PASS " : "  FAIL ") + name);
}

enableReadingRuler();
const bands = body.children.filter((c) => c.id === "__aaas_ruler__");
check("enable appends one ruler element to body", bands.length === 1);
check("ruler is click-through", bands[0] && bands[0].style.cssText.includes("pointer-events:none"));
check("ruler starts hidden", bands[0] && bands[0].style.cssText.includes("visibility:hidden"));
check("doc listeners registered (mousemove + focusin)", docListeners.length === 2);
check("mouseleave listener on documentElement", html.listeners.length === 1);

enableReadingRuler();
check("double-enable idempotent (still one element)", body.children.filter((c) => c.id === "__aaas_ruler__").length === 1);
check("double-enable adds no extra listeners", docListeners.length === 2 && html.listeners.length === 1);

positionRuler(400);
const band = body.children.find((c) => c.id === "__aaas_ruler__");
check("positionRuler shows the band", band.style.visibility === "visible");
check("positionRuler centers the band", band.style.transform.includes("translate3d(0,345px,0)"));
positionRuler(-5000);
check("positionRuler clamps above viewport", band.style.transform.includes("-110px"));

disableReadingRuler();
check("disable removes the element", body.children.filter((c) => c.id === "__aaas_ruler__").length === 0);
check("disable removes doc listeners by reference", docListeners.length === 0);
check("disable removes documentElement listener", html.listeners.length === 0);

disableReadingRuler();
check("double-disable is safe", true);

const fails = results.filter((r) => !r.ok);
console.log("");
console.log(fails.length === 0 ? "OK — all " + results.length + " checks passed" : "FAIL — " + fails.length + " of " + results.length + " failed");
process.exit(fails.length === 0 ? 0 : 1);
