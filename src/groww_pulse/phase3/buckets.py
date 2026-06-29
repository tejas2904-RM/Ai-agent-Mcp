"""Seed theme buckets for Groww review clustering."""

from __future__ import annotations

from dataclasses import dataclass

from groww_pulse.phase1.models import NormalizedReview


@dataclass(frozen=True)
class SeedTheme:
    key: str
    name: str
    keywords: tuple[str, ...]


SEED_THEMES: tuple[SeedTheme, ...] = (
    SeedTheme(
        "trading_orders",
        "Trading & orders",
        (
            "order",
            "trade",
            "trading",
            "execute",
            "buy",
            "sell",
            "demat",
            "fno",
            "option",
            "intraday",
            "brokerage",
        ),
    ),
    SeedTheme(
        "app_ux_support",
        "App UX & support",
        (
            "crash",
            "bug",
            "slow",
            "lag",
            "freeze",
            "update",
            "login",
            "otp",
            "ui",
            "interface",
            "chart",
            "support",
            "customer",
            "help",
        ),
    ),
    SeedTheme(
        "payments_withdrawals",
        "Payments & withdrawals",
        (
            "payment",
            "upi",
            "withdraw",
            "redeem",
            "credit",
            "debit",
            "autopay",
            "charges",
            "bank",
        ),
    ),
    SeedTheme(
        "mutual_funds_sip",
        "Mutual funds & SIP",
        ("mutual", "sip", "fund", "nav", "elss", "portfolio"),
    ),
    SeedTheme(
        "onboarding_kyc",
        "Onboarding & KYC",
        (
            "kyc",
            "verification",
            "onboard",
            "pan",
            "aadhaar",
            "document",
            "signup",
            "register",
            "ddpi",
        ),
    ),
)

GENERAL_THEME_KEY = "general_experience"
GENERAL_THEME_NAME = "General experience"


def match_theme_key(review: NormalizedReview) -> str:
    """Assign a review to the first matching seed bucket, else general."""
    haystack = f"{review.title} {review.text}".lower()
    for theme in SEED_THEMES:
        if any(keyword in haystack for keyword in theme.keywords):
            return theme.key
    return GENERAL_THEME_KEY


def theme_name_for_key(key: str) -> str:
    for theme in SEED_THEMES:
        if theme.key == key:
            return theme.name
    if key == GENERAL_THEME_KEY:
        return GENERAL_THEME_NAME
    return key.replace("_", " ").title()
