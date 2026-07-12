"""Scrape client: proxy rotation + trailing-window rate limiter for stats.wnba.com.

Python port of the R side's ``R/utils.R`` (``get_proxy_ips`` / ``next_proxy`` /
``rate_limit``), reused verbatim from hoopR-nba-stats-data's
``nba_data_build/scrape/`` (proxy rotation + rate limiting are stats-API-host-
agnostic).
"""

from __future__ import annotations

from .leaguedash import LeagueDashClient, build_mega, megas, season_str, variants
from .proxy import RoundRobin, load_proxies, redact
from .rate_limit import TokenBucket

__all__ = [
    "LeagueDashClient",
    "build_mega",
    "megas",
    "season_str",
    "variants",
    "RoundRobin",
    "load_proxies",
    "redact",
    "TokenBucket",
]
