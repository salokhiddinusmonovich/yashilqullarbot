from rest_framework import serializers
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
    """Для отображения карточек в ленте (без полного текста и комментов)"""
    tags = TagSerializer(many=True, read_only=True)
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ['id', 'title', 'slug', 'cover_image', 'tags', 'read_time_minutes', 'likes_count', 'comments_count', 'created_at', 'is_featured']

    def get_comments_count(self, obj):
        return obj.comments.count()

class ArticleImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleImage
        fields = ['id', 'image']

class ArticleDetailSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    comments = serializers.SerializerMethodField()
    gallery_images = ArticleImageSerializer(many=True, read_only=True)

    class Meta:
        model = Article
        fields = ['id', 'title', 'slug', 'cover_image', 'content', 'author_name', 'author_role',
                  'tags', 'read_time_minutes', 'likes_count', 'created_at', 'comments',
                  'video', 'video_url', 'gallery_images']

    def get_comments(self, obj):
        top_level_comments = obj.comments.filter(parent__isnull=True).order_by('-created_at')
        return CommentSerializer(top_level_comments, many=True).data
    






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