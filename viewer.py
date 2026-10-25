"""Render research progress / final report as a standalone HTML page.

The page is rebuilt from the checkpoint after every completed Part, so it can
be left open in a browser while research runs (it auto-refreshes).

CLI:
    python viewer.py FIG            # build + open the latest page for FIG
    python viewer.py 2698.HK --no-open
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import webbrowser
from pathlib import Path

from config import DATA_DIR, REPORTS_DIR
from prompts import PARTS

URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")

PAGE_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.1.6/purify.min.js"></script>
<style>
:root {
  --bg: #f7f7f5; --panel: #ffffff; --text: #1d1d1f; --muted: #6e6e73;
  --border: #e3e3e0; --accent: #2f6fde; --ok: #1f8a4c; --warn: #c2410c; --code: #f1f1ef;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #161618; --panel: #1e1e21; --text: #e8e8ea; --muted: #9a9aa0;
    --border: #2e2e33; --accent: #6ea0ff; --ok: #4ade80; --warn: #fb923c; --code: #26262a;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
  font: 15px/1.7 -apple-system, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif; }
header { position: sticky; top: 0; z-index: 2; background: var(--panel);
  border-bottom: 1px solid var(--border); padding: 12px 24px; display: flex;
  flex-wrap: wrap; gap: 8px 20px; align-items: baseline; }
header h1 { font-size: 18px; margin: 0; }
header .meta { color: var(--muted); font-size: 13px; }
header .signal { font-weight: 700; }
header label { margin-left: auto; font-size: 13px; color: var(--muted); cursor: pointer; }
.layout { display: grid; grid-template-columns: 240px minmax(0, 1fr); max-width: 1280px; margin: 0 auto; }
nav { position: sticky; top: 58px; align-self: start; max-height: calc(100vh - 58px);
  overflow: auto; padding: 16px 8px 16px 16px; font-size: 13px; }
nav a { display: flex; gap: 6px; padding: 5px 8px; border-radius: 6px; color: var(--text); text-decoration: none; }
nav a:hover { background: var(--code); }
nav a.pending { color: var(--muted); }
nav .dot { width: 14px; flex: none; text-align: center; }
main { padding: 16px 24px 80px; min-width: 0; }
section.part { background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
  padding: 8px 24px 16px; margin-bottom: 20px; scroll-margin-top: 70px; }
section.part.pending { color: var(--muted); padding: 12px 24px; }
section.part > h2 { font-size: 17px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
.md table { border-collapse: collapse; display: block; overflow-x: auto; margin: 12px 0; font-size: 14px; }
.md th, .md td { border: 1px solid var(--border); padding: 6px 10px; vertical-align: top; }
.md th { background: var(--code); }
.md code { background: var(--code); padding: 1px 4px; border-radius: 4px; }
.md blockquote { margin: 8px 0; padding: 4px 14px; border-left: 3px solid var(--accent); color: var(--muted); }
details { margin-top: 10px; border-top: 1px dashed var(--border); padding-top: 8px; }
summary { cursor: pointer; color: var(--accent); font-size: 14px; }
.chunk { background: var(--code); border-radius: 8px; padding: 10px 12px; margin: 8px 0;
  white-space: pre-wrap; word-break: break-word; font: 12.5px/1.55 Consolas, Menlo, monospace; max-height: 420px; overflow: auto; }
.chunk .tool { color: var(--warn); font-weight: 700; }
.sources li { word-break: break-all; font-size: 13px; }
a { color: var(--accent); }
.ok { color: var(--ok); } .bad { color: var(--warn); }
@media (max-width: 800px) {
  .layout { grid-template-columns: 1fr; }
  nav { position: static; max-height: none; padding: 12px 16px 0; }
  main { padding: 12px 16px 60px; }
  section.part { padding: 6px 14px 12px; }
}
</style>
</head>
<body>
<header>
  <h1>__TITLE__</h1>
  <span class="meta">__META__</span>
  __REFRESH_TOGGLE__
</header>
<div class="layout">
  <nav>__NAV__</nav>
  <main>__MAIN__</main>
</div>
<script>
document.querySelectorAll("script.md-src").forEach(function (s) {
  var target = document.getElementById(s.dataset.target);
  var text = JSON.parse(s.textContent);
  if (window.marked && window.DOMPurify) {
    target.innerHTML = DOMPurify.sanitize(marked.parse(text));
  } else {
    target.textContent = text;  // offline fallback
    target.style.whiteSpace = "pre-wrap";
  }
});
(function () {
  var box = document.getElementById("autorefresh");
  if (!box) return;
  var KEY = "rv-scroll:" + location.pathname;
  try {
    var y = sessionStorage.getItem(KEY);
    if (y) window.scrollTo(0, parseInt(y, 10));
    box.checked = sessionStorage.getItem(KEY + ":off") !== "1";
  } catch (e) {}
  box.addEventListener("change", function () {
    try { sessionStorage.setItem(KEY + ":off", box.checked ? "0" : "1"); } catch (e) {}
  });
  setInterval(function () {
    if (!box.checked) return;
    try { sessionStorage.setItem(KEY, String(window.scrollY)); } catch (e) {}
    location.reload();
  }, 30000);
})();
</script>
</body>
</html>
"""


