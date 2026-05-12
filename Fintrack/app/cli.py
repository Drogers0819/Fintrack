"""
Flask CLI commands.

One-off operational commands that don't belong in routes (not user-
facing) or services (single-purpose, manual control). Register via
register_cli_commands(app) from create_app.

Commands defined here:
  • backfill-net-worth — populate starting_net_worth for users who
    finished onboarding before the Net Worth feature shipped. Always
    requires an explicit --dry-run or --confirm flag so an empty
    invocation never writes.
"""

from __future__ import annotations

import click
from flask import current_app


def register_cli_commands(app):
    """Register all CLI commands with the given Flask app."""
    app.cli.add_command(backfill_net_worth)
    app.cli.add_command(wipe_users_by_email)
    app.cli.add_command(backfill_recurring_contributions)


@click.command("backfill-net-worth")
@click.option(
    "--dry-run",
    "dry_run",
    is_flag=True,
    default=False,
    help="List affected users and computed values. Does not write.",
)
@click.option(
    "--confirm",
    "confirm",
    is_flag=True,
    default=False,
    help="Actually write starting_net_worth for affected users.",
)
def backfill_net_worth(dry_run: bool, confirm: bool):
    """Backfill starting_net_worth for users who completed onboarding
    before commit baf67a1.

    Uses each user's CURRENT net worth as their backfill baseline.
    Progress for these users is measured from the backfill moment,
    NOT from their true onboarding moment. Acceptable for the small
    pre-launch test cohort. Should not happen at scale post-launch.

    Idempotent: re-running the command is a no-op for users whose
    starting_net_worth has already been set.
    """
    if not dry_run and not confirm:
        click.echo(
            "Pass --dry-run to preview affected users or --confirm to write. "
            "Refusing to run without either flag.",
            err=True,
        )
        raise click.Abort()

    if dry_run and confirm:
        click.echo("Pass only one of --dry-run or --confirm.", err=True)
        raise click.Abort()

    from app import db
    from app.models.user import User
    from app.services.net_worth_service import compute_current_net_worth

    affected = (
        User.query
        .filter(User.plan_wizard_complete.is_(True))
        .filter(User.starting_net_worth.is_(None))
        .order_by(User.id)
        .all()
    )

    if not affected:
        click.echo("No users to backfill. Already in sync.")
        return

    mode_label = "DRY RUN" if dry_run else "WRITE"
    click.echo(f"[{mode_label}] Backfilling {len(affected)} user(s).")
    click.echo(
        "Note: these users will see progress measured from the backfill "
        "point, not their true onboarding moment."
    )
    click.echo("-" * 60)

    written = 0
    for user in affected:
        snapshot = compute_current_net_worth(user)
        action = "would write" if dry_run else "writing"
        click.echo(
            f"user_id={user.id} starting_net_worth={snapshot} ({action})"
        )
        if confirm:
            user.starting_net_worth = snapshot
            written += 1

    if confirm:
        db.session.commit()

    click.echo("-" * 60)
    if dry_run:
        click.echo(f"DRY RUN complete. {len(affected)} user(s) would be backfilled.")
    else:
        click.echo(f"Backfill complete. {written} user(s) updated.")


# ─── wipe-users-by-email ─────────────────────────────────────


