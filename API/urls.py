from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .api import TelegramLoginView, LogoutView, ProfileView

urlpatterns = [
    path('login/', TelegramLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', ProfileView.as_view(), name='profile'), 
]