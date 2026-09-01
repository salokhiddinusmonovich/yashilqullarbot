from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.db.models import Exists, OuterRef, Value, BooleanField, Prefetch
from app_telegram.models import (
    TGUser, Article, Tag, Comment, TeamMemberYashilQullar, ArticleImage, EcoProject, EcoProjectImage,
    ProjectParticipation, EcoProjectComment, Partner, ArticleLike, CommentLike, EcoProjectCommentLike,
)


def _comments_queryset_with_liked_flag(comment_model, like_model, like_fk_name, user, is_auth):
    """
    select_related('user') убирает N+1 на user_name/user_photo, а
    annotate(is_liked_by_me_annotated) убирает по одному лишнему запросу
    на КАЖДЫЙ комментарий, который раньше делал get_is_liked_by_me().
    """
    qs = comment_model.objects.select_related('user').order_by('-created_at')
    if is_auth:
        qs = qs.annotate(
            is_liked_by_me_annotated=Exists(
                like_model.objects.filter(**{like_fk_name: OuterRef('pk'), 'user': user})
            )
        )
    else:
        qs = qs.annotate(is_liked_by_me_annotated=Value(False, output_field=BooleanField()))
    return qs


class ProfileSerializer(serializers.ModelSerializer):
    # Добавляем кастомные поля для профиля, которые нужны на фронтенде
    rank = serializers.ReadOnlyField() # Берет из @property в модели
    projects_count = serializers.SerializerMethodField() # Считаем проекты

    class Meta:
        model = TGUser
        # ВАЖНО: Мы НЕ добавляем сюда никакие "trees", только то, что есть в модели
        fields = [
           "id", 'tg_id', 'fullname', 'username', 'photo', 'region', 
            'balance', 'rank', 'projects_count', 
            'age', 'email', 'phone', 'education_place', 'experience', 'role'
        ]
        # Запрещаем юзеру самому себе накручивать баланс или ранг через PATCH
        read_only_fields = ['tg_id', 'balance', 'rank', 'projects_count']

    def get_projects_count(self, obj):
        # Подсчитываем количество проектов, где статус 'attended' (Келди)
        return obj.participations.filter(status='attended').count()
    




class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']

class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.fullname', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_photo = serializers.SerializerMethodField()
    is_liked_by_me = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()
 
    class Meta:
        model = Comment
        fields = ['id', 'user_id', 'user_name', 'user_photo', 'text', 'likes_count',
                  'is_liked_by_me', 'created_at', 'replies']
 
    def get_user_photo(self, obj):
        if obj.user and obj.user.photo:
            request = self.context.get('request')
            url = obj.user.photo.url
            return request.build_absolute_uri(url) if request else url
        return None
 
    def get_is_liked_by_me(self, obj):
        # Заполняется через annotate() в get_comments() ниже — без него
        # каждый комментарий бил бы по базе отдельным запросом (N+1).
        annotated = getattr(obj, 'is_liked_by_me_annotated', None)
        if annotated is not None:
            return annotated
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not request or not user or not getattr(user, 'is_authenticated', False):
            return False
        return obj.user_likes.filter(user=user).exists()

    def get_replies(self, obj):
        # obj.replies.all() переиспользует prefetch_related-кэш, если он был
        # проставлен в get_comments() — отдельный obj.replies.exists() здесь
        # раньше удваивал число запросов без всякой пользы.
        replies = obj.replies.all()
        if replies:
            # ВАЖНО: context=self.context — без этого is_liked_by_me/user_photo
            # у вложенных ответов всегда были бы пустыми/False.
            return CommentSerializer(replies, many=True, context=self.context).data
        return []


class ArticleListSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    comments_count = serializers.SerializerMethodField()
    has_video = serializers.SerializerMethodField()
    author_name = serializers.SerializerMethodField()
    author_role = serializers.SerializerMethodField()
    author_photo = serializers.SerializerMethodField()
    author_id = serializers.IntegerField(source='author.id', read_only=True, allow_null=True)

    class Meta:
        model = Article
        fields = ['id', 'title', 'slug', 'cover_image', 'tags', 'read_time_minutes', 'likes_count', 'is_liked_by_me',
          'comments_count', 'created_at', 'is_featured', 'author_name', 'author_role', 'author_photo', 'has_video', 'author_id']

    def get_comments_count(self, obj):
        # Проставляется через annotate(Count('comments')) в ArticleViewSet —
        # иначе это отдельный SELECT COUNT на каждую статью в списке (N+1).
        annotated = getattr(obj, 'comments_count_annotated', None)
        if annotated is not None:
            return annotated
        return obj.comments.count()

    def get_has_video(self, obj):
        return bool((obj.video and obj.video.name) or (obj.video_url and obj.video_url.strip()))

    def get_author_name(self, obj):
        return obj.author.fullname if obj.author else None

    def get_author_role(self, obj):
        if obj.author:
            return obj.author.get_role_display()
        return None

    def get_author_photo(self, obj):
        if obj.author and obj.author.photo:
            request = self.context.get('request')
            url = obj.author.photo.url
            return request.build_absolute_uri(url) if request else url
        return None
    
    is_liked_by_me = serializers.SerializerMethodField()

    def get_is_liked_by_me(self, obj):
        # Проставляется через annotate(Exists(...)) в ArticleViewSet.get_queryset —
        # без него это отдельный SELECT ... EXISTS на каждую статью в списке (N+1).
        annotated = getattr(obj, 'is_liked_by_me_annotated', None)
        if annotated is not None:
            return annotated
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not request or not user or not getattr(user, 'is_authenticated', False):
            return False
        return obj.user_likes.filter(user=user).exists()


class ArticleImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleImage
        fields = ['id', 'image']

class ArticleDetailSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    comments = serializers.SerializerMethodField()
    gallery_images = ArticleImageSerializer(many=True, read_only=True)
    author_name = serializers.SerializerMethodField()
    author_role = serializers.SerializerMethodField()
    author_photo = serializers.SerializerMethodField()
    author_id = serializers.IntegerField(source='author.id', read_only=True, allow_null=True)

    class Meta:
        model = Article
        fields = ['id', 'title', 'slug', 'cover_image', 'content', 'tags',
          'read_time_minutes', 'likes_count', 'is_liked_by_me', 'created_at', 'comments',
          'video', 'video_url', 'gallery_images',
          'author_name', 'author_role', 'author_photo', 'author_id']

    def get_comments(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        is_auth = bool(request and user and getattr(user, 'is_authenticated', False))

        # Глубина вложенности реплаев не ограничена схемой (parent — self-FK),
        # но на практике треды редко уходят глубже пары уровней. Явно
        # прогружаем 2 уровня replies через prefetch_related (article + 2
        # уровня комментариев вместо N+1 SELECT'ов на каждый узел дерева);
        # более глубокая вложенность просто упадёт обратно на обычный
        # запрос внутри CommentSerializer.get_replies — работает всегда,
        # просто без этой оптимизации на экстремальной глубине.
        replies_qs = _comments_queryset_with_liked_flag(Comment, CommentLike, 'comment', user, is_auth)

        top_level_comments = obj.comments.filter(parent__isnull=True).select_related('user').order_by('-created_at')
        if is_auth:
            top_level_comments = top_level_comments.annotate(
                is_liked_by_me_annotated=Exists(CommentLike.objects.filter(comment=OuterRef('pk'), user=user))
            )
        else:
            top_level_comments = top_level_comments.annotate(
                is_liked_by_me_annotated=Value(False, output_field=BooleanField())
            )
        top_level_comments = top_level_comments.prefetch_related(
            Prefetch('replies', queryset=replies_qs.prefetch_related(Prefetch('replies', queryset=replies_qs)))
        )
        return CommentSerializer(top_level_comments, many=True, context=self.context).data

    def get_author_name(self, obj):
        return obj.author.fullname if obj.author else None

    def get_author_role(self, obj):
        if obj.author:
            return obj.author.get_role_display()
        return None

    def get_author_photo(self, obj):
        if obj.author and obj.author.photo:
            request = self.context.get('request')
            url = obj.author.photo.url
            return request.build_absolute_uri(url) if request else url
        return None

    is_liked_by_me = serializers.SerializerMethodField()

    def get_is_liked_by_me(self, obj):
        annotated = getattr(obj, 'is_liked_by_me_annotated', None)
        if annotated is not None:
            return annotated
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not request or not user or not getattr(user, 'is_authenticated', False):
            return False
        return obj.user_likes.filter(user=user).exists()



class TeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamMemberYashilQullar
        fields = ['id', 'fullname', 'photo', 'telegram_username', 'instagram', 'github', 'linkedin', 'bio', 'focus']

class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        # Фронтенд передает только текст и (если это ответ) ID родительского коммента
        fields = ['text', 'parent']


class CommentEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        # Только текст — автора, статью, parent и лайки менять через
        # редактирование нельзя, это не то же самое, что создать заново.
        fields = ['text']


 
 
class RegisterSerializer(serializers.ModelSerializer):
    """
    POST /register/
    Body: { fullname, email, password }
    """
    password = serializers.CharField(write_only=True, min_length=8)
 
    class Meta:
        model = TGUser
        fields = ['fullname', 'email', 'password']
 
    def validate_email(self, value):
        existing = TGUser.objects.filter(email=value).first()
        if existing:
            if existing.tg_id:
                # Уже зарегистрирован через Telegram-бота — это не "email занят",
                # это конкретная и полезная подсказка, что делать дальше.
                raise serializers.ValidationError(
                    "This email is already registered via our Telegram bot. "
                    "Please sign in using Telegram instead of creating a new account."
                )
            raise serializers.ValidationError(
                "An account with this email already exists. Try signing in instead."
            )
        return value
 
    def validate_password(self, value):
        # Использует стандартные Django-валидаторы из AUTH_PASSWORD_VALIDATORS
        # в settings.py (длина, похожесть на данные юзера, распространённость и т.д.)
        validate_password(value)
        return value
 
    def create(self, validated_data):
        raw_password = validated_data.pop('password')
        user = TGUser(
            fullname=validated_data['fullname'],
            email=validated_data['email'],
            auth_provider=TGUser.AuthProvider.EMAIL,
        )
        user.set_password(raw_password)
        user.save()
        return user
 
 
class PasswordLoginSerializer(serializers.Serializer):
    """
    POST /login/password/
    Body: { email, password }
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
 
    def validate(self, attrs):
        try:
            user = TGUser.objects.get(email=attrs['email'])
        except TGUser.DoesNotExist:
            raise serializers.ValidationError("Invalid email or password.")
 
        if not user.password:
            # Аккаунт создан через Telegram-бота — там пароль никогда не
            # спрашивается и не сохраняется (password=NULL). "Invalid email
            # or password" тут вводит в заблуждение — пароля там в принципе
            # никогда не было. Говорим честно, что делать дальше.
            raise serializers.ValidationError(
                "This account was created via our Telegram bot and has no password. "
                "Please use \"Continue with Telegram\" below instead."
            )
 
        if not user.check_password(attrs['password']):
            raise serializers.ValidationError("Invalid email or password.")
 
        attrs['user'] = user
        return attrs
    


class EcoProjectImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EcoProjectImage
        fields = ['id', 'image']

class EcoProjectCommentSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_name = serializers.CharField(source='user.fullname', read_only=True)
    user_photo = serializers.SerializerMethodField()
    is_liked_by_me = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()
 
    class Meta:
        model = EcoProjectComment
        fields = ['id', 'user_id', 'user_name', 'user_photo', 'text', 'likes_count',
                  'is_liked_by_me', 'created_at', 'replies']
 
    def get_user_photo(self, obj):
        if obj.user and obj.user.photo:
            request = self.context.get('request')
            url = obj.user.photo.url
            return request.build_absolute_uri(url) if request else url
        return None
 
    def get_is_liked_by_me(self, obj):
        annotated = getattr(obj, 'is_liked_by_me_annotated', None)
        if annotated is not None:
            return annotated
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not request or not user or not getattr(user, 'is_authenticated', False):
            return False
        return obj.user_likes.filter(user=user).exists()

    def get_replies(self, obj):
        replies = obj.replies.all()
        if replies:
            return EcoProjectCommentSerializer(replies, many=True, context=self.context).data
        return []


class EcoProjectCommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EcoProjectComment
        fields = ['text', 'parent']


class EcoProjectCommentEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = EcoProjectComment
        fields = ['text']
 
 
class EcoProjectImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EcoProjectImage
        fields = ['id', 'image']
 
 
class EcoProjectSerializer(serializers.ModelSerializer):
    """
    GET /projects/ и /projects/<id>/
    Теперь ведёт себя как полноценный пост: лайки, комментарии, галерея.
    title/description/location_name переводятся modeltranslation-ом по Accept-Language.
    """
    gallery_images = EcoProjectImageSerializer(many=True, read_only=True)
    region_display = serializers.CharField(source='get_region_display', read_only=True)
    participants_count = serializers.SerializerMethodField()
    is_joined = serializers.SerializerMethodField()
    is_liked_by_me = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
 
    class Meta:
        model = EcoProject
        fields = [
            'id', 'title', 'description', 'date', 'location_name', 'photo',
            'gallery_images', 'is_active', 'max_participants', 'participants_count',
            'region', 'region_display', 'is_joined', 'chat_link',
            'likes_count', 'is_liked_by_me', 'comments_count', 'comments',
        ]
 
    def get_participants_count(self, obj):
        annotated = getattr(obj, 'participants_count_annotated', None)
        if annotated is not None:
            return annotated
        return obj.participants.filter(status__in=['approved', 'attended']).count()

    def get_is_joined(self, obj):
        annotated = getattr(obj, 'is_joined_annotated', None)
        if annotated is not None:
            return annotated
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not request or not user or not getattr(user, 'is_authenticated', False):
            return False
        return obj.participants.filter(user=user).exists()

    def get_is_liked_by_me(self, obj):
        annotated = getattr(obj, 'is_liked_by_me_annotated', None)
        if annotated is not None:
            return annotated
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not request or not user or not getattr(user, 'is_authenticated', False):
            return False
        return obj.user_likes.filter(user=user).exists()

    def get_comments_count(self, obj):
        annotated = getattr(obj, 'comments_count_annotated', None)
        if annotated is not None:
            return annotated
        return obj.comments.count()

    def get_comments(self, obj):
        # Для списка (/projects/) это довольно дорого при много проектов —
        # если список большой, можно позже отдавать comments только в detail.
        # Пока оставляем одинаково для простоты (мало проектов на старте).
        # select_related('user') + annotate(is_liked_by_me) + 2 уровня
        # prefetch на replies убирают N+1 запросов, которые раньше шли на
        # каждый комментарий И на каждый его лайк-чек отдельно.
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        is_auth = bool(request and user and getattr(user, 'is_authenticated', False))

        replies_qs = _comments_queryset_with_liked_flag(
            EcoProjectComment, EcoProjectCommentLike, 'comment', user, is_auth
        )

        top_level = obj.comments.filter(parent__isnull=True).select_related('user').order_by('-created_at')
        if is_auth:
            top_level = top_level.annotate(
                is_liked_by_me_annotated=Exists(EcoProjectCommentLike.objects.filter(comment=OuterRef('pk'), user=user))
            )
        else:
            top_level = top_level.annotate(
                is_liked_by_me_annotated=Value(False, output_field=BooleanField())
            )
        top_level = top_level.prefetch_related(
            Prefetch('replies', queryset=replies_qs.prefetch_related(Prefetch('replies', queryset=replies_qs)))
        )
        return EcoProjectCommentSerializer(top_level, many=True, context=self.context).data
 
class RegionTeamMemberSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    region_display = serializers.CharField(source='get_region_display', read_only=True)
 
    class Meta:
        model = TGUser
        fields = [
            'id', 'fullname', 'photo', 'role', 'role_display',
            'region_display', 'balance',
            'username', 'experience',
        ]

class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = ['id', 'name', 'description', 'logo', 'instagram', 'telegram', 'linkedin']



class LeaderboardEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = TGUser
        fields = ['tg_id', 'fullname', 'photo', 'balance', 'rank', 'region']
 