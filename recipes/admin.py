from django.contrib import admin

# Register your models here.
from .models import Ingredient, Mixture, MixtureIngredients

admin.site.register(Ingredient)
