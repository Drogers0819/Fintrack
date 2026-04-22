from datetime import datetime
from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user


PAID_TIERS = {"pro", "pro_plus", "joint"}


def is_subscription_active(user):
    if user is None or not getattr(user, "is_authenticated", False):
        return False

    if (user.subscription_tier or "free") in PAID_TIERS:
        return True

    if user.trial_ends_at and user.trial_ends_at > datetime.utcnow():
        return True

    return False


def requires_subscription(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not is_subscription_active(current_user):
            flash("Start your trial to access this feature", "info")
            return redirect(url_for("pages.trial_gate"))
        return view(*args, **kwargs)

    return wrapper
