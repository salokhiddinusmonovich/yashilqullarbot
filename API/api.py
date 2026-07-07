import hashlib
import hmac
from django.conf import settings
from rest_framework import status, views, generics
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from app_telegram.models import TGUser, Article, TeamMemberYashilQullar, Comment
from .serializers import ProfileSerializer, ArticleListSerializer, ArticleDetailSerializer, TeamMemberSerializer, CommentCreateSerializer
from rest_framework import viewsets

class TelegramLoginView(views.APIView):
    """
    POST /api/auth/login/
    Body: Telegram widget data { id, first_name, last_name?, username?, photo_url?, auth_date, hash }
    Returns: { access, refresh, user }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        data = {k: v[0] if isinstance(v, list) else v for k, v in request.data.items()} # mutable copy

        # 1. Extract hash before building check string
        hash_val = data.pop('hash', None)
        if not hash_val:
            return Response({"error": "Missing hash"}, status=status.HTTP_400_BAD_REQUEST)

        tg_id = data.get('id')
        if not tg_id:
            return Response({"error": "Missing id"}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Verify Telegram hash
        data_check_string = "\n".join(
            [f"{k}={v}" for k, v in sorted(data.items())]
        )
        secret_key = hashlib.sha256(
            settings.TELEGRAM_BOT_TOKEN.encode()
        ).digest()
        expected_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        if hash_val != expected_hash:
            return Response(
                {"error": "Invalid hash — Telegram verification failed"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 3. Get or create TGUser
        fullname = data.get('first_name', '')
        last_name = data.get('last_name', '')
        if last_name:
            fullname = f"{fullname} {last_name}"

        tg_user, created = TGUser.objects.get_or_create(
            tg_id=int(tg_id),
            defaults={
                'fullname': fullname,
                'username': data.get('username', ''),
                # ВАЖНО: None, а не '' — email теперь unique=True.
                # Telegram-виджет никогда не присылает email, так что
                # '' у двух разных юзеров подряд = мгновенный
                # UniqueViolation при следующей же регистрации через бота.
                # None безопасен: unique допускает сколько угодно NULL.
                'email': None,
                'phone': None,
            }
        )

        # Update name/username if returning user
        if not created:
            tg_user.fullname = fullname
            if data.get('username'):
                tg_user.username = data.get('username')
            tg_user.save(update_fields=['fullname', 'username'])

        # 4. Generate JWT — we use tg_id as the token subject
        #    We create tokens manually without Django User
        refresh = CustomRefreshToken.for_tg_user(tg_user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": ProfileSerializer(tg_user).data,
        }, status=status.HTTP_200_OK)


class CustomRefreshToken(RefreshToken):
    """
    Custom token that stores tg_id instead of Django user pk.
    """
    @classmethod
    def for_tg_user(cls, tg_user: TGUser):
        token = cls()
        token['tg_id'] = tg_user.tg_id
        token['fullname'] = tg_user.fullname
        return token


class TGUserJWTAuthentication(JWTAuthentication):
    """
    Custom authenticator that resolves TGUser from JWT tg_id claim.
    Use this instead of default JWTAuthentication.
    Add to settings: REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES
    """
    def get_user(self, validated_token):
        tg_id = validated_token.get('tg_id')
        if not tg_id:
            raise InvalidToken("Token contains no tg_id")
        try:
            return TGUser.objects.get(tg_id=tg_id)
        except TGUser.DoesNotExist:
            raise InvalidToken("TGUser not found")


class LogoutView(views.APIView):
    """
    POST /api/auth/logout/
    Body: { refresh }
    Blacklists the refresh token.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"error": "Refresh token required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"detail": "Successfully logged out"},
                status=status.HTTP_200_OK
            )
        except TokenError:
            return Response(
                {"error": "Invalid or expired token"},
                status=status.HTTP_400_BAD_REQUEST
            )


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/auth/me/   — get current user profile
    PATCH /api/auth/me/   — update current user profile
    Requires: Authorization: Bearer <access_token>
    """
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TGUserJWTAuthentication]
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_object(self):
        # request.user is now the TGUser instance (set by TGUserJWTAuthentication)
        return self.request.user
    

class TeamListView(generics.ListAPIView):
    """
    GET /api/team/
    Возвращает список всех волонтеров команды Yashil Qo'llar.
    Фронтенд должен сгруппировать их по полю 'focus' (founder, digital, media, organization).
    """
    # Сортируем по ID или можешь добавить поле order в модель позже
    queryset = TeamMemberYashilQullar.objects.all().order_by('id') 
    serializer_class = TeamMemberSerializer
    permission_classes = [AllowAny]


class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/blog/ — список всех статей
    GET /api/blog/{id}/ — конкретная статья со всеми комментариями
    """
    queryset = Article.objects.all().order_by('-created_at')
    permission_classes = [AllowAny] 
    
    # Для поиска по URL-slug вместо ID (например: /api/blog/aral-sea-project/)
    lookup_field = 'slug'

    def get_serializer_class(self):
        # Если запрашивают одну статью — отдаем детальный сериализатор, если список — короткий
        if self.action == 'retrieve':
            return ArticleDetailSerializer
        return ArticleListSerializer
    


