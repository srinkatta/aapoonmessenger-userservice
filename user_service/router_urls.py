from user.api.routers import urlpatterns as user_urlpatterns
from user.api.admin.routers import urlpatterns as admin_urlpatterns

router_urlpatterns = []
router_admin_urlpatterns = []

router_urlpatterns += user_urlpatterns
router_admin_urlpatterns += admin_urlpatterns
