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
