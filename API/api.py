import hashlib
import hmac
from django.conf import settings
from rest_framework import status, views, response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from app_telegram.models import TGUser
from serializers import ProfileSerializer
from rest_framework import generics

class TelegramLoginView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        hash_val = data.pop('hash', None)
        tg_id = data.get('id')

        # Проверка безопасности (хеш от Telegram)
        data_check_string = "\n".join([f"{k}={v}" for k, v in sorted(data.items())])
        secret_key = hashlib.sha256(settings.TELEGRAM_BOT_TOKEN.encode()).digest()
        expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if hash_val != expected_hash:
            return response.Response({"error": "Invalid hash"}, status=status.HTTP_401_UNAUTHORIZED)

        # Авторизация или регистрация
        tg_profile, _ = TGUser.objects.get_or_create(
            tg_id=tg_id,
            defaults={'fullname': data.get('first_name', 'Unknown')}
        )
        
        refresh = RefreshToken.for_user(tg_profile.user)
        return response.Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_200_OK)

class LogoutView(views.APIView):
    def post(self, request):
        try:
            token = RefreshToken(request.data["refresh"])
            token.blacklist()
            return response.Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return response.Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
        


# --- ПРОФИЛЬ (GET и PATCH) ---
class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated] # Требуется JWT токен!

    def get_object(self):
        # Автоматически находим профиль того пользователя, чей токен сейчас используется
        return TGUser.objects.get(user=self.request.user)
    # ... остальной код