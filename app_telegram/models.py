from django.db import models
from django.utils.html import format_html

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
 
    class Role(models.TextChoices):
        VOLUNTEER = 'volunteer', 'Volunteer'
        COORDINATOR = 'coordinator', 'Coordinator'
        MOBILOGRAPH = 'mobilograph', 'Mobilographer'
        IT = 'it', 'IT Specialist'
        ORGANIZER = 'organizer', 'Organizer'
        FOUNDER = 'Founder', 'Founder'
 
    # НОВОЕ: откуда пришёл юзер — нужно, чтобы фронт понимал,
    # какую форму логина показывать, и для аналитики.
    class AuthProvider(models.TextChoices):
        TELEGRAM = 'telegram', 'Telegram Bot'
        EMAIL = 'email', 'Email + Password'
        GOOGLE = 'google', 'Google'
 
    # ИЗМЕНЕНО: tg_id больше не обязателен — международный юзер его не имеет.
    # unique=True + null=True — Postgres допускает много NULL при unique-констрейнте.
    tg_id = models.BigIntegerField(
        unique=True, null=True, blank=True, db_index=True, verbose_name='id Telegram'
    )
 
    fullname = models.CharField(max_length=255)
    age = models.PositiveSmallIntegerField(blank=True, null=True)
 
    # ИЗМЕНЕНО: email теперь unique — это будет основной идентификатор
    # для email- и google-логина. null=True (не blank='') чтобы старые
    # telegram-юзера без email не конфликтовали друг с другом на unique.
    email = models.EmailField(max_length=255, unique=True, null=True, blank=True)
 
    phone = models.CharField(max_length=20, blank=True, null=True)
    username = models.CharField(max_length=255, blank=True, null=True, verbose_name='Username')
    experience = models.TextField(blank=True, null=True, verbose_name='tajribasi')
    photo = models.ImageField(upload_to='users_photos/', blank=True, null=True, verbose_name='Profil rasmi')
    region = models.CharField(max_length=20, choices=Region.choices, blank=True, null=True, verbose_name='Hudud')
    education_place = models.CharField(max_length=255, blank=True, null=True, verbose_name='O‘qish joyi')
    is_admin = models.BooleanField(default=False)
    balance = models.PositiveIntegerField(default=0, verbose_name="Эко-баллы")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VOLUNTEER, verbose_name='Статус / Роль')
 
    # НОВОЕ: хэш пароля для email-регистрации. Пусто у telegram-only юзеров.
    # Хранится через django.contrib.auth.hashers.make_password — НЕ plaintext.
    password = models.CharField(max_length=128, blank=True, null=True, verbose_name="Пароль (хэш)")
 
    auth_provider = models.CharField(
        max_length=20, choices=AuthProvider.choices, default=AuthProvider.TELEGRAM,
        verbose_name="Способ регистрации",
    )
 
    is_tester = models.BooleanField(default=False, verbose_name="Тестировщик")
 
    @property
    def rank(self):
        if self.balance < 150:
            return "🌱 Nihol (Росток)"
        elif self.balance < 300:
            return "🌳 Daraxt (Дерево)"
        else:
            return "🛡 Tabiat Himoyachisi (Защитник)"
    
    def set_password(self, raw_password: str):
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw_password)
 
    def check_password(self, raw_password: str) -> bool:
        from django.contrib.auth.hashers import check_password
        if not self.password:
            return False
        return check_password(raw_password, self.password)
 
    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'пользователи'
 
    def __str__(self):
        return f'{self.fullname} ({self.tg_id or self.email}) {self.role}'
 

