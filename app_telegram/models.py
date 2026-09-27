from django.db import models
from django.utils.html import format_html

from .i18n import tr

class TimeBasedModel(models.Model):
    class Meta:
        abstract = True
        ordering = ('-created',)

    created = models.DateTimeField(auto_now_add=True, verbose_name=tr('f_created'))
    updated = models.DateTimeField(auto_now=True, verbose_name=tr('f_updated'))


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
        HEAD_COORDINATOR = 'head_coordinator', 'Head of Coordinators'
        MAIN_COORDINATOR = 'main_coordinator', 'Main Coordinator' 
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
        unique=True, null=True, blank=True, db_index=True, verbose_name=tr('f_tg_id')
    )
 
    fullname = models.CharField(max_length=255, verbose_name=tr('f_fullname'))
    age = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name=tr('f_age'))
 
    # ИЗМЕНЕНО: email теперь unique — это будет основной идентификатор
    # для email- и google-логина. null=True (не blank='') чтобы старые
    # telegram-юзера без email не конфликтовали друг с другом на unique.
    email = models.EmailField(max_length=255, unique=True, null=True, blank=True)
    bio = models.TextField(blank=True, null=True, verbose_name="Bio")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name=tr('f_phone'))
    username = models.CharField(max_length=255, blank=True, null=True, verbose_name=tr('f_username'))
    experience = models.TextField(blank=True, null=True, verbose_name=tr('f_experience'))
    photo = models.ImageField(upload_to='users_photos/', blank=True, null=True, verbose_name=tr('f_photo'))
    region = models.CharField(max_length=20, choices=Region.choices, blank=True, null=True, verbose_name=tr('f_region'), db_index=True)
    education_place = models.CharField(max_length=255, blank=True, null=True, verbose_name=tr('f_education'))
    is_admin = models.BooleanField(default=False, verbose_name=tr('f_is_admin'))
    balance = models.PositiveIntegerField(default=0, verbose_name=tr('f_balance'), db_index=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VOLUNTEER, verbose_name=tr('f_role'), db_index=True)
 
    # НОВОЕ: хэш пароля для email-регистрации. Пусто у telegram-only юзеров.
    # Хранится через django.contrib.auth.hashers.make_password — НЕ plaintext.
    password = models.CharField(max_length=128, blank=True, null=True, verbose_name=tr('f_password'))
 
    auth_provider = models.CharField(
        max_length=20, choices=AuthProvider.choices, default=AuthProvider.TELEGRAM,
        verbose_name=tr('f_auth_provider'),
    )
 
    is_tester = models.BooleanField(default=False, verbose_name=tr('f_is_tester'))
 
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
    
    @property
    def is_authenticated(self):
        # Если у нас вообще есть объект TGUser (а не AnonymousUser) —
        # значит JWT уже успешно проверен, юзер аутентифицирован.
        return True
 
    @property
    def is_anonymous(self):
        return False
 
    class Meta:
        verbose_name = tr('user')
        verbose_name_plural = tr('users')
 
    def __str__(self):
        return f'{self.fullname} ({self.tg_id or self.email}) {self.role}'
 

class TeamMemberYashilQullar(models.Model):
    FOCUS_CHOICES = [
        ('founder', 'Founder'),
        ('media', 'Media Lead'),
        ('organization', 'Organization'),
        # 'digital' убран — если у кого-то из существующих участников
        # стоял именно этот focus, см. миграцию данных ниже, иначе
        # значение останется в базе, но не будет валидным выбором в форме.
    ]
 
    fullname = models.CharField(max_length=255)
    photo = models.ImageField(upload_to='team_photos/', blank=True, null=True)
    telegram_username = models.CharField(max_length=255, blank=True, null=True)
    instagram = models.CharField(max_length=255, blank=True, null=True)
    github = models.URLField(blank=True, null=True, verbose_name="GitHub")
    linkedin = models.URLField(blank=True, null=True, verbose_name="LinkedIn")
    bio = models.TextField(blank=True, null=True, verbose_name="Bio")  # ← было skills
    focus = models.CharField(max_length=20, choices=FOCUS_CHOICES, default='organization')
 
    def __str__(self):
        return self.fullname

