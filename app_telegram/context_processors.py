"""Template context processors for this project."""
from django.templatetags.static import static

from .season import get_season


def season_branding(request):
    """Exposes yq_season_logo (current season's logo SVG URL) to every
    template, so the admin header can swap it automatically like the
    website does."""
    return {"yq_season_logo": static(f"brand/season-{get_season()}.svg")}
