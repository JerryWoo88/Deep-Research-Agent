# 🔬 Equity Deep Research Agent

An agentic equity research pipeline that **autonomously gathers data** via web search, yfinance, and SEC filings, then produces a **structured 11-part investment research report** with a final BUY / HOLD / SELL judgment.

> Fork of [Akkao114/Deep-Research-Agent](https://github.com/Akkao114/Deep-Research-Agent), adapted to DeepSeek and to data accuracy: SEC as-filed financials, no truncation of collected data, date anchoring, and an HTML report view. See [本版本的改动](#本版本的改动).

## 🇨🇳 中文快速上手

输入一个股票代码，程序会自动搜集资料（网页、yfinance、SEC 财报原文），用 DeepSeek 写出 11 个部分的中文研报，最后给出 买入/持有/卖出 判断。一份报告大约需要 **1 小时**，并会消耗一定的 DeepSeek 额度。

### 准备

- **Python 3.10 或更高版本**（安装时勾选 "Add Python to PATH"）
- **Git**
- **DeepSeek API key**：在 [platform.deepseek.com](https://platform.deepseek.com) 注册、充值并创建 key
- **能访问境外网站的网络**：SEC、yfinance、DuckDuckGo 都在境外。程序会自动使用系统代理（Windows 的系统代理设置、macOS 的网络代理设置）

### 1. 下载

```bash
git clone https://github.com/JerryWoo88/Deep-Research-Agent.git
cd Deep-Research-Agent
```

### 2. 安装依赖（装在项目自己的虚拟环境里，不影响电脑上其他 Python 项目）

Windows（PowerShell）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

macOS / Linux：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

### 3. 填写 API key

把 `.env.example` 复制一份，改名为 `.env`（Windows：`copy .env.example .env`；macOS：`cp .env.example .env`），用记事本打开并填写：

```
OPENAI_API_KEY=你的 DeepSeek key（sk- 开头）
API_BASE_URL=https://api.deepseek.com/v1
SEC_USER_AGENT=你的名字 你的邮箱
```

- `OPENAI_API_KEY` 这个名字不要改：DeepSeek 用的是 OpenAI 兼容接口，程序从这个变量读 key。
- `SEC_USER_AGENT` 是 SEC 要求的访问者身份，必须填，否则读不到美股财报原文。
- `.env` 只在你自己电脑上，不会被上传到 GitHub。不要把 key 发给别人。

### 4. 运行

Windows：

```powershell
.\.venv\Scripts\python.exe main.py --mode deep FIG
```

macOS / Linux：

```bash
.venv/bin/python main.py --mode deep FIG
```

把 `FIG` 换成任意股票代码：美股如 `AAPL`、`TEM`，港股如 `0700.HK`。

运行过程：

1. 先检查三个 DeepSeek 模型能否连通（看到三个 ✅ 才继续）。
2. 先做第 4 部分「公司基本面」预览，浏览器会自动打开网页版。确认研究的是对的公司，回到终端输入 `y` 回车继续。
3. 依次完成其余部分和最终判断（约 1 小时），完成后浏览器再次打开完整报告。

### 结果在哪

`reports/` 文件夹：

- `代码_日期.html`：网页版，带目录、表格、每部分的原始资料和全部来源链接（推荐看这个）
- `代码_日期.md`：纯文本版
- `代码_日期.json`：结论（信号、置信度、使用的模型）

### 注意事项

- **运行期间电脑不要睡眠、不要关机、不要关终端窗口。** 中断后在**同一天**重新运行同一条命令，会从已完成的部分接着跑；第二天再跑会从头开始（进度文件名带日期）。想强制从头开始，加 `--no-resume`。
- 终端里出现 `[WARN] Part X hit tool call limit (40)` 是正常提示：这部分查资料的次数用满了，程序会用已查到的资料继续，不是错误。
- 美股的财务数字直接来自 SEC 申报，最可靠。港股没有 SEC 数据，主要依赖 yfinance 和网页，可信度较低。
- `.json` 里的 `cost_usd` 是按原项目默认价格估算的，不准；实际费用看 DeepSeek 控制台。
- 同一只股票跑两次，结论和置信度可能不同；关键数字请按报告里注明的出处核对。**本工具不构成投资建议。**

### 本版本的改动

- **模型**：DeepSeek。搜集资料用 `deepseek-chat`（flash，不思考）；提取数据用 `deepseek-flash`（思考）；写报告和最终判断用 `deepseek-v4-pro`（思考）；执行摘要用 `deepseek-v4-pro`（不思考）。在 `model-router/router_config.py` 修改。
- **修复原项目的错误**：搜索库包名（`ddgs`）；SEC 网页 403；SEC 文件列表只看最近 100 份导致找不到年报；提取数据只读约 20–30% 的资料、最终判断读不到估值章节。
- **新增工具**：`get_sec_financial_data`（SEC 申报的财务数据）、`get_insider_trading`（高管/董事持股变动汇总）；`get_sec_filings` 只列关键财报、业绩公告（附新闻稿链接）和人员变动；`read_url` 可按关键词跳转、分页读长文件。
- **准确性**：告诉模型今天的日期并要求以工具数据为准；写作规则禁止空话、要求每个判断带数字和出处；模型返回空答案时自动重试，仍为空则报错，不会写进报告。
- **网页版报告**：`viewer.py`，研究过程中每完成一部分自动更新。也可以手动生成：`python viewer.py FIG`。

## ✨ Features

- **Fully autonomous** — the agent iteratively calls 6 built-in tools to research each section
- **11-part report structure** — covering industry landscape, company fundamentals, financials, governance, valuation, and more
- **Preview mode** — Part 4 (Company Fundamentals) runs first for sanity check before the full research begins
- **Checkpoint & resume** — each completed part is saved to disk; interrupted runs can be seamlessly resumed
- **Configurable model tiers** — supports Gemini, Claude, or any OpenAI-compatible API via a pluggable model router
- **Pre-flight API check** — verifies all model endpoints before starting long runs
- **Anti-hallucination guardrails** — target-lock and anti-fabrication rules built into prompts

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Research Agent                         │
│                                                          │
│  ┌──────────┐   ┌───────────┐   ┌────────┐   ┌───────┐ │
│  │ Research  │──▶│ Extraction│──▶│ Writing│──▶│ Judge │ │
│  │   Loop    │   │  (low)    │   │ (high) │   │(high) │ │
│  │ (medium)  │   └───────────┘   └────────┘   └───────┘ │
│  └────┬──────┘                                           │
│       │                                                  │
│  ┌────▼──────────────────────────────────┐               │
│  │            6 Built-in Tools            │               │
│  │ web_search │ stock_info │ financials   │               │
│  │ sec_filings│ read_url   │ read_local   │               │
│  └───────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────┘
```

### Report Structure (11 Parts)

| Part | Title | Key Content |
|:---:|---|---|
| 1 | Core Narrative | Industry changes, company response, market perception |
| 2 | Industry Landscape | Market size, competition landscape |
| 3 | Comparable Company Study | Peer selection, returns, business quality |
| 4 | **Company Fundamentals** ⭐ | Company intro, competitive advantages *(preview first)* |
| 5 | Financial Deep Dive | Revenue, margins, cash flow analysis |
| 6 | Capacity & CAPEX | Capital expenditure analysis |
| 7 | Governance & Returns | Management credibility, shareholder returns |
| 8 | Growth Drivers | Growth drivers across stages |
| 9 | Price Review | Stock price movement analysis |
| 10 | Valuation & Timing | Valuation methods, buy/sell points |
| 11 | Synthesis | **BUY / HOLD / SELL** judgment |

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/JerryWoo88/Deep-Research-Agent.git
cd Deep-Research-Agent
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> The `model-router/` directory is included in the repo and installed in editable mode.

### 3. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your actual API keys
```

**Required:**
| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | DeepSeek API key (any OpenAI-compatible provider works) |
| `API_BASE_URL` | Provider endpoint, e.g. `https://api.deepseek.com/v1` |
| `SEC_USER_AGENT` | SEC EDGAR identity (e.g. `YourName email@example.com`); SEC rejects requests without one |

**Optional:**
| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Only if a tier uses Gemini directly |
| `ANTHROPIC_API_KEY` | Only if a tier uses Claude (`provider: "anthropic"`) |

### 4. Run

```bash
# Interactive mode
python main.py

# CLI mode
python main.py --mode deep AAPL
python main.py --mode deep 2698.HK
python main.py --mode deep "some company name"

# Resume after interruption (automatic)
python main.py --mode deep AAPL

# Force fresh start
python main.py --mode deep AAPL --no-resume
```

## ⚙️ Configuration

### Research Parameters (`config.py`)

| Variable | Default | Description |
|---|---|---|
| `MAX_TOOL_CALLS_PER_PART` | `40` | Max tool calls per research part |
| `MAX_MESSAGES_PER_PART` | `45` | Max LLM round-trips per part |
| `TOOL_RESULT_LLM_CHARS` / `TOOL_RESULT_RAW_CHARS` | `20000` | Chars kept per tool result |
| `EXTRACTION_RAW_CHARS` / `JUDGMENT_REPORT_CHARS` | `1000000` | Effectively no truncation |
| `RESEARCH_MAX_TOKENS` / `WRITING_MAX_TOKENS` / `JUDGMENT_MAX_TOKENS` | `32000` | Includes thinking tokens |
| `EXTRACTION_MAX_TOKENS` | `64000` | Includes thinking tokens |

### Model Routing (`model-router/router_config.py`)

| Tier | Model | Thinking | Usage |
|---|---|---|---|
| `medium` | `deepseek-chat` (flash) | off | Research loop (tool-calling) |
| `low` | `deepseek-flash` | on | Data extraction / conflict checks |
| `high` | `deepseek-v4-pro` | on | Report writing, final judgment |
| `summary` | `deepseek-v4-pro` | off | Executive summary |

Backup `MODEL_MAP` blocks for Gemini and Claude are kept (commented out) in `router_config.py`.

## 📁 Project Structure

```
research-agent/
├── main.py                 # CLI entry point & target resolution
├── agent.py                # Core agentic loop
├── config.py               # Centralized configuration
├── prompts.py              # Prompt templates & part definitions
├── schemas.py              # Pydantic data models
├── state.py                # Checkpoint & report management
├── tools.py                # 6 research tools + dispatcher
├── utils.py                # Logging & message formatting
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── modes/
│   └── deep_research_review.md  # Research framework (customizable)
├── model-router/           # Pluggable model routing layer
│   ├── router.py
│   ├── router_config.py
│   └── setup.py
├── reports/                # Generated reports (gitignored)
└── data/                   # Checkpoints (gitignored)
```

## 🔧 Customization

### Research Framework
Edit `modes/deep_research_review.md` to customize:
- Add, remove, or reorder research parts
- Change the industry focus or constraints
- Modify language or objectivity rules

Changes take effect immediately — no code modifications needed.

### Adding New Tools
Add tool definitions to `TOOL_DEFINITIONS` in `tools.py` and implement the corresponding function. Register it in `TOOL_DISPATCH`.

## 📄 Output

Reports are saved as Markdown + JSON metadata:
```
reports/AAPL_2026-03-18.md     # Full research report
reports/AAPL_2026-03-18.json   # Signal, cost, models used
```

## ⚠️ Disclaimer

This tool is for **research and educational purposes only**. It does not constitute investment advice. The AI-generated analysis may contain errors or hallucinations despite built-in guardrails. Always verify findings with primary sources before making any investment decisions.

## 📜 License

MIT
