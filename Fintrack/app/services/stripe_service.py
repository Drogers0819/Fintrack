import os

import stripe


STRIPE_PRICES = {
    "plan_monthly": "price_1TPRnLQvB4INLZ9mMJhjrL0m",
    "coach_monthly": "price_1TPRogQvB4INLZ9m3J0qg73Y",
    "duo_monthly": "price_1TPRpTQvB4INLZ9m9dA7PjSE",
}

PRICE_TO_TIER = {
    "price_1TPRnLQvB4INLZ9mMJhjrL0m": "pro",
    "price_1TPRogQvB4INLZ9m3J0qg73Y": "pro_plus",
    "price_1TPRpTQvB4INLZ9m9dA7PjSE": "joint",
}

PLAN_SLUG_TO_PRICE_KEY = {
    "plan": "plan_monthly",
    "coach": "coach_monthly",
    "duo": "duo_monthly",
}

TIER_LABELS = {
    "free": "Claro Free",
    "pro": "Claro Plan",
    "pro_plus": "Claro Coach",
    "joint": "Claro Duo",
}

TIER_PRICING = {
    "pro": "£9.99/mo",
    "pro_plus": "£16.99/mo",
    "joint": "£24.99/mo",
}

PUBLIC_PLAN_SUMMARY = [
    {
        "slug": "plan",
        "tier": "pro",
        "name": "Claro Plan",
        "price": "£9.99/mo",
        "tagline": "Your core financial plan, kept on track.",
        "features": [
            "Full financial plan with monthly tracking",
            "What-if scenarios",
            "Monthly check-ins",
        ],
    },
    {
        "slug": "coach",
        "tier": "pro_plus",
        "name": "Claro Coach",
        "price": "£16.99/mo",
        "tagline": "Plan + AI companion that actually knows you.",
        "features": [
            "Everything in Claro Plan",
            "AI companion: ask anything about your money",
            "Priority insights and nudges",
        ],
    },
    {
        "slug": "duo",
        "tier": "joint",
        "name": "Claro Duo",
        "price": "£24.99/mo",
        "tagline": "Coach for two — align your money together.",
        "features": [
            "Everything in Claro Coach",
            "Two linked accounts, one plan",
            "Shared goals and joint tracking",
        ],
    },
]


def init_stripe():
    """Configure the stripe SDK with the secret key from the environment.

    Safe to call repeatedly. Returns True if a key was configured.
    """
    key = os.environ.get("STRIPE_SECRET_KEY")
    if key:
        stripe.api_key = key
        return True
    return False


def publishable_key():
    return os.environ.get("STRIPE_PUBLISHABLE_KEY", "")


def webhook_secret():
    return os.environ.get("STRIPE_WEBHOOK_SECRET", "")


def price_id_for_plan(plan_slug):
    key = PLAN_SLUG_TO_PRICE_KEY.get(plan_slug)
    if not key:
        return None
    return STRIPE_PRICES.get(key)


def tier_for_price_id(price_id):
    return PRICE_TO_TIER.get(price_id, "free")
