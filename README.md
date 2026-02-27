# DeFi Research Agent

Automated due diligence reports for DeFi protocols. Type a protocol name, get a structured markdown report with live TVL data, security history, funding rounds, and a 0-10 risk score.

**Stack:** `Python 3 · DeFiLlama API · requests · marked.js`

---

## Why I built this

Evaluating a DeFi protocol properly takes hours: checking TVL trends, hunting for audit reports, reading post-mortems on hacks, scanning governance forums. I kept doing this manually before allocating capital. This agent structures that workflow into a repeatable pipeline and outputs a consistent report every time.

## What a report contains

1. **Executive Summary** Verdict, global score (0-10), top risks, positive signals
2. **On-Chain Findings** TVL, multi-chain deployment, funding history, security incidents, key events
3. **Third-Party Intelligence** Analyst coverage, security audits, community sentiment
4. **Red Flags Register** Severity-ranked risk indicators
5. **Data Limitations** Gaps and areas needing further investigation

Sample output: `reports/aave-2026-02-15.md`, `reports/lido-2026-02-15.md`

## Usage

### CLI
```bash
pip install -r requirements.txt

# Generate a report
python3 main.py aave

# Custom TVL history window
python3 main.py aave --days 90

# Raw JSON output
python3 main.py uniswap --json
```

Reports are saved to `reports/<slug>-<date>.md`.

### Web UI
```bash
python3 web.py
# Open http://localhost:8000
```

Type any protocol name or click a quick-pick card (Aave, Lido, Ethena, Uniswap, Maker). Reports render inline with markdown formatting and can be downloaded as `.md` files.

## Project Structure
```
main.py              CLI entry point
web.py               Web UI server (port 8000)
defillama.py         DeFiLlama API client with caching and fuzzy resolution
report.py            Structured report builder
markdown_report.py   Markdown renderer
web_research.py      Web research module
requirements.txt     Dependencies
reports/             Generated reports (gitignored)
```

## Status

- **DeFiLlama data**: Live (TVL, chains, funding, hacks, hallmarks)
- **Web research**: Template data, live source integration in progress
- **Global Score**: Synthesizes TVL, security, audits, and funding into a 0-10 rating

## GitHub Topics

`defi` `python` `due-diligence` `defillama` `tvl` `risk-assessment` `agent` `crypto` `research`
