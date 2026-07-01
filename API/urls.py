from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .api import (
    TelegramLoginView, LogoutView, ProfileView, 
    TeamListView, ArticleViewSet, # <-- Импортируем именно ArticleViewSet
    CommentCreateView, ArticleLikeView, CommentLikeView
)

urlpatterns = [
    path('login/', TelegramLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', ProfileView.as_view(), name='profile'),
    path('team/', TeamListView.as_view(), name='team-list'),
    
    # Пути для блога (расписываем действия ViewSet)
    path('blog/', ArticleViewSet.as_view({'get': 'list'}), name='blog-list'),
    path('blog/<slug:slug>/', ArticleViewSet.as_view({'get': 'retrieve'}), name='blog-detail'),
    
    # Наши новые пути для комментов и лайков
    path('blog/<slug:slug>/comment/', CommentCreateView.as_view(), name='article-comment'),
    path('blog/<slug:slug>/like/', ArticleLikeView.as_view(), name='article-like'),
    path('comment/<int:pk>/like/', CommentLikeView.as_view(), name='comment-like'),
]