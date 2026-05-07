"""
Signposting library — Block 2 Task 2.7.

Single source of truth for the free, regulated UK resources Claro
points users to. Templates and services pull from here rather than
hardcoding strings, so descriptions / URLs / phone numbers can change
in one place.

Discipline
----------
Every entry is:
  • free at point of use,
  • regulated where applicable (FCA-regulated debt advice, charity
    regulators for non-financial support), and
  • appropriate for a specific situation, not a paid affiliate or a
    well-known-but-irrelevant link.

We do not list paid products. We do not list Claro-affiliate links.
We do not list commercial referrals. The library is safety
infrastructure: real users in distress hit dead ends if this data is
wrong, so changes go through the same review path as code.

Data shape
----------
At <20 entries this is a Python module rather than a DB table:
  • version-controlled in code (audit trail = git log),
  • imports validate at startup (malformed entry = boot fail, loud),
  • zero infra cost,
  • cheap to query (in-memory, no DB round-trip).

Categories
----------
Categories are the tags that drive contextual suggestions. Adding a
new category is a code change. Resources can carry multiple tags.
"""

from __future__ import annotations

from typing import Iterable

# Valid category tags. Any resource referencing a tag not in this set
# fails the import-time validation below — no silent typos.
CATEGORIES: tuple[str, ...] = (
    "debt",
    "general_money",
    "benefits",
    "housing",
    "mental_health",
    "gambling",
    # Placeholder — no resources tagged yet. Reserved so future
    # additions don't change the taxonomy under us.
    "relationships",
)


SIGNPOSTING_RESOURCES: tuple[dict, ...] = (
    {
        "id": "stepchange",
        "name": "StepChange",
        "url": "https://www.stepchange.org",
        "description": "Free debt advice and debt management plans",
        "categories": ("debt", "general_money"),
        "phone": None,
        "email": None,
        "regulated_by": "FCA",
        "free": True,
    },
    {
        "id": "moneyhelper",
        "name": "MoneyHelper",
        "url": "https://www.moneyhelper.org.uk",
        "description": "Free, government-backed money guidance",
        "categories": ("general_money", "benefits"),
        "phone": None,
        "email": None,
        "regulated_by": "Government",
        "free": True,
    },
    {
        "id": "citizens_advice",
        "name": "Citizens Advice",
        "url": "https://www.citizensadvice.org.uk",
        "description": "Free advice on benefits, work, housing, and consumer rights",
        "categories": ("benefits", "housing", "general_money"),
        "phone": None,
        "email": None,
        "regulated_by": "Charity",
        "free": True,
    },
    {
        "id": "national_debtline",
        "name": "National Debtline",
        "url": "https://www.nationaldebtline.org",
        "description": "Free debt advice from a regulated charity",
        "categories": ("debt",),
        "phone": "0808 808 4000",
        "email": None,
        "regulated_by": "FCA",
        "free": True,
    },
    {
        "id": "samaritans",
        "name": "Samaritans",
        "url": "https://www.samaritans.org",
        "description": "Free emotional support, 24/7",
        "categories": ("mental_health",),
        "phone": "116 123",
        "email": "jo@samaritans.org",
        "regulated_by": "Charity",
        "free": True,
    },
    {
        "id": "mind",
        "name": "Mind",
        "url": "https://www.mind.org.uk",
        "description": "Mental health information and support",
        "categories": ("mental_health",),
        "phone": "0300 123 3393",
        "email": None,
        "regulated_by": "Charity",
        "free": True,
    },
    {
        "id": "gamcare",
        "name": "GamCare",
        "url": "https://www.gamcare.org.uk",
        "description": "Free help and support for problem gambling",
        "categories": ("gambling", "mental_health"),
        "phone": "0808 8020 133",
        "email": None,
        "regulated_by": "Charity",
        "free": True,
    },
    {
        "id": "shelter",
        "name": "Shelter",
        "url": "https://www.shelter.org.uk",
        "description": "Housing advice for renters and homeowners",
        "categories": ("housing",),
        "phone": "0808 800 4444",
        "email": None,
        "regulated_by": "Charity",
        "free": True,
    },
)


# ─── Validation ──────────────────────────────────────────────


_REQUIRED_FIELDS = (
    "id", "name", "url", "description", "categories", "free",
)


def _validate_library() -> None:
    """Run at import time. Any malformed entry raises and prevents the
    Flask app from booting — better a loud failure than a quiet bad
    library in production."""
    seen_ids: set[str] = set()
    for resource in SIGNPOSTING_RESOURCES:
        for field in _REQUIRED_FIELDS:
            if field not in resource:
                raise ValueError(
                    f"Signposting resource missing required field "
                    f"'{field}': {resource.get('id') or resource}"
                )

        rid = resource["id"]
        if rid in seen_ids:
            raise ValueError(f"Duplicate signposting resource id: {rid!r}")
        seen_ids.add(rid)

        url = resource["url"]
        if not isinstance(url, str) or not url.startswith("https://"):
            raise ValueError(
                f"Signposting resource {rid!r} has non-https URL: {url!r}"
            )

        cats = resource["categories"]
        if not cats:
            raise ValueError(
                f"Signposting resource {rid!r} must list at least one category"
            )
        for cat in cats:
            if cat not in CATEGORIES:
                raise ValueError(
                    f"Signposting resource {rid!r} references unknown "
                    f"category {cat!r} (valid: {CATEGORIES})"
                )

        if resource.get("free") is not True:
            raise ValueError(
                f"Signposting resource {rid!r} must be free at point of use"
            )


_validate_library()


# ─── Lookups ─────────────────────────────────────────────────


def get_resource(resource_id: str) -> dict | None:
    """Return the resource dict by id, or None when unknown."""
    for resource in SIGNPOSTING_RESOURCES:
        if resource["id"] == resource_id:
            return resource
    return None


def get_resources_for_category(category: str) -> list[dict]:
    """Return every resource tagged with the given category, in
    library order. Unknown category returns []."""
    if category not in CATEGORIES:
        return []
    return [r for r in SIGNPOSTING_RESOURCES if category in r["categories"]]


def get_resources_for_categories(categories: Iterable[str]) -> list[dict]:
    """Return resources matching any of the provided categories,
    deduplicated, in library order."""
    wanted = set(c for c in categories if c in CATEGORIES)
    if not wanted:
        return []
    return [
        r for r in SIGNPOSTING_RESOURCES
        if any(c in wanted for c in r["categories"])
    ]


def get_all_resources() -> list[dict]:
    """Return the full list. Used by the admin audit page and the
    companion's dynamic resource-name list."""
    return list(SIGNPOSTING_RESOURCES)
