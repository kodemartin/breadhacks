from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader

from .models import Ingredient

# Create your views here.
def ingredients(request):
    ingredients = Ingredient.objects.order_by('type')
    ingredients_per_type = {}
    for i in ingredients:
        try:
            ingredients_per_type[i.type].append(i.name)
        except KeyError:
            ingredients_per_type[i.type] = [i.name,]
    template = loader.get_template('ingredients/list.html')
    context = {'ingredients': ingredients_per_type,
               'header': 'Available ingredients'}
    return HttpResponse(template.render(context, request))
