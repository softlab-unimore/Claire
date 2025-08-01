from django.urls import path
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

]