@click.command("wipe-users-by-email")
@click.option(
    "--email",
    "emails",
    multiple=True,
    help="Email address to delete. Repeat the flag for multiple users.",
)
@click.option(
    "--confirm",
    is_flag=True,
    default=False,
    help="Required to actually perform the deletion. Without this flag "
         "the command prints a dry-run plan and exits.",
)
def wipe_users_by_email(emails: tuple[str, ...], confirm: bool):
    """Hard-delete specific user accounts (and all related data) by email.

    Pre-launch test-account cleanup. Reuses the existing
    delete_user_account service which handles Stripe cancellation,
    PostHog event firing, and DB cascade cleanup per user.

    Per-user commits: a failure on user N rolls back only that user
    and continues with the rest. Re-running is idempotent — already-
    deleted emails are skipped with a log line.

    USAGE
        flask --app run wipe-users-by-email \\
            --email a@test.com --email b@test.com           (dry run)
        flask --app run wipe-users-by-email \\
            --email a@test.com --email b@test.com --confirm (executes)
    """
    from app.models.budget import Budget
    from app.models.chat import ChatMessage
    from app.models.checkin import CheckIn
    from app.models.crisis_event import CrisisEvent
    from app.models.goal import Goal
    from app.models.life_checkin import LifeCheckIn
    from app.models.subscription_event import SubscriptionEvent
    from app.models.transaction import Transaction
    from app.models.user import User
    from app.services.account_service import delete_user_account

    if not emails:
        click.echo(
            "No emails provided. Pass --email one or more times to identify "
            "users to delete.",
            err=True,
        )
        raise click.Abort()

    # Normalise: trim whitespace, dedupe while preserving order.
    seen: set[str] = set()
    cleaned: list[str] = []
    for raw in emails:
        e = (raw or "").strip()
        if not e:
            continue
        if e.lower() in seen:
            continue
        seen.add(e.lower())
        cleaned.append(e)

    if not cleaned:
        click.echo("All provided emails were blank after trimming. Aborting.", err=True)
        raise click.Abort()

    # Per-email lookup with detail counts.
    plan: list[dict] = []
    missing: list[str] = []
    for email in cleaned:
        user = User.query.filter(User.email == email).first()
        if user is None:
            missing.append(email)
            continue
        plan.append({
            "user_id": user.id,
            "email": user.email,
            "goals": Goal.query.filter_by(user_id=user.id).count(),
            "checkins": CheckIn.query.filter_by(user_id=user.id).count(),
            "transactions": Transaction.query.filter_by(user_id=user.id).count(),
            "budgets": Budget.query.filter_by(user_id=user.id).count(),
            "life_checkins": LifeCheckIn.query.filter_by(user_id=user.id).count(),
            "chat_messages": ChatMessage.query.filter_by(user_id=user.id).count(),
            "crisis_events": CrisisEvent.query.filter_by(user_id=user.id).count(),
            "subscription_events": SubscriptionEvent.query.filter_by(user_id=user.id).count(),
        })

    mode_label = "DRY RUN" if not confirm else "WRITE"
    click.echo(f"[{mode_label}] Wipe plan")
    click.echo("-" * 70)

    for email in missing:
        click.echo(f"user_id=? email={email} not found, skipping")

    if not plan:
        click.echo("No matching users to delete.")
        # Report the total preserved so the operator sees the baseline.
        preserved_total = User.query.count()
        click.echo("-" * 70)
        click.echo(
            f"Wipe complete. 0 user(s) deleted. "
            f"{preserved_total} user(s) preserved in database."
        )
        return

    for row in plan:
        related = (
            f"goals={row['goals']} checkins={row['checkins']} "
            f"transactions={row['transactions']} budgets={row['budgets']} "
            f"life_checkins={row['life_checkins']} chat_messages={row['chat_messages']} "
            f"crisis_events={row['crisis_events']} subscription_events={row['subscription_events']}"
        )
        action = "→ will be deleted" if not confirm else "→ deleting..."
        click.echo(
            f"user_id={row['user_id']} email={row['email']} {related} {action}"
        )

    click.echo("-" * 70)
    total_users_before = User.query.count()
    click.echo(
        f"{len(plan)} user(s) match. {total_users_before} user(s) currently in database."
    )

    if not confirm:
        click.echo(
            "DRY RUN complete. Re-run with --confirm to perform the deletion."
        )
        return

    # Execute. Per-user commits inside delete_user_account.
    deleted = 0
    failed: list[dict] = []
    for row in plan:
        ok = delete_user_account(row["user_id"], reason="cli-wipe")
        if ok:
            click.echo(f"user_id={row['user_id']} email={row['email']} → DELETED")
            deleted += 1
        else:
            click.echo(
                f"user_id={row['user_id']} email={row['email']} → FAILED",
                err=True,
            )
            failed.append(row)

    preserved_total = User.query.count()
    click.echo("-" * 70)
    click.echo(
        f"Wipe complete. {deleted} user(s) deleted. "
        f"{preserved_total} user(s) preserved in database."
    )
    if failed:
        click.echo(
            f"{len(failed)} user(s) failed to delete. Re-run the command to retry "
            f"failed users.",
            err=True,
        )


