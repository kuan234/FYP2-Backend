from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('get/', views.getData),
    path('add/', views.addEmployee),
    path('login/', views.login_view),
    path('detect_face/', views.detect_face),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# urlpatterns = [
#     path('search/', views.searchProducts),
#     path('upload/', views.uploadImage),
# ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
 