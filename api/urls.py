from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('get/', views.getData),
    path('add/', views.add_employee),
    path('login/', views.login_view),
    path('verify_face/', views.verify_face),
    path('log/', views.get_attendance_by_date),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # path('detect_face/', views.detect_face),
# urlpatterns = [
#     path('search/', views.searchProducts),
#     path('upload/', views.uploadImage),
# ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
 