class TeamMemberYashilQullar(TimeBasedModel):
    # Убрали OneToOneField к TGUser. Теперь это самостоятельная модель.
    fullname = models.CharField(max_length=255, verbose_name="F.I.SH (Имя)")
    photo = models.ImageField(upload_to='team_photos/', verbose_name="Rasm (Фото)")
    telegram_username = models.CharField(max_length=100, blank=True, null=True, verbose_name="Telegram Username (@...)")
    instagram = models.CharField(max_length=100, blank=True, null=True, verbose_name="Instagram username (@...)")
    skills = models.TextField(blank=True, null=True, verbose_name='Ko‘nikmalar (Навыки)')
    
    FOCUS_CHOICES = [
        ('founder', 'Founder'),
        ('digital', 'Digital Lead'),
        ('media', 'Media Lead'),
        ('organization', 'Organization'),
    ]
    focus = models.CharField(max_length=255, choices=FOCUS_CHOICES, verbose_name="Yo'nalishi (Роль)")

    class Meta:
        verbose_name = 'Team member (Yashil Qullar)'
        verbose_name_plural = 'Team members (Yashil Qullar)'

    def __str__(self):
        return self.fullname

class EcoProject(models.Model):
    title = models.CharField(max_length=255, verbose_name="Loyiha nomi")
    description = models.TextField(verbose_name="Tavsif", blank=True, null=True)
    date = models.DateTimeField(verbose_name="Sana va vaqt")
    location_name = models.CharField(max_length=255, verbose_name="Manzil nomi")
    photo = models.ImageField(upload_to='projects/', null=True, blank=True, verbose_name="Rasm")
    is_active = models.BooleanField(default=True, verbose_name="Faolmi?")
    max_participants = models.PositiveIntegerField(default=100, verbose_name="Макс. участников")

    # НОВОЕ: Ссылка на чат для этого проекта
    chat_link = models.URLField(blank=True, null=True, verbose_name="Ссылка на чат (для принятых)")
    region = models.CharField(
    max_length=20, 
    choices=TGUser.Region.choices, 
    default='tashkent_s', 
    verbose_name="Qaysi viloyat uchun?"
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Eco loyiha"
        verbose_name_plural = "Eco loyihalar"



class ProjectParticipation(models.Model):
    STATUS_CHOICES = [
        ('pending', '⏳ Кутиш (Ожидание)'), 
        ('approved', '✅ Қабул қилинди (Принят)'),
        ('attended', '🌟 Келди (Пришел +10 баллов)'),
        ('rejected', '❌ Рад этилди (Отклонен)'),
    ]

    user = models.ForeignKey(TGUser, on_delete=models.CASCADE, related_name='participations')
    project = models.ForeignKey(EcoProject, on_delete=models.CASCADE, related_name='participants')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    applied_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            old_obj = ProjectParticipation.objects.get(pk=self.pk)
            # Если статус изменился на "Пришёл" — даем монеты
            if old_obj.status != 'attended' and self.status == 'attended':
                self.user.balance += 10
                self.user.save()
            # Если статус был "Пришёл", но изменили на другой — забираем монеты
            elif old_obj.status == 'attended' and self.status != 'attended':
                if self.user.balance >= 10:
                    self.user.balance -= 10
                    self.user.save()
        elif self.status == 'attended':
            self.user.balance += 10
            self.user.save()
            
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ('user', 'project')
        verbose_name = "Ishtirokchi"
        verbose_name_plural = "Ishtirokchilar"


# # НОВОЕ: Модели для Магазина (Shop)
# class Product(TimeBasedModel):
#     name = models.CharField(max_length=255, verbose_name="Название товара")
#     description = models.TextField(verbose_name="Описание")
#     price = models.PositiveIntegerField(verbose_name="Цена в монетах")
#     image = models.ImageField(upload_to='shop/', verbose_name="Фото товара")
#     stock = models.PositiveIntegerField(default=0, verbose_name="Количество в наличии")

#     class Meta:
#         verbose_name = "Товар"
#         verbose_name_plural = "Товары"

#     def __str__(self):
#         return self.name

class Partner(TimeBasedModel):
    name = models.CharField(max_length=255, verbose_name="Имя компании")
    description = models.TextField(blank=True, null=True, verbose_name="Описание партнерства")
    logo = models.ImageField(upload_to='partners_logos/', blank=True, null=True, verbose_name="Логотип")
    instagram = models.URLField(blank=True, null=True, verbose_name="Instagram Link")
    telegram = models.URLField(blank=True, null=True, verbose_name="Telegram Link")
    linkedin = models.URLField(blank=True, null=True, verbose_name="LinkedIn Link")
    is_active = models.BooleanField(default=True, verbose_name="Показывать в боте")

    class Meta:
        verbose_name = 'Партнер'
        verbose_name_plural = 'Партнеры'

    def __str__(self):
        return self.name
    


class ProjectNotification(models.Model):
    project = models.ForeignKey(EcoProject, on_delete=models.CASCADE)
    user = models.ForeignKey(TGUser, on_delete=models.CASCADE)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'user')
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"






