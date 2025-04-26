from django.db import models

# Create your models here.
class User(models.Model):
   name = models.CharField(max_length=100)
   surname = models.CharField(max_length=100)
   email = models.EmailField(max_length=256)

class Group(models.Model):
   name = models.CharField(max_length=100)
   users = models.ManyToManyField(User)

class Activity(models.Model):
   name = models.CharField(max_length=100)
   description = models.TextField()
   text = models.TextField()
   group_id = models.ForeignKey(Group, on_delete=models.CASCADE)

class UserActivity(models.Model):
   class Status(models.TextChoices):
      DONE = "D", _("Done")
      IN_PROGRESS = "IP", _("InProgress")

   chat_text = models.TextField()
   status = models.CharField(max_length=2, choices=Status, default=Status.IN_PROGRESS)
   activity_id = ForeignKey(Activity, on_delete=models.CASCADE)
   user_id = ForeignKey(User, on_delete=models.CASCADE)
