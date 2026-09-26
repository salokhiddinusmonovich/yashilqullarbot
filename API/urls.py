from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .api import (
    TelegramLoginView, LogoutView, ProfileView,
    TeamListView, ArticleViewSet,
    CommentCreateView, ArticleLikeView, CommentLikeView, CreateLoginTokenView, LoginTokenStatusView,
    RegisterView, PasswordLoginView, GoogleLoginView,  # НОВОЕ
)
from .api import EcoProjectViewSet, JoinProjectView


from .api import EcoProjectLikeView, EcoProjectCommentCreateView, EcoProjectCommentLikeView, RegionTeamView, PublicProfileView,PartnerListView, LeaderboardView, RegionalTeamOverviewView
from .api import CommentDeleteView, CommentEditView, EcoProjectCommentDeleteView, EcoProjectCommentEditView

from . import webapp

urlpatterns = [
    # ── Telegram Mini App (API/webapp.py) ──
    path('login/telegram-webapp/', webapp.WebAppLoginView.as_view(), name='webapp-login'),
    path('webapp/bootstrap/', webapp.BootstrapView.as_view(), name='webapp-bootstrap'),
    path('webapp/me/', webapp.MeView.as_view(), name='webapp-me'),
    path('webapp/me/photo/', webapp.MePhotoView.as_view(), name='webapp-me-photo'),
    path('webapp/me/password/', webapp.MePasswordView.as_view(), name='webapp-me-password'),
    path('webapp/events/', webapp.AllEventsView.as_view(), name='webapp-events'),
    path('webapp/events/<int:pk>/join/', webapp.JoinView.as_view(), name='webapp-join'),
    path('webapp/lang/', webapp.LangView.as_view(), name='webapp-lang'),
    path('webapp/qr.svg', webapp.QRView.as_view(), name='webapp-qr'),
    path('webapp/top/', webapp.LeaderboardView.as_view(), name='webapp-top'),
    path('webapp/staff/events/', webapp.StaffEventsView.as_view(), name='webapp-staff-events'),
    path('webapp/staff/checkin/', webapp.StaffCheckInView.as_view(), name='webapp-staff-checkin'),
    path('webapp/staff/search/', webapp.StaffSearchView.as_view(), name='webapp-staff-search'),

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
    path('comment/<int:pk>/edit/', CommentEditView.as_view(), name='comment-edit'),
    path('comment/<int:pk>/delete/', CommentDeleteView.as_view(), name='comment-delete'),
]

urlpatterns += [
    path('projects/', EcoProjectViewSet.as_view({'get': 'list'}), name='project-list'),
    path('projects/<int:pk>/', EcoProjectViewSet.as_view({'get': 'retrieve'}), name='project-detail'),
    path('projects/<int:pk>/join/', JoinProjectView.as_view(), name='project-join'),
]


urlpatterns += [
    path('projects/<int:pk>/like/', EcoProjectLikeView.as_view(), name='project-like'),
    path('projects/<int:pk>/comment/', EcoProjectCommentCreateView.as_view(), name='project-comment'),
    path('project-comment/<int:pk>/like/', EcoProjectCommentLikeView.as_view(), name='project-comment-like'),
    path('project-comment/<int:pk>/edit/', EcoProjectCommentEditView.as_view(), name='project-comment-edit'),
    path('project-comment/<int:pk>/delete/', EcoProjectCommentDeleteView.as_view(), name='project-comment-delete'),

    path('team/region/<str:region>/', RegionTeamView.as_view(), name='team-by-region'),
    path('users/<int:pk>/profile/', PublicProfileView.as_view(), name='public-profile'),

    path('partners/', PartnerListView.as_view(), name='partner-list'),
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
    path('team/regional-overview/', RegionalTeamOverviewView.as_view(), name='team-regional-overview'),
]