from django.shortcuts import render

from .models import Ingredient

# Create your views here.
def ingredients(request):
    ingredients = Ingredient.objects.order_by('type', 'name', 'variety')

    # Classify the ingredients according to type
    ingredients_per_type = {}
    for i in ingredients:
        display_name = ' '.join(filter(None, (i.name, i.variety)))
        try:
            ingredients_per_type[i.type].append(display_name)
        except KeyError:
            ingredients_per_type[i.type] = [display_name,]

    context = {'ingredients': ingredients_per_type,
               'header': 'Available ingredients'}
    return render(request, 'ingredients/list.html', context)