class EcoProject(models.Model):
    title = models.CharField(max_length=255, verbose_name=tr('f_title'))
    description = models.TextField(verbose_name=tr('f_description'), blank=True, null=True)
    date = models.DateTimeField(verbose_name=tr('f_date'))
    location_name = models.CharField(max_length=255, verbose_name=tr('f_location'))
    photo = models.ImageField(upload_to='projects/', null=True, blank=True, verbose_name=tr('f_photo'))
    is_active = models.BooleanField(default=True, verbose_name=tr('f_is_active'))
    max_participants = models.PositiveIntegerField(default=100, verbose_name=tr('f_max'))
    likes_count = models.PositiveIntegerField(default=0, verbose_name=tr('f_likes'))
    # НОВОЕ: Ссылка на чат для этого проекта
    chat_link = models.URLField(blank=True, null=True, verbose_name=tr('f_chat_link'))
    region = models.CharField(
    max_length=20, 
    choices=TGUser.Region.choices, 
    default='tashkent_s', 
    verbose_name=tr('f_project_region')
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = tr('project')
        verbose_name_plural = tr('projects')
        indexes = [
            models.Index(fields=['is_active', 'date'], name='ecoproj_active_date_idx'),
        ]



class ProjectParticipation(models.Model):
    STATUS_CHOICES = [
        ('approved', tr('st_approved')),
        ('attended', tr('st_attended')),
        ('rejected', tr('st_rejected')),
    ]

    user = models.ForeignKey(TGUser, on_delete=models.CASCADE, related_name='participations', verbose_name=tr('user'))
    project = models.ForeignKey(EcoProject, on_delete=models.CASCADE, related_name='participants', verbose_name=tr('project'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name=tr('f_status'))
    applied_at = models.DateTimeField(auto_now_add=True, verbose_name=tr('f_applied_at'))

    def save(self, *args, **kwargs):
        became_attended = False
        if self.pk:
            old_obj = ProjectParticipation.objects.get(pk=self.pk)
            # Если статус изменился на "Пришёл" — даем монеты
            if old_obj.status != 'attended' and self.status == 'attended':
                became_attended = True
                self.user.balance += 10
                self.user.save()
            # Если статус был "Пришёл", но изменили на другой — забираем монеты
            elif old_obj.status == 'attended' and self.status != 'attended':
                if self.user.balance >= 10:
                    self.user.balance -= 10
                    self.user.save()
        elif self.status == 'attended':
            became_attended = True
            self.user.balance += 10
            self.user.save()

        super().save(*args, **kwargs)
        if became_attended:
            # «Пригласи друга»: первый приход друга → бонус пригласившему (app_telegram/referrals.py)
            from . import referrals
            referrals.on_attended(self.user)

    class Meta:
        unique_together = ('user', 'project')
        verbose_name = tr('participation')
        verbose_name_plural = tr('participations')


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
    name = models.CharField(max_length=255, verbose_name=tr('f_name'))
    description = models.TextField(blank=True, null=True, verbose_name=tr('f_description'))
    logo = models.ImageField(upload_to='partners_logos/', blank=True, null=True, verbose_name=tr('f_logo'))
    instagram = models.URLField(blank=True, null=True, verbose_name="Instagram Link")
    telegram = models.URLField(blank=True, null=True, verbose_name="Telegram Link")
    linkedin = models.URLField(blank=True, null=True, verbose_name="LinkedIn Link")
    is_active = models.BooleanField(default=True, verbose_name=tr('f_show_in_bot'))

    class Meta:
        verbose_name = tr('partner')
        verbose_name_plural = tr('partners')

    def __str__(self):
        return self.name
    


class ProjectNotification(models.Model):
    project = models.ForeignKey(EcoProject, on_delete=models.CASCADE)
    user = models.ForeignKey(TGUser, on_delete=models.CASCADE)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'user')
        verbose_name = tr('notification')
        verbose_name_plural = tr('notifications')






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
        verbose_name = tr('article_image')
        verbose_name_plural = tr('article_images')

class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='comments')
    # Parent отвечает за вложенность (reply). Если null — это главный комментарий.
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    
    # Привязываем комментатора к твоей базе пользователей
    user = models.ForeignKey(TGUser, on_delete=models.CASCADE)
    text = models.TextField()
    
    likes_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['article', 'parent'], name='comment_article_parent_idx'),
        ]

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
        verbose_name = tr('login_token')
        verbose_name_plural = tr('login_tokens')


class EventFeedback(models.Model):
    user = models.ForeignKey(TGUser, on_delete=models.CASCADE, related_name='feedbacks')
    project = models.ForeignKey(EcoProject, on_delete=models.CASCADE, related_name='feedbacks')
    rating = models.PositiveSmallIntegerField(verbose_name=tr('f_rating'))
    comment = models.TextField(blank=True, null=True, verbose_name=tr('f_comment'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'project')
        verbose_name = tr('feedback')
        verbose_name_plural = tr('feedbacks')

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
        verbose_name = tr('project_image')
        verbose_name_plural = tr('project_images')
 

class EcoProjectComment(models.Model):
    project = models.ForeignKey('EcoProject', on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    user = models.ForeignKey(TGUser, on_delete=models.CASCADE)
    text = models.TextField()
    likes_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['project', 'parent'], name='ecoprojcomment_proj_par_idx'),
        ]

    def __str__(self):
        return f"Comment by {self.user.fullname} on {self.project.title}"
 
 
class EcoProjectCommentLike(models.Model):
    comment = models.ForeignKey(EcoProjectComment, on_delete=models.CASCADE, related_name='user_likes')
    user = models.ForeignKey(TGUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        unique_together = ('comment', 'user')
 
 
class EcoProjectLike(models.Model):
    project = models.ForeignKey('EcoProject', on_delete=models.CASCADE, related_name='user_likes')
    user = models.ForeignKey(TGUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        unique_together = ('project', 'user')
 