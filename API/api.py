from rest_framework import status, views, response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from app_telegram.models import TGUser
from .serializers import UserSerializer

class RegisterView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return response.Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": serializer.data
            }, status=status.HTTP_201_CREATED)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        tg_id = request.data.get('tg_id')
        try:
            # 1. Find your custom profile
            tg_profile = TGUser.objects.get(tg_id=tg_id)
            
            # 2. Get the linked Django User
            user = tg_profile.user 
            
            # 3. Now SimpleJWT works perfectly
            refresh = RefreshToken.for_user(user)
            
            return response.Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            })
        except TGUser.DoesNotExist:
            return response.Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

class LogoutView(views.APIView):
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return response.Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return response.Response(status=status.HTTP_400_BAD_REQUEST)