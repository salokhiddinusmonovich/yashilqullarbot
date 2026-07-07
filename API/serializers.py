from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from app_telegram.models import TGUser, Article, Tag, Comment, TeamMemberYashilQullar, ArticleImage

class ProfileSerializer(serializers.ModelSerializer):
    # Добавляем кастомные поля для профиля, которые нужны на фронтенде
    rank = serializers.ReadOnlyField() # Берет из @property в модели
    projects_count = serializers.SerializerMethodField() # Считаем проекты

    class Meta:
        model = TGUser
        # ВАЖНО: Мы НЕ добавляем сюда никакие "trees", только то, что есть в модели
        fields = [
            'tg_id', 'fullname', 'username', 'photo', 'region', 
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
    # Берем fullname из твоей модели TGUser
    user_name = serializers.CharField(source='user.fullname', read_only=True)
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = ['id', 'user_name', 'text', 'likes_count', 'created_at', 'replies']

    def get_replies(self, obj):
        # Рекурсивно собираем ответы на этот комментарий
        if obj.replies.exists():
            return CommentSerializer(obj.replies.all(), many=True).data
        return []

class ArticleListSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    comments_count = serializers.SerializerMethodField()
    has_video = serializers.SerializerMethodField()
    author_name = serializers.SerializerMethodField()
    author_role = serializers.SerializerMethodField()
    author_photo = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ['id', 'title', 'slug', 'cover_image', 'tags', 'read_time_minutes', 'likes_count',
                  'comments_count', 'created_at', 'is_featured', 'author_name', 'author_role', 'author_photo', 'has_video']

    def get_comments_count(self, obj):
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

    class Meta:
        model = Article
        fields = ['id', 'title', 'slug', 'cover_image', 'content', 'tags',
                  'read_time_minutes', 'likes_count', 'created_at', 'comments',
                  'video', 'video_url', 'gallery_images',
                  'author_name', 'author_role', 'author_photo']

    def get_comments(self, obj):
        top_level_comments = obj.comments.filter(parent__isnull=True).order_by('-created_at')
        return CommentSerializer(top_level_comments, many=True).data

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
    






class TeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamMemberYashilQullar
        fields = [
            'id', 
            'fullname', 
            'photo', 
            'telegram_username', 
            'instagram', 
            'skills', 
            'focus'
        ]


class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        # Фронтенд передает только текст и (если это ответ) ID родительского коммента
        fields = ['text', 'parent']





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
        if TGUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
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
 
        if not user.check_password(attrs['password']):
            raise serializers.ValidationError("Invalid email or password.")
 
        attrs['user'] = user
        return attrs