"""
Команды рассылки для админов. Все — ответом (reply) на сообщение,
которое нужно разослать. Пересылается как есть (copy_to), поэтому
текст рассылки админ пишет сам, на нужном языке.

/send                  — всем
/adminsend             — только админам
/targetsend @a @b      — конкретным людям (username или ФИО)
/regionsend samarkand  — одному региону
/remindregion          — напоминание тем, у кого не выбран регион (на языке каждого)
/check @nick           — подписан ли человек на канал
"""
import asyncio
import logging
from html import escape

from aiogram import types, Dispatcher
from aiogram.utils import exceptions
from aiogram.utils.exceptions import ChatNotFound
from asgiref.sync import sync_to_async
from django.db.models import Q

from app_telegram.models import TGUser
from tgbot.i18n import t, REGIONS
from tgbot.services import stats
from tgbot.services.lang import langs_of

logger = logging.getLogger(__name__)

CHANNEL_ID = -1002652020165


async def _is_admin(message: types.Message) -> bool:
    if message.from_user.id in message.bot["config"].tg_bot.admin_ids:
        return True
    return await sync_to_async(TGUser.objects.filter(tg_id=message.from_user.id, is_admin=True).exists)()


async def _broadcast(tg_ids, send):
    """
    Общий цикл рассылки с защитой от флуда. send(tg_id) — корутина отправки.
    Возвращает (доставлено, заблокировали, ошибок).
    """
    sent = blocked = errors = 0
    for tg_id in tg_ids:
        for _ in range(2):
            try:
                await send(tg_id)
                sent += 1
            except exceptions.BotBlocked:
                blocked += 1
                await stats.mark_blocked(tg_id)
            except exceptions.RetryAfter as e:
                await asyncio.sleep(e.timeout)
                continue  # одна повторная попытка после паузы от Telegram
            except Exception as e:
                logger.error("Ошибка отправки на %s: %s", tg_id, e)
                errors += 1
            break
        await asyncio.sleep(0.05)  # ~20 сообщений/сек — ниже лимита Telegram
    return sent, blocked, errors


async def _copy_to_all(message: types.Message, cmd: str, tg_ids):
    if not message.reply_to_message:
        await message.answer(t("bc_reply_needed", cmd=cmd))
        return
    tg_ids = [i for i in tg_ids if i]
    if not tg_ids:
        await message.answer(t("bc_empty"))
        return
    await message.answer(t("bc_started", n=len(tg_ids)))
    sent, blocked, errors = await _broadcast(
        tg_ids, lambda tg_id: message.reply_to_message.copy_to(chat_id=tg_id)
    )
    await message.answer(t("bc_done", sent=sent, blocked=blocked, errors=errors))


def _ids(qs):
    return sync_to_async(list)(qs.filter(tg_id__isnull=False).values_list("tg_id", flat=True))


async def run_broadcast(message: types.Message):
    if not await _is_admin(message):
        return
    await _copy_to_all(message, "/send", await _ids(TGUser.objects.all()))


async def send_to_admins(message: types.Message):
    if not await _is_admin(message):
        return
    await _copy_to_all(message, "/adminsend", await _ids(TGUser.objects.filter(is_admin=True)))


async def target_broadcast(message: types.Message):
    if not await _is_admin(message):
        return
    targets = [a.lstrip('@') for a in message.get_args().split()]
    if message.reply_to_message and not targets:
        await message.answer(t("bc_args_needed", example="/targetsend @nick1 @nick2"))
        return
    ids = await _ids(TGUser.objects.filter(Q(username__in=targets) | Q(fullname__in=targets))) if targets else []
    await _copy_to_all(message, "/targetsend @nick", ids)


async def region_broadcast(message: types.Message):
    if not await _is_admin(message):
        return
    region = message.get_args().strip().lower()
    if message.reply_to_message and not region:
        await message.answer(t("bc_args_needed", example="/regionsend tashkent_s"))
        return
    if region and region not in REGIONS:
        await message.answer(t("bc_bad_region", regions=", ".join(REGIONS)))
        return
    ids = await _ids(TGUser.objects.filter(region=region)) if region else []
    await _copy_to_all(message, "/regionsend samarkand", ids)


async def check_user_subscription(message: types.Message):
    if not await _is_admin(message):
        return
    query = message.get_args().strip()
    if not query:
        await message.answer(t("bc_args_needed", example="/check @nickname"))
        return

    name = query.lstrip('@')
    q = Q(tg_id=int(name)) if name.isdigit() else Q(username__iexact=name) | Q(fullname__icontains=name)
    user = await sync_to_async(TGUser.objects.filter(q).exclude(tg_id__isnull=True).first)()
    if not user:
        await message.answer(t("chk_not_found", q=escape(query)))
        return

    try:
        member = await message.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user.tg_id)
        res = {
            'creator': t("chk_admin"), 'administrator': t("chk_admin"), 'member': t("chk_member"),
            'left': t("chk_left"), 'kicked': t("chk_kicked"),
        }.get(member.status, member.status)
        await message.answer(t("chk_result", name=escape(user.fullname or "—"), id=user.tg_id, res=res))
    except ChatNotFound:
        await message.answer(t("chk_error", e="channel not found"))
    except Exception as e:
        await message.answer(t("chk_error", e=escape(str(e))))


async def remind_no_region(message: types.Message):
    """Напоминание всем, у кого регион пустой или не из списка (на языке каждого)."""
    if not await _is_admin(message):
        return

    users = await sync_to_async(list)(
        TGUser.objects.filter(tg_id__isnull=False).exclude(region__in=list(REGIONS))
        .only("tg_id", "fullname", "username", "region")
    )
    if not users:
        await message.answer(t("bc_region_ok"))
        return

    lines = [t("bc_region_list", n=len(users)), ""]
    for i, u in enumerate(users, 1):
        uname = f" (@{escape(u.username)})" if u.username else ""
        lines.append(f"{i}. {escape(u.fullname or '—')}{uname} · <b>{escape(u.region or '—')}</b>")
    report = "\n".join(lines)
    for x in range(0, len(report), 4000):
        await message.answer(report[x:x + 4000])

    langs = await langs_of([u.tg_id for u in users])
    await message.answer(t("bc_started", n=len(users)))
    sent, blocked, errors = await _broadcast(
        [u.tg_id for u in users],
        lambda tg_id: message.bot.send_message(tg_id, t("remind_region", langs.get(tg_id))),
    )
    await message.answer(t("bc_done", sent=sent, blocked=blocked, errors=errors))


def register_admin(dp: Dispatcher):
    dp.register_message_handler(run_broadcast, commands=['send'], state="*")
    dp.register_message_handler(send_to_admins, commands=['adminsend'], state="*")
    dp.register_message_handler(target_broadcast, commands=['targetsend'], state="*")
    dp.register_message_handler(region_broadcast, commands=['regionsend'], state="*")
    dp.register_message_handler(check_user_subscription, commands=['check'], state="*")
    dp.register_message_handler(remind_no_region, commands=['remindregion'], state="*")
