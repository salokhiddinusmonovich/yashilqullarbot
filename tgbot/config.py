from dataclasses import dataclass

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
    # МЫ ВООБЩЕ УБРАЛИ ENVIRONS И ПИШЕМ ДАННЫЕ ПРЯМО ТУТ
    return Config(
        tg_bot=TgBot(
            token="8597081931:AAHrLlthINCN8nIZp_zh3WEbzfc-5GhoHmw",
            admin_ids=[111],
        ),
        redis=Redis(
            host="redis",  # Название сервиса из docker-compose
            port="6379",
            password=None,
            use_redis=True
        ),
        misc=Miscellaneous()
    )