# ─── backfill-recurring-contributions ────────────────────────


@click.command("backfill-recurring-contributions")
@click.option(
    "--dry-run",
    "dry_run",
    is_flag=True,
    default=False,
    help="List affected users and the Legacy row that would be created.",
)
@click.option(
    "--confirm",
    is_flag=True,
    default=False,
    help="Write Legacy contributions rows for affected users.",
)
def backfill_recurring_contributions(dry_run: bool, confirm: bool):
    """One-shot migration for the RecurringContribution refactor.

    For each user where User.subscriptions_total > 0 OR
    User.other_commitments > 0 AND no RecurringContribution rows
    exist for that source yet, creates a single "Legacy contributions"
    row that preserves the rolled-up amount. No chip identity is
    invented — we cannot recover information that wasn't captured.

    Idempotent: users who already have RecurringContribution rows
    for a source are skipped for that source (a user might have
    rows for subscriptions but not other_commitments, and the
    migration handles that mixed case).
    """
    if not dry_run and not confirm:
        click.echo(
            "Pass --dry-run to preview or --confirm to write. "
            "Refusing to run without either flag.",
            err=True,
        )
        raise click.Abort()

    if dry_run and confirm:
        click.echo("Pass only one of --dry-run or --confirm.", err=True)
        raise click.Abort()

    from app import db
    from app.models.recurring_contribution import RecurringContribution
    from app.models.user import User
    from app.services.recurring_contribution_service import (
        recompute_cached_aggregate,
    )

    sources_to_check = (
        ("subscriptions", "subscriptions_total"),
        ("other_commitments", "other_commitments"),
    )

    mode_label = "DRY RUN" if dry_run else "WRITE"
    click.echo(f"[{mode_label}] Recurring contribution backfill")
    click.echo("-" * 70)

    plan: list[dict] = []
    users = User.query.order_by(User.id).all()
    for user in users:
        for source_key, scalar_col in sources_to_check:
            scalar = getattr(user, scalar_col, None)
            if scalar is None or float(scalar) <= 0:
                continue
            existing_count = RecurringContribution.query.filter_by(
                user_id=user.id, source=source_key,
            ).count()
            if existing_count > 0:
                continue
            plan.append({
                "user_id": user.id,
                "source": source_key,
                "amount": float(scalar),
            })

    if not plan:
        click.echo("No users to backfill. Already in sync.")
        return

    for entry in plan:
        action = "would write" if dry_run else "writing"
        click.echo(
            f"user_id={entry['user_id']} source={entry['source']} "
            f"amount=£{entry['amount']:.2f} → Legacy contributions ({action})"
        )

    click.echo("-" * 70)

    if not confirm:
        click.echo(
            f"DRY RUN complete. {len(plan)} Legacy row(s) would be created."
        )
        click.echo(
            "Note: backfilled rows have no chip identity. Their label is "
            "'Legacy contributions ({source})' and chip_id is NULL — we "
            "cannot recover information that wasn't captured pre-refactor."
        )
        return

    written = 0
    for entry in plan:
        row = RecurringContribution(
            user_id=entry["user_id"],
            source=entry["source"],
            chip_id=None,
            label=f"Legacy contributions ({entry['source'].replace('_', ' ')})",
            amount=entry["amount"],
            linked_goal_id=None,
        )
        db.session.add(row)
        written += 1
    db.session.commit()

    # Recompute the cached aggregate on each affected user. The amount
    # should be unchanged (we wrote the same scalar value into the row)
    # but recomputing keeps the invariant explicit.
    seen_users: set[int] = set()
    for entry in plan:
        if entry["user_id"] in seen_users:
            continue
        user = db.session.get(User, entry["user_id"])
        if user is not None:
            recompute_cached_aggregate(user, entry["source"])
        seen_users.add(entry["user_id"])

    click.echo(f"Backfill complete. {written} Legacy row(s) created.")
