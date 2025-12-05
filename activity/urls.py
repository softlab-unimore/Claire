from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
   path("", views.get_login, name="login"),
   path("logout", views.logout_request, name="logout"),
   path("register", views.register, name="register"),
   path("index", views.index, name="index"),
   path("activity", views.get_activity_page, name="activity"),
   path("members", views.get_members, name="members"),
   path("create_class", views.create_class, name="create_class"),
   path("new_activity", views.get_new_activity, name="new_activity"),
   path("get_chat", views.get_chat, name="chat"),
   path('download-messages/', views.download_total_messages, name='download_total_messages'),
   path('delete_class', views.delete_class, name='delete_class'),
   path('delete_activity', views.delete_activity, name='delete_activity'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
