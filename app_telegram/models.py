from django.contrib.auth.models import User
from django.db import models
import uuid
from django.db import models


class TimeBasedModel(models.Model):
    class Meta:
        abstract = True
        ordering = ('-created',)

    created = models.DateTimeField(auto_now_add=True, verbose_name='дата создания')
    updated = models.DateTimeField(auto_now=True, verbose_name='дата обновления')


class TGUser(TimeBasedModel):
    class Region(models.TextChoices):
        KARAKALPAKSTAN = 'karakalpakstan', 'Qoraqalpogʻiston Respublikasi'
        ANDIJON = 'andijon', 'Andijon viloyati'
        BUKHARA = 'bukhara', 'Buxoro viloyati'
        FARGONA = 'fargona', 'Fargʻona viloyati'
        JIZZAKH = 'jizzakh', 'Jizzax viloyati'
        KHOREZM = 'khorezm', 'Xorazm viloyati'
        NAMANGAN = 'namangan', 'Namangan viloyati'
        NAVOI = 'navoi', 'Navoiy viloyati'
        QASHQADARYO = 'qashqadaryo', 'Qashqadaryo viloyati'
        SAMARKAND = 'samarkand', 'Samarqand viloyati'
        SIRDARYO = 'sirdaryo', 'Sirdaryo viloyati'
        SURKHANDARYO = 'surkhandaryo', 'Surxondaryo viloyati'
        TASHKENT_V = 'tashkent_v', 'Toshkent viloyati'
        TASHKENT_S = 'tashkent_s', 'Toshkent shahri'

    tg_id = models.BigIntegerField(unique=True, db_index=True, verbose_name='id Telegram')
    fullname = models.CharField(max_length=255)
    age = models.PositiveSmallIntegerField(blank=True, null=True)
    email = models.EmailField(max_length=255)
    phone = models.CharField(max_length=20)
    username = models.CharField(max_length=255, blank=True, null=True, verbose_name='Username')
    experience = models.TextField(
    blank=True, 
    null=True, 
    verbose_name='tajribasi'
    )

    photo = models.ImageField(
    upload_to='users_photos/', 
    blank=True, 
    null=True, 
    verbose_name='Profil rasmi'
    )

    region = models.CharField(
        max_length=20,
        choices=Region.choices,
        blank=True,
        null=True,
        verbose_name='Hudud'
    )

    education_place = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='O‘qish joyi'
    )

    balance = models.PositiveIntegerField(default=0, verbose_name="Эко-баллы") # Наши монетки
    
    # Можно добавить метод для определения статуса прямо в модель
    @property
    def rank(self):
        if self.balance < 50:
            return "🌱 Nihol (Росток)"
        elif self.balance < 150:
            return "🌳 Daraxt (Дерево)"
        else:
            return "🛡 Tabiat Himoyachisi (Защитник)"

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'пользователи'

    def __str__(self):
        return f'{self.fullname} ({self.tg_id})'


class TeamMemberYashilQullar(TimeBasedModel):
    tg_user = models.OneToOneField(
        TGUser,
        on_delete=models.CASCADE,
        related_name='team_member',
        verbose_name='Telegram foydalanuvchi'
    )

    # Faqat jamoaga xos qo'shimcha ma'lumotlar qoladi
    skills = models.TextField(
        blank=True, 
        null=True, 
        verbose_name='Ko‘nikmalar'
    )
    telegram_username = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name='Telegram username'
    )
    
    FOCUS_CHOICES = [
        ('founder', 'Founder'),
        ('digital', 'Digital Lead'),
        ('media', 'Media Lead'),
        ('organization', 'Organization'),
    ]
    focus = models.CharField(max_length=255, choices=FOCUS_CHOICES)

    class Meta:
        verbose_name = 'Team member (Yashil Qullar)'
        verbose_name_plural = 'Team members (Yashil Qullar)'

    def __str__(self):
        # Ismni asosiy TGUser modelidan olamiz
        return self.tg_user.fullname







class EcoProject(TimeBasedModel):
    title = models.CharField(max_length=255, verbose_name='Nomi')
    description = models.TextField(verbose_name='Tavsif')
    date = models.DateTimeField(verbose_name='Sana va vaqt')
    location_name = models.CharField(max_length=255, verbose_name='Joy nomi')
    location_url = models.URLField(verbose_name='Google/Yandex Map linki', blank=True, null=True)
    photo = models.ImageField(upload_to='projects/', verbose_name='Rasm', blank=True, null=True)
    
    # Секретный код для начисления баллов
    secret_code = models.CharField(max_length=50, verbose_name='Maxfiy kod', blank=True, null=True)
    
    # Ссылка на спец. канал для этого эвента
    channel_link = models.URLField(verbose_name='Telegram kanal linki', blank=True, null=True)
    
    is_active = models.BooleanField(default=True, verbose_name='Faolmi')
    max_participants = models.PositiveIntegerField(blank=True, null=True, verbose_name='Maksimal ishtirokchilar')

    class Meta:
        verbose_name = 'Eco loyiha'
        verbose_name_plural = 'Eco loyihalar'

    def __str__(self):
        return self.title

class ProjectParticipation(TimeBasedModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Kutilmoqda' # Ожидает проверки
        REGISTERED = 'registered', 'Qabul qilindi' # Принят
        ATTENDED = 'attended', 'Keldi'
        REJECTED = 'rejected', 'Rad etildi'

    user = models.ForeignKey(TGUser, on_delete=models.CASCADE)
    project = models.ForeignKey(EcoProject, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING # По умолчанию — ожидание
    )

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_status = None
        if not is_new:
            # Получаем старый статус из базы
            old_status = ProjectParticipation.objects.get(pk=self.pk).status

        super().save(*args, **kwargs)

        # Если ты в админке поменял с 'pending' на 'registered'
        if old_status == 'pending' and self.status == 'registered':
            from tgbot.services.notifications import send_acceptance_msg
            import asyncio
            # Отправляем юзеру сообщение
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(send_acceptance_msg(self.user.tg_id, self.project))
            except:
                pass


class Partner(TimeBasedModel):
    name = models.CharField(max_length=255, verbose_name="Имя компании")
    description = models.TextField(blank=True, null=True, verbose_name="Описание партнерства")
    logo = models.ImageField(upload_to='partners_logos/', blank=True, null=True, verbose_name="Логотип")
    
    # Соцсети
    instagram = models.URLField(blank=True, null=True, verbose_name="Instagram Link")
    telegram = models.URLField(blank=True, null=True, verbose_name="Telegram Link")
    linkedin = models.URLField(blank=True, null=True, verbose_name="LinkedIn Link")
    
    is_active = models.BooleanField(default=True, verbose_name="Показывать в боте")

    class Meta:
        verbose_name = 'Партнер'
        verbose_name_plural = 'Партнеры'

    def __str__(self):
        return self.name