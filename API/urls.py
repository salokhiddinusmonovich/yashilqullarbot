from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .api import (
    TelegramLoginView, LogoutView, ProfileView,
    TeamListView, ArticleViewSet,
    CommentCreateView, ArticleLikeView, CommentLikeView, CreateLoginTokenView, LoginTokenStatusView,
    RegisterView, PasswordLoginView, GoogleLoginView,  # НОВОЕ
)
from .api import EcoProjectViewSet, JoinProjectView 

urlpatterns = [
    # ── Telegram bot login (без изменений) ──
    path('login/', TelegramLoginView.as_view(), name='login'),
    path('login/token/', CreateLoginTokenView.as_view(), name='create-login-token'),
    path('login/token/<str:token>/', LoginTokenStatusView.as_view(), name='login-token-status'),

    # ── НОВОЕ: регистрация и вход для международных юзеров ──
    path('register/', RegisterView.as_view(), name='register'),
    path('login/password/', PasswordLoginView.as_view(), name='login-password'),
    path('login/google/', GoogleLoginView.as_view(), name='login-google'),

    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', ProfileView.as_view(), name='profile'),
    path('team/', TeamListView.as_view(), name='team-list'),

    path('blog/', ArticleViewSet.as_view({'get': 'list'}), name='blog-list'),
    path('blog/<slug:slug>/', ArticleViewSet.as_view({'get': 'retrieve'}), name='blog-detail'),
    path('blog/<slug:slug>/comment/', CommentCreateView.as_view(), name='article-comment'),
    path('blog/<slug:slug>/like/', ArticleLikeView.as_view(), name='article-like'),
    path('comment/<int:pk>/like/', CommentLikeView.as_view(), name='comment-like'),
]

urlpatterns += [
    path('projects/', EcoProjectViewSet.as_view({'get': 'list'}), name='project-list'),
    path('projects/<int:pk>/', EcoProjectViewSet.as_view({'get': 'retrieve'}), name='project-detail'),
    path('projects/<int:pk>/join/', JoinProjectView.as_view(), name='project-join'),
]
 