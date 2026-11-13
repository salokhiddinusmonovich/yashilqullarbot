"""⛔ Записался и не пришёл → следующие 2 мероприятия своего региона записаться нельзя, с 3-го — можно."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["DJANGO_SETTINGS_MODULE"] = "test_settings"; os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
import django; django.setup()
from django.core.management import call_command
call_command("migrate", run_syncdb=True, verbosity=0)
import fakeredis, tgbot.services.lang as L
L._sync = fakeredis.FakeRedis(decode_responses=True)
import app_telegram.telegram as TT; TT.send_in_background = lambda m, on_done=None: None
import app_telegram.referrals as R; R.on_attended = lambda u: None
from datetime import timedelta
from django.utils import timezone
from app_telegram.models import TGUser, EcoProject, ProjectParticipation as PP
from app_telegram import services as S, waitlist as W
ok = 0
def check(c, m):
    global ok; assert c, m; ok += 1; print("  ✓", m)

now = timezone.now()
def ev(days, region="tashkent_s", active=True, title=None, maxp=50):
    return EcoProject.objects.create(title=title or f"ev{days}", date=now + timedelta(days=days), region=region, is_active=active, max_participants=maxp)
aziza = TGUser.objects.create(tg_id=1, fullname="Aziza", region="tashkent_s")
other = TGUser.objects.create(tg_id=2, fullname="Bek", region="tashkent_s")

missed = ev(-3, title="Plogging")
PP.objects.create(user=aziza, project=missed, status='approved')            # записалась — не пришла
PP.objects.create(user=other, project=missed, status='attended')            # отмечали людей → это неявка
ev(1, region="samarkand")                                                     # другой регион — не считается
ev(1.5, active=False)                                                         # отменённое — не считается
e1, e2, e3 = ev(2), ev(4), ev(6)
check(S.join_event(aziza, e1.id)[0] == "noshow", "1-е мероприятие после неявки — нельзя")
check(S.join_event(aziza, e2.id)[0] == "noshow", "2-е — нельзя")
check(S.join_event(aziza, e3.id)[0] == "ok", "3-е — снова можно")
check(S.noshow_block(aziza, e1) == missed, "причина — «Plogging»")
check(S.join_event(other, e1.id)[0] == "ok", "пришедший записывается спокойно")
check(S.join_event(TGUser.objects.create(tg_id=3, fullname="New", region="tashkent_s"), e1.id)[0] == "ok", "новичок — без ограничений")

# отметили задним числом → блок снимается сам
pp = PP.objects.get(user=aziza, project=missed); pp.status = 'attended'; pp.save()
check(S.join_event(aziza, e1.id)[0] == "ok", "координатор отметил задним числом — блок снят")

# мероприятие, где вообще никого не отмечали, — не неявка (сканирования не было)
u = TGUser.objects.create(tg_id=4, fullname="Dilnoza", region="tashkent_s")
noscan = ev(-2); PP.objects.create(user=u, project=noscan, status='approved')
check(S.join_event(u, e2.id)[0] == "ok", "на мероприятии никого не отмечали — не наказываем")

# сутки на поздние отметки
v = TGUser.objects.create(tg_id=5, fullname="Jasur", region="tashkent_s")
fresh = EcoProject.objects.create(title="today", date=now - timedelta(hours=5), region="tashkent_s", max_participants=50)
PP.objects.create(user=v, project=fresh, status='approved'); PP.objects.create(user=other, project=fresh, status='attended')
check(S.join_event(v, e2.id)[0] == "ok", "прошло меньше суток — ещё не неявка")

# наказание «отбыто»: после неявки уже прошли 2 мероприятия
w = TGUser.objects.create(tg_id=6, fullname="Madina", region="samarkand")
old = ev(-20, region="samarkand"); PP.objects.create(user=w, project=old, status='approved')
PP.objects.create(user=TGUser.objects.create(tg_id=7, fullname="x", region="samarkand"), project=old, status='attended')
ev(-10, region="samarkand"); ev(-5, region="samarkand")
check(S.join_event(w, ev(3, region="samarkand").id)[0] == "ok", "2 мероприятия после неявки уже прошли — снова можно")

# Ташкент-город и область — одно целое
t2 = TGUser.objects.create(tg_id=8, fullname="Sardor", region="tashkent_v")
m2 = ev(-1.5); PP.objects.create(user=t2, project=m2, status='approved'); PP.objects.create(user=other, project=m2, status='attended')
check(S.join_event(t2, e1.id)[0] == "noshow", "Ташкентская область: мероприятия Ташкента считаются «своими»")

# очередь: заблокированного не записывает автоматически
z = TGUser.objects.create(tg_id=9, fullname="Zarina", region="tashkent_s")
mz = ev(-1.2); PP.objects.create(user=z, project=mz, status='approved'); PP.objects.create(user=other, project=mz, status='attended')
small = ev(1.2, maxp=1); PP.objects.create(user=other, project=small, status='approved')
q = TGUser.objects.create(tg_id=10, fullname="Otabek", region="tashkent_s")
W.join(z, small); W.join(q, small)
PP.objects.filter(user=other, project=small).delete()                        # место освободилось → promote
check(not PP.objects.filter(user=z, project=small).exists(), "из очереди заблокированного не записываем")
check(PP.objects.filter(user=q, project=small).exists(), "место получил следующий в очереди")
print(f"OK: {ok} проверок")
