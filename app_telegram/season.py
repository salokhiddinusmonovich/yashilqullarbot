"""Date-driven seasonal branding — mirrors src/components/effects/season.ts
in the frontend repo exactly, so the admin logo matches the website's."""
from datetime import date

SEASONS = ("spring", "summer", "autumn", "winter")


def get_season(d: date | None = None) -> str:
    d = d or date.today()
    m = d.month
    if m in (12, 1, 2):
        return "winter"
    if m in (3, 4, 5):
        return "spring"
    if m in (6, 7, 8):
        return "summer"
    return "autumn"
