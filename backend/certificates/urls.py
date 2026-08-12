from rest_framework.routers import DefaultRouter
from .views import CertificateViewSet, VerifyCertificateView

router = DefaultRouter()
router.include_root_view = False
router.register('certificates', CertificateViewSet, basename='certificate')
router.register('verify', VerifyCertificateView, basename='verify')

urlpatterns = router.urls
