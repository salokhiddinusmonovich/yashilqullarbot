from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .api import (
    TelegramLoginView, LogoutView, ProfileView, 
    TeamListView, ArticleListView, ArticleDetailView, # У тебя там была опечатка "a", я поправил
    CommentCreateView, ArticleLikeView, CommentLikeView # <-- Импортируем новые вьюхи
)

urlpatterns = [
    path('login/', TelegramLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', ProfileView.as_view(), name='profile'),
    path('team/', TeamListView.as_view(), name='team-list'),
    
    # Пути для блога
    path('blog/', ArticleListView.as_view(), name='blog-list'),
    path('blog/<slug:slug>/', ArticleDetailView.as_view(), name='blog-detail'),
    
    # --- НОВЫЕ ПУТИ ДЛЯ КОММЕНТОВ И ЛАЙКОВ ---
    path('blog/<slug:slug>/comment/', CommentCreateView.as_view(), name='article-comment'),
    path('blog/<slug:slug>/like/', ArticleLikeView.as_view(), name='article-like'),
    path('comment/<int:pk>/like/', CommentLikeView.as_view(), name='comment-like'),
]