from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenBlacklistView, TokenRefreshView

from .auth_views import AuthConfigView, GoogleLoginView, LocalLoginView
from .views import DivisionViewSet, MeView, RoleViewSet, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("roles", RoleViewSet, basename="role")
router.register("divisions", DivisionViewSet, basename="division")
router.register("me", MeView, basename="me")

urlpatterns = [
    path("config/", AuthConfigView.as_view(), name="auth-config"),
    path("login/google/", GoogleLoginView.as_view(), name="auth-login-google"),
    path("login/local/", LocalLoginView.as_view(), name="auth-login-local"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("logout/", TokenBlacklistView.as_view(), name="auth-logout"),
    *router.urls,
]
