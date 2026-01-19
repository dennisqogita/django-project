from django.db import models

# Create your models here.
class Member(models.Model):
    firstname = models.CharField(max_length=255)
    lastname = models.CharField(max_length=255)

class Subject(models.Model):
    title = models.CharField(max_length=255)
    subtitle = models.TextField(default="Subtitle")
