from django.http import HttpResponse, Http404
from django.db.models import Q
from django.shortcuts import render, get_object_or_404

from .forms import MixtureForm, IngredientFormset
from .models import Ingredient, Mixture

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


def new_mixture(request):
    if request.method == 'POST':
        form = MixtureForm(request.POST)
        formset = IngredientFormset(request.POST)
        if all([form.is_valid(), formset.is_valid()]):
            ingredient_quantity = {}
            for f in formset:
                ingredient = Ingredient.objects.get(id=f['ingredient'].value())
                ingredient_quantity[ingredient] = int(f['quantity'].value())
            mixture = Mixture.new(
                title=form['title'].value(), unit=form['unit'].value(),
                ingredient_quantity=ingredient_quantity
                )

            return HttpResponse(
                f'Congrats. You entered a valid mixture [{mixture.hash32}].'
                )
    else:
        form = MixtureForm()
        formset = IngredientFormset()

    return render(request, 'mixtures/new.html', {
        'formset': formset, 'form': form, 'header': 'Add new mixture'
        })

def new_recipe(request):
    if request.method == 'POST':
        return HttpResponse(
            f'Congrats. You entered a valid recipe'
            )
    else:
        recipe_form = MixtureForm(prefix='recipe')
        overall_formula = IngredientFormset(prefix='overall')

    return render(request, 'new.html', {
        'recipe': recipe_form, 'overall': overall_formula,
        'header': 'Add new recipe'
        })


def mixture_preview(request):
    # TODO: Hanlde POST requests
    key = request.GET['key']
    mixture = get_object_or_404(Mixture, Q(id=key) | Q(hash32=key))
    return HttpResponse(f'Mixture [{mixture.id}-{mixture.hash32}]')