class CommentCreateView(generics.CreateAPIView):
    """
    POST /api/blog/<slug>/comment/
    Body: { "text": "Супер статья!", "parent": null }
    """
    serializer_class = CommentCreateSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TGUserJWTAuthentication]

    def perform_create(self, serializer):
        # Достаем статью по slug из URL
        slug = self.kwargs.get('slug')
        article = get_object_or_404(Article, slug=slug)
        
        # Сохраняем коммент, жестко привязывая его к текущему юзеру и статье
        serializer.save(user=self.request.user, article=article)


class ArticleLikeView(views.APIView):
    """
    POST /api/blog/<slug>/like/
    Просто дергаем этот эндпоинт, чтобы добавить лайк статье.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [TGUserJWTAuthentication]

    def post(self, request, slug):
        article = get_object_or_404(Article, slug=slug)
        article.likes_count += 1
        article.save(update_fields=['likes_count'])
        
        return Response(
            {"message": "Article liked", "likes_count": article.likes_count},
            status=status.HTTP_200_OK
        )


class CommentLikeView(views.APIView):
    """
    POST /api/comment/<id>/like/
    Дергаем эндпоинт, чтобы лайкнуть конкретный коммент.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [TGUserJWTAuthentication]

    def post(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        comment.likes_count += 1
        comment.save(update_fields=['likes_count'])
        
        return Response(
            {"message": "Comment liked", "likes_count": comment.likes_count},
            status=status.HTTP_200_OK
        )
    

import uuid
from app_telegram.models import LoginToken

class CreateLoginTokenView(views.APIView):
    """
    POST /login/token/
    Создаёт одноразовый токен и deep-link на бота.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        token = uuid.uuid4().hex
        LoginToken.objects.create(token=token)
        bot_username = settings.TELEGRAM_BOT_USERNAME
        return Response({
            "token": token,
            "deep_link": f"https://t.me/{bot_username}?start=login_{token}",
        })


class LoginTokenStatusView(views.APIView):
    """
    GET /login/token/<token>/
    Фронт поллит этот эндпоинт, пока не увидит status: confirmed.
    """
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            lt = LoginToken.objects.get(token=token)
        except LoginToken.DoesNotExist:
            return Response({"status": "expired"}, status=status.HTTP_404_NOT_FOUND)

        if lt.status == 'confirmed' and lt.tg_id:
            tg_user = get_object_or_404(TGUser, tg_id=lt.tg_id)
            refresh = CustomRefreshToken.for_tg_user(tg_user)
            lt.delete()  # одноразовый — использовали, удалили
            return Response({
                "status": "confirmed",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": ProfileSerializer(tg_user).data,
            })

        return Response({"status": lt.status})
    



class CustomRefreshToken(RefreshToken):
    """
    Универсальный токен для ЛЮБОГО способа входа (telegram / email / google).
    Кладём pk (uid) — это работает для всех, включая юзеров без tg_id.
    """
    @classmethod
    def for_tg_user(cls, tg_user: TGUser):
        # оставлено для обратной совместимости с существующим кодом,
        # который его вызывает (TelegramLoginView и т.д.)
        return cls.for_user_obj(tg_user)
 
    @classmethod
    def for_user_obj(cls, user: TGUser):
        token = cls()
        token['uid'] = user.pk
        token['fullname'] = user.fullname
        return token
 
 
class TGUserJWTAuthentication(JWTAuthentication):
    """
    Сначала пробуем новый claim 'uid' (pk) — работает для всех юзеров.
    Если его нет (старый токен, выданный до этого изменения) — fallback на tg_id.
    """
    def get_user(self, validated_token):
        uid = validated_token.get('uid')
        if uid is not None:
            try:
                return TGUser.objects.get(pk=uid)
            except TGUser.DoesNotExist:
                raise InvalidToken("User not found")
 
        tg_id = validated_token.get('tg_id')
        if tg_id:
            try:
                return TGUser.objects.get(tg_id=tg_id)
            except TGUser.DoesNotExist:
                raise InvalidToken("TGUser not found")
 
        raise InvalidToken("Token contains no user identifier")
 
 
"""
2) ДОБАВИТЬ эти вьюхи (после LogoutView, например).
"""
from .serializers import RegisterSerializer, PasswordLoginSerializer
 
 
class RegisterView(views.APIView):
    """
    POST /register/
    Body: { fullname, email, password }
    Регистрация международного юзера БЕЗ Telegram-бота.
    """
    permission_classes = [AllowAny]
 
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
 
        refresh = CustomRefreshToken.for_user_obj(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": ProfileSerializer(user).data,
        }, status=status.HTTP_201_CREATED)
 
 
class PasswordLoginView(views.APIView):
    """
    POST /login/password/
    Body: { email, password }
    """
    permission_classes = [AllowAny]
 
    def post(self, request):
        serializer = PasswordLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
 
        refresh = CustomRefreshToken.for_user_obj(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": ProfileSerializer(user).data,
        }, status=status.HTTP_200_OK)
 
 
class GoogleLoginView(views.APIView):
    """
    POST /login/google/
    Body: { id_token }   — id_token берётся на фронте из Google Identity Services
    (google.accounts.id.initialize / One Tap / кнопка "Sign in with Google").
 
    Требует: pip install google-auth
    Требует: settings.GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    (получить Client ID в Google Cloud Console → APIs & Services → Credentials
    → OAuth 2.0 Client IDs → Web application, добавить домен фронта в
    Authorized JavaScript origins).
    """
    permission_classes = [AllowAny]
 
    def post(self, request):
        token = request.data.get("id_token")
        if not token:
            return Response({"error": "Missing id_token"}, status=status.HTTP_400_BAD_REQUEST)
 
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests
 
        try:
            idinfo = google_id_token.verify_oauth2_token(
                token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )
        except ValueError:
            return Response({"error": "Invalid Google token"}, status=status.HTTP_401_UNAUTHORIZED)
 
        email = idinfo.get("email")
        if not email:
            return Response({"error": "Google account has no email"}, status=status.HTTP_400_BAD_REQUEST)
 
        fullname = idinfo.get("name", "")
        user, created = TGUser.objects.get_or_create(
            email=email,
            defaults={"fullname": fullname, "auth_provider": TGUser.AuthProvider.GOOGLE},
        )
 
        refresh = CustomRefreshToken.for_user_obj(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": ProfileSerializer(user).data,
            "created": created,
        }, status=status.HTTP_200_OK)
 