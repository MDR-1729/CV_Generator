from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.accept, name='accept'),
    path('resume/', views.resume, name='resume'),
    path('resume/<int:profile_id>/', views.resume, name='resume_detail'),
    path('resume/<int:profile_id>/download/pdf/', views.download_resume_pdf, name='resume_download_pdf'),
    path('resume/<int:profile_id>/download/docx/', views.download_resume_docx, name='resume_download_docx'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)