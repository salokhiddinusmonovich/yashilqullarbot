"""
НОВЫЙ ФАЙЛ — API/authentication.py

Вынесено отдельно от api.py специально, чтобы разорвать циклический импорт:
DEFAULT_AUTHENTICATION_CLASSES резолвится ДО того, как rest_framework.views
успевает до конца загрузиться, а api.py импортирует `from rest_framework
import views` в самом верху — отсюда AttributeError на APIView.

Этот файл ничего из rest_framework.views/generics не трогает, поэтому
безопасен для загрузки на самом раннем этапе инициализации DRF.
"""
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from app_telegram.models import TGUser


class CustomRefreshToken(RefreshToken):
    """
    Универсальный токен для ЛЮБОГО способа входа (telegram / email / google).
    Кладём pk (uid) — это работает для всех, включая юзеров без tg_id.
    """
    @classmethod
    def for_tg_user(cls, tg_user: TGUser):
        # оставлено для обратной совместимости со старым кодом, который
        # его вызывает (TelegramLoginView и т.д.)
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