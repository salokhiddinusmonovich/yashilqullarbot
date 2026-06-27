from rest_framework import status, views, response, serializers
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, inline_serializer

from app_telegram.models import TGUser
from .serializers import UserSerializer

class RegisterView(views.APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="User Registration",
        description="Creates a new TGUser profile and standard User, then returns JWT tokens.",
        request=UserSerializer,
        responses={
            201: inline_serializer(
                name='RegisterResponse',
                fields={
                    'refresh': serializers.CharField(),
                    'access': serializers.CharField(),
                    'user': UserSerializer()
                }
            ),
            400: inline_serializer(
                name='RegisterValidationError',
                fields={'error': serializers.CharField(default="Validation errors")}
            )
        }
    )
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            tg_user = serializer.save() 
            
            # Request valid authentication token context from the shadow user model
            refresh = RefreshToken.for_user(tg_user.user)
            
            return response.Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": serializer.data
            }, status=status.HTTP_201_CREATED)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(views.APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="User Login",
        description="Log in using a Telegram ID. Returns access and refresh tokens.",
        request=inline_serializer(
            name="LoginRequest",
            fields={
                "tg_id": serializers.IntegerField(help_text="Telegram User ID")
            }
        ),
        responses={
            200: inline_serializer(
                name='LoginResponse',
                fields={
                    'refresh': serializers.CharField(),
                    'access': serializers.CharField(),
                }
            ),
            400: inline_serializer(
                name='LoginMissingIdError',
                fields={'error': serializers.CharField(default="tg_id field is required")}
            ),
            404: inline_serializer(
                name='LoginNotFoundError',
                fields={'error': serializers.CharField(default="User profile not found")}
            )
        }
    )
    def post(self, request):
        tg_id = request.data.get('tg_id')
        if not tg_id:
            return response.Response({"error": "tg_id field is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tg_profile = TGUser.objects.get(tg_id=tg_id)
            user = tg_profile.user 
            refresh = RefreshToken.for_user(user)
            
            return response.Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }, status=status.HTTP_200_OK)
        except TGUser.DoesNotExist:
            return response.Response({"error": "User profile not found"}, status=status.HTTP_404_NOT_FOUND)


class LogoutView(views.APIView):
    # Depending on your setup, you might want permission_classes = [IsAuthenticated] here
    @extend_schema(
        summary="User Logout",
        description="Blacklists the provided refresh token so it can no longer be used.",
        request=inline_serializer(
            name="LogoutRequest",
            fields={
                "refresh": serializers.CharField(help_text="The refresh token to blacklist")
            }
        ),
        responses={
            205: None,
            400: inline_serializer(
                name='LogoutError',
                fields={'error': serializers.CharField(default="Refresh token required or invalid")}
            )
        }
    )
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return response.Response(status=status.HTTP_205_RESET_CONTENT)
        except KeyError:
            return response.Response({"error": "Refresh token required"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return response.Response({"error": "Invalid or blacklisted token"}, status=status.HTTP_400_BAD_REQUEST)