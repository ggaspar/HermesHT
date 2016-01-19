from django.db import models

# Create your models here.

class Hashtag(models.Model):
    name = models.CharField(max_length=50)
    startingTime = models.DateTimeField(auto_now_add=True)
    tweetsQuantity = models.IntegerField(default=0)

class Company(models.Model):
    name = models.CharField(max_length=50, unique=True)


