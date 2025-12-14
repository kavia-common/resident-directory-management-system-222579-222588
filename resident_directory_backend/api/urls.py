from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    health,
    ResidentViewSet,
    PhotoViewSet,
    register,
    AdminSummaryView,
)

router = DefaultRouter()
router.register(r'residents', ResidentViewSet, basename='resident')
router.register(r'photos', PhotoViewSet, basename='photo')

urlpatterns = [
    # Health
    path('health/', health, name='Health'),
    # Auth
    path('auth/register/', register, name='auth-register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # API Routers
    path('', include(router.urls)),
    # Admin summary
    path('admin/summary/', AdminSummaryView.as_view(), name='admin-summary'),
]
