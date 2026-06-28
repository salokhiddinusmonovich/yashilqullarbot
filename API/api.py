import hashlib
import hmac
from django.conf import settings
from rest_framework import status, views, generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from app_telegram.models import TGUser
from .serializers import ProfileSerializer


class TelegramLoginView(views.APIView):
    """
    POST /api/auth/login/
    Body: Telegram widget data { id, first_name, last_name?, username?, photo_url?, auth_date, hash }
    Returns: { access, refresh, user }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        data = dict(request.data)  # mutable copy

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
                # email and phone are required in your model — set blank defaults
                # user must complete profile later
                'email': '',
                'phone': '',
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