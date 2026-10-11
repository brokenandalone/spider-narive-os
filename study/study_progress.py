"""Manual academic progress statistics. Never label these official SNHU grades."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def valid_score(earned, possible):
    try:
        earned, possible = Decimal(str(earned)), Decimal(str(possible))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError("Enter valid numeric points earned and possible.") from error
    if (not earned.is_finite() or not possible.is_finite() or
            earned < 0 or possible <= 0 or
            earned > 100000 or possible > 100000):
        raise ValueError("Points must be finite, earned at least zero, and possible above zero.")
    # Extra-credit scores over 100% are allowed and clearly shown as entered.
    if earned > possible * 3:
        raise ValueError("Earned points exceed 300% of possible. Check the entry.")
    earned = earned.quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
    possible = possible.quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
    if possible <= 0:
        raise ValueError("Possible points must be at least 0.01.")
    return earned, possible


def grade_summary(rows):
    """Unweighted, manually entered point totals, NOT term GPA or official grades."""
    earned_total = Decimal("0")
    possible_total = Decimal("0")
    scored = 0
    for row in rows:
        if row["earned"] is None or row["possible"] is None:
            continue
        earned, possible = valid_score(row["earned"], row["possible"])
        scored += 1
        earned_total += earned
        possible_total += possible
    percent = ((earned_total * 100 / possible_total)
               .quantize(Decimal(".1"), rounding=ROUND_HALF_UP)
               if possible_total else None)
    return {
        "graded": scored,
        "earned": str(earned_total.quantize(Decimal(".01"))),
        "possible": str(possible_total.quantize(Decimal(".01"))),
        "percentage": str(percent) if percent is not None else None,
    }


def valid_study_session(topic, minutes):
    topic = str(topic).strip()
    if not topic or len(topic) > 240 or "\x00" in topic:
        raise ValueError("Enter a study topic of up to 240 characters.")
    if type(minutes) is not int or not 1 <= minutes <= 600:
        raise ValueError("A study session must be 1 to 600 whole minutes.")
    return topic, minutes


def session_summary(rows):
    minutes = sum(int(row["minutes"]) for row in rows)
    return {"sessions": len(rows), "minutes": minutes,
            "hours": round(minutes / 60, 1)}
