"""
Точка на карте → страна, регион, короткий адрес (OpenStreetMap Nominatim, бесплатно, без ключа).
Правила Nominatim: не чаще 1 запроса в секунду и свой User-Agent — у нас это единичные запросы.
Не ответил — регион берём ближайший по центрам (app_telegram/spots.CENTERS), и человек его подтверждает.
"""
import logging
import os

import aiohttp

log = logging.getLogger(__name__)
URL = os.environ.get("GEOCODER_URL", "https://nominatim.openstreetmap.org/reverse")
UA = "YashilQollarBot/1.0 (https://yashilqollar.uz)"


async def reverse(lat: float, lon: float, lang: str = "uz") -> dict | None:
    """{country: 'uz', region: 'jizzakh' | None, address: 'Sharof Rashidov ko'chasi, Jizzax'} или None."""
    from app_telegram.spots import ISO_REGION
    params = {"lat": f"{lat:.6f}", "lon": f"{lon:.6f}", "format": "jsonv2", "zoom": 16, "addressdetails": 1,
              "accept-language": {"uz": "uz,ru", "ru": "ru", "en": "en"}.get(lang, "uz,ru")}
    try:
        async with aiohttp.ClientSession(headers={"User-Agent": UA}) as s:
            async with s.get(URL, params=params, timeout=aiohttp.ClientTimeout(total=6)) as r:
                if r.status != 200:
                    return None
                data = await r.json()
    except Exception as e:
        log.warning("reverse geocode failed: %s", e)
        return None
    a = data.get("address") or {}
    if not a:
        return None
    iso = a.get("ISO3166-2-lvl4") or ""
    parts = [a.get(k) for k in ("road", "neighbourhood", "suburb", "village", "town", "district", "city", "county") if a.get(k)]
    seen, short = set(), []
    for p in parts:
        if p not in seen:
            seen.add(p)
            short.append(p)
    return {"country": (a.get("country_code") or "").lower(), "region": ISO_REGION.get(iso),
            "address": ", ".join(short[:3]) or (data.get("display_name") or "")[:200]}
