from user.api.routers import urlpatterns as user_urlpatterns
from certificates.api.routers import urlpatterns as certificate_urlpatterns

router_urlpatterns = []
router_urlpatterns += user_urlpatterns
router_urlpatterns += certificate_urlpatterns
