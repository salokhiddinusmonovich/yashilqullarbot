import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Redis:
    use_redis: bool
    host: str
    port: str
    password: str | None

@dataclass
class TgBot:
    token: str
    admin_ids: list[int]

@dataclass
class Miscellaneous:
    other_params: str = None

@dataclass
class Config:
    tg_bot: TgBot
    redis: Redis
    misc: Miscellaneous

def load_config(path: str = None):
    admin_ids_raw = os.environ.get("ADMIN_IDS", "111")
    admin_ids = [int(x.strip()) for x in admin_ids_raw.split(",") if x.strip()]

    return Config(
        tg_bot=TgBot(
            token=os.environ.get("BOT_TOKEN"),
            admin_ids=admin_ids,
        ),
        redis=Redis(
            host=os.environ.get("REDIS_HOST", "redis"),
            port=os.environ.get("REDIS_PORT", "6379"),
            password=os.environ.get("REDIS_PASSWORD") or None,
            use_redis=True,
        ),
        misc=Miscellaneous()
    )