class Tag(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name
    
class Article(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    cover_image = models.ImageField(upload_to='blog/covers/', blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    video = models.FileField(upload_to='blog/videos/', blank=True, null=True, verbose_name="Video fayl (yuklash)")
    video_url = models.URLField(blank=True, null=True, verbose_name="Video havolasi (YouTube va h.k.)")
    
    # Данные автора как на скрине (например: "Aziz Karimov", "Founder")
    author = models.ForeignKey(
        'TGUser', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='articles',
        limit_choices_to={'is_admin': True},
        verbose_name="Muallif (faqat admin foydalanuvchilar)"
    )
    tags = models.ManyToManyField(Tag, related_name='articles')
    
    read_time_minutes = models.PositiveIntegerField(default=3)
    likes_count = models.PositiveIntegerField(default=0)
    
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
class ArticleImage(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='blog/gallery/')
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib raqami")

    class Meta:
        ordering = ['order']
        verbose_name = "Rasm (galereya)"
        verbose_name_plural = "Rasmlar (galereya)"

class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='comments')
    # Parent отвечает за вложенность (reply). Если null — это главный комментарий.
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    
    # Привязываем комментатора к твоей базе пользователей
    user = models.ForeignKey(TGUser, on_delete=models.CASCADE)
    text = models.TextField()
    
    likes_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.fullname} on {self.article.title}"
    


class LoginToken(models.Model):
    token = models.CharField(max_length=64, unique=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'pending'), ('confirmed', 'confirmed')],
        default='pending',
    )
    tg_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Токен входа'
        verbose_name_plural = 'Токены входа'


class EventFeedback(models.Model):
    user = models.ForeignKey(TGUser, on_delete=models.CASCADE, related_name='feedbacks')
    project = models.ForeignKey(EcoProject, on_delete=models.CASCADE, related_name='feedbacks')
    rating = models.PositiveSmallIntegerField(verbose_name="Baho (1-5)")
    comment = models.TextField(blank=True, null=True, verbose_name="Fikr-mulohaza")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'project')
        verbose_name = "Fikr-mulohaza"
        verbose_name_plural = "Fikr-mulohazalar"

    def __str__(self):
        return f"{self.user.fullname} — {self.project.title} ({self.rating}⭐)"
    



class ArticleLike(models.Model):
    """
    Кто именно лайкнул статью — раньше likes_count просто увеличивался
    без привязки к юзеру, поэтому нельзя было понять "лайкнул ли Я",
    и один юзер мог накрутить счётчик бесконечно.
    """
    article = models.ForeignKey('Article', on_delete=models.CASCADE, related_name='user_likes')
    user = models.ForeignKey(TGUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        unique_together = ('article', 'user')
        verbose_name = 'Лайк статьи'
        verbose_name_plural = 'Лайки статей'
 
 
class CommentLike(models.Model):
    """То же самое, но для комментариев."""
    comment = models.ForeignKey('Comment', on_delete=models.CASCADE, related_name='user_likes')
    user = models.ForeignKey(TGUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        unique_together = ('comment', 'user')
        verbose_name = 'Лайк комментария'
        verbose_name_plural = 'Лайки комментариев'
 
 
class EcoProjectImage(models.Model):
    """
    Множественные фото для эко-проекта (плоггинг и т.п.) — та же логика,
    что уже есть у ArticleImage для статей блога.
    """
    project = models.ForeignKey('EcoProject', on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='projects/gallery/')
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib raqami")
 
    class Meta:
        ordering = ['order']
        verbose_name = "Loyiha rasmi (galereya)"
        verbose_name_plural = "Loyiha rasmlari (galereya)"
 