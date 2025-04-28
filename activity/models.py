from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User

# Create your models here.
class UserProfile(models.Model):
   ROLE_CHOICES = [
      ('student', 'Student'),
      ('teacher', 'Teacher'),
   ]

   user = models.OneToOneField(User, on_delete=models.CASCADE)
   role = models.CharField(max_length=10, choices=ROLE_CHOICES)

   def __str__(self):
      return f"{self.user} ({self.role})"

class Group(models.Model):
   name = models.CharField(max_length=100)
   share_link = models.CharField(max_length=256, default="")
   userprofiles = models.ManyToManyField(UserProfile)

class Activity(models.Model):
   name = models.CharField(max_length=256)
   description = models.TextField()
   text = models.TextField()
   group_id = models.ForeignKey(Group, on_delete=models.CASCADE)

class UserActivity(models.Model):
   class Status(models.TextChoices):
      DONE = "D", _("Done")
      IN_PROGRESS = "IP", _("InProgress")

   chat_text = models.TextField()
   status = models.CharField(max_length=2, choices=Status, default=Status.IN_PROGRESS)
   activity_id = models.ForeignKey(Activity, on_delete=models.CASCADE)
   user_id = models.ForeignKey(User, on_delete=models.CASCADE)
