from django.contrib import admin

from django.contrib import admin
from models import Hashtag, Company


class HashtagAdmin(admin.ModelAdmin):
    list_display = ('name','startingTime', 'tweetsQuantity')

admin.site.register(Hashtag, HashtagAdmin)


class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name',)

admin.site.register(Company, CompanyAdmin)

