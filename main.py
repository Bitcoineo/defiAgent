"""DeFi research agent — Phase 1: DeFiLlama data reports."""

import argparse
import json
import sys

from defillama import DefiLlamaClient, DefiLlamaAPIError, ProtocolNotFoundError
from report import build_report
from web_research import (
    search_analyst_coverage,
    search_audit_reports,
    search_community_sentiment,
    search_red_flags,
)


def run_report(client, protocol_name, tvl_days=30):
    """Orchestrate API calls and build a structured report dict."""
    meta = client.resolve_protocol(protocol_name)
    detail = client.get_protocol_detail(meta["slug"])

    child_names = [c["name"] for c in meta["children"]]
    hacks = client.find_hacks_for_protocol(meta["name"], child_names)

    web_research = {
        "analyst_coverage": search_analyst_coverage(meta["name"]),
        "audit_reports": search_audit_reports(meta["name"]),
        "community_sentiment": search_community_sentiment(meta["name"]),
        "red_flags": search_red_flags(meta["name"]),
    }

    return build_report(detail, meta, hacks, tvl_history_days=tvl_days, web_research=web_research)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a DeFi protocol research report from DeFiLlama data."
    )
    parser.add_argument("protocol", help="Protocol name (e.g., 'aave', 'uniswap', 'lido')")
    parser.add_argument("--days", type=int, default=30, help="Days of TVL history (default: 30)")
    parser.add_argument("--json", action="store_true", dest="raw_json", help="Output raw JSON")
    args = parser.parse_args()

    client = DefiLlamaClient()

    try:
        report = run_report(client, args.protocol, tvl_days=args.days)
    except ProtocolNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except DefiLlamaAPIError as e:
        print(f"API Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.raw_json:
        print(json.dumps(report))
    else:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