def _md_block(text: str, block_id: str) -> str:
    """Embed markdown as JSON; it is rendered (and sanitized) in the browser."""
    payload = json.dumps(text, ensure_ascii=False).replace("</", "<\\/")
    return (f'<div class="md" id="{block_id}"></div>'
            f'<script type="application/json" class="md-src" data-target="{block_id}">{payload}</script>')


def _linkify(escaped: str) -> str:
    return URL_RE.sub(lambda m: f'<a href="{m.group(0)}" target="_blank" rel="noopener">{m.group(0)}</a>', escaped)


def _raw_chunks_html(raw: str) -> str:
    out = []
    for chunk in raw.split("\n\n---\n\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        esc = html.escape(chunk)
        esc = re.sub(r"^\[(\w+)\]", r'<span class="tool">[\1]</span>', esc)
        out.append(f'<div class="chunk">{_linkify(esc)}</div>')
    return "\n".join(out)


def _sources(raw: str) -> list[str]:
    seen: dict[str, None] = {}
    for u in URL_RE.findall(raw):
        seen.setdefault(u.rstrip(".,;"), None)
    return list(seen)


def _executive_summary(report_md: Path) -> str:
    """Executive summary is the text before the report header in the final .md."""
    text = report_md.read_text(encoding="utf-8")
    idx = text.find("\n# ")
    return text[:idx].rstrip().rstrip("-").rstrip() if idx > 0 else ""


def build_html(checkpoint_path: Path, report_md: Path | None = None) -> Path:
    cp = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    target = cp.get("target", {})
    name = target.get("ticker") or target.get("raw_input", "report").replace(" ", "_")
    company = target.get("company_name") or target.get("raw_input", "")
    day = cp.get("date", "")

    report_parts = {int(k): v for k, v in cp.get("report_parts", {}).items()}
    research = {p["part_id"]: p for p in cp.get("parts", [])}
    failed = set(cp.get("failed_part_ids", []))
    done = set(cp.get("completed_part_ids", []))
    total = len(PARTS)
    finished = report_md is not None and report_md.exists()

    signal = ""
    if 11 in report_parts:
        head = report_parts[11][:300]
        m = re.search(r"\b(BUY|HOLD|SELL)\b", head)
        if m:
            signal = m.group(1)
        c = re.search(r"Confidence:\s*(\d+)%", head)
        if c:
            signal += f" · 置信度 {c.group(1)}%"

    meta_bits = [f"{name}", day, f"进度 {len(done)}/{total}" + (" · 已完成" if finished else " · 研究中…")]
    if signal:
        meta_bits.insert(0, f'<span class="signal">{html.escape(signal)}</span>')
    models = cp.get("models_used") or {}
    if models:
        meta_bits.append("模型 " + " / ".join(f"{k}: {v}" for k, v in models.items()))
    meta_bits.append(f"tokens {cp.get('total_input_tokens', 0):,} in / {cp.get('total_output_tokens', 0):,} out")

    nav, main = [], []

    summary_text = _executive_summary(report_md) if finished else ""
    if summary_text:
        nav.append('<a href="#summary"><span class="dot ok">★</span>执行摘要</a>')
        main.append(f'<section class="part" id="summary"><h2>执行摘要</h2>{_md_block(summary_text, "md-summary")}</section>')

    all_sources: dict[str, None] = {}
    for part_id, title, _desc in PARTS:
        anchor = f"part{part_id}"
        if part_id in report_parts:
            dot, cls = '<span class="dot ok">✓</span>', ""
        elif part_id in failed:
            dot, cls = '<span class="dot bad">✗</span>', "pending"
        else:
            dot, cls = '<span class="dot">○</span>', "pending"
        nav.append(f'<a class="{cls}" href="#{anchor}">{dot}{part_id}. {html.escape(title)}</a>')

        if part_id not in report_parts:
            status = "研究失败" if part_id in failed else "尚未完成"
            main.append(f'<section class="part pending" id="{anchor}">Part {part_id} · {html.escape(title)} — {status}</section>')
            continue

        body = [f'<section class="part" id="{anchor}">', _md_block(report_parts[part_id], f"md-{part_id}")]
        r = research.get(part_id)
        if r:
            srcs = _sources(r.get("raw_data", ""))
            for s in srcs:
                all_sources.setdefault(s, None)
            if r.get("summary"):
                body.append(f'<details><summary>提取的关键数据</summary>{_md_block(r["summary"], f"md-sum-{part_id}")}</details>')
            if r.get("raw_data"):
                body.append(f'<details><summary>原始搜集资料（{len(srcs)} 个链接）</summary>{_raw_chunks_html(r["raw_data"])}</details>')
        body.append("</section>")
        main.append("\n".join(body))

    if all_sources:
        nav.append('<a href="#sources"><span class="dot">🔗</span>全部资料来源</a>')
        items = "".join(f'<li><a href="{html.escape(u)}" target="_blank" rel="noopener">{html.escape(u)}</a></li>'
                        for u in all_sources)
        main.append(f'<section class="part" id="sources"><h2>全部资料来源（{len(all_sources)}）</h2><ol class="sources">{items}</ol></section>')

    toggle = "" if finished else '<label><input type="checkbox" id="autorefresh" checked> 每 30 秒自动刷新</label>'
    title = html.escape(f"{company} ({name})" if company and company != name else name)
    page = (PAGE_TEMPLATE
            .replace("__TITLE__", title)
            .replace("__META__", " · ".join(meta_bits))
            .replace("__REFRESH_TOGGLE__", toggle)
            .replace("__NAV__", "\n".join(nav))
            .replace("__MAIN__", "\n".join(main)))

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / f"{name}_{day}.html"
    out.write_text(page, encoding="utf-8")
    return out


def open_in_browser(path: Path) -> None:
    try:
        webbrowser.open(path.resolve().as_uri())
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the HTML view of a research run")
    parser.add_argument("target", help="Ticker or name used for the run, e.g. FIG or 2698.HK")
    parser.add_argument("--no-open", action="store_true", help="Only build, don't open the browser")
    args = parser.parse_args()

    name = args.target.strip().upper().replace(" ", "_")
    checkpoints = sorted(DATA_DIR.glob(f"checkpoint_{name}_*.json"))
    if not checkpoints:
        print(f"No checkpoint found for {name} in {DATA_DIR}")
        sys.exit(1)
    cp = checkpoints[-1]
    day = cp.stem.rsplit("_", 1)[-1]
    out = build_html(cp, REPORTS_DIR / f"{name}_{day}.md")
    print(f"HTML: {out}")
    if not args.no_open:
        open_in_browser(out)


if __name__ == "__main__":
    main()
