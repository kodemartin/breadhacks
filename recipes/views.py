from django.http import HttpResponse, Http404, JsonResponse
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.views import defaults, View

from .forms import NestedMixtureForm, MixtureForm, IngredientFormSet
from .models import Ingredient, Mixture, Recipe


__all__ = ['list_ingredients', 'add_new_mixture', 'RecipeFormView',
           'mixture_preview']


# Create your views here.
def list_ingredients(request):
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


def add_new_mixture(request):
    if request.method == 'POST':
        form = MixtureForm(request.POST)
        formset = IngredientFormSet(request.POST)
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
        prefix = request.GET.get('prefix')
        form = MixtureForm(prefix=prefix)
        formset = IngredientFormSet(prefix=prefix)

    return render(request, 'mixtures/new.html', {
        'formset': formset, 'form': form, 'header': 'Add new mixture'
        })


class RecipeFormView(View):
    template_name = 'new.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = None
        self.units = None
        self.ingredients = None
        self.partial = None

    def get(self, request, *args, **kwargs):
        recipe_form = MixtureForm(prefix='recipe')
        overall_formula = IngredientFormSet(prefix='overall')
        return render(request, self.template_name, {
            'recipe': recipe_form, 'overall': overall_formula,
            'header': 'Add new recipe'
            })

    def post(self, request, *args, **kwargs):
        self.validate_overall_data(request)

        self.validate_partial_mixtures(request)

        try:
            recipe = self.save_recipe()
        except IntegrityError:
            hash32 = Recipe.evaluate_hash_static(self.ingredients,
                                                 [m for _, m in self.partial])
            recipe = Recipe.objects.get(hash32=hash32)
            return HttpResponse(f'Found duplicate [{recipe.hash32}]')

        return HttpResponse(
            f'Awesome! Recipe [{recipe.hash32}] saved successfully'
            )

    def validate_overall_data(self, request):
        """Validate the title, unit of the recipe,
        and the ingredients of the overall formula.

        The method stores these data in respective
        attributes of the class. More specifically::

            * self.title: Is the title string.
            * self.units: The set of units.
            * self.ingredients: A list of tuples (Ingredient, <quantity>)
              representing the overall formula.

        :param HttpRequest request:
        :return: None or HttpResponseBadRequest
        """
        recipe_form = MixtureForm(request.POST, prefix='recipe')
        overall_formula = IngredientFormSet(request.POST, prefix='overall')
        for form in (recipe_form, overall_formula):
            if not form.is_valid():
                # TODO: More user-friendly handling
                return JsonResponse({'error': 'Invalid recipe',
                                     'message': form.errors.as_json()})
        self.title = recipe_form.cleaned_data['title']
        self.units = recipe_form.cleaned_data['unit']
        self.ingredients = list(overall_formula.generate_cleaned_data())

    def validate_partial_mixtures(self, request):
        """Retrieve all data from any partial mixture
        forms, validate them, and store them in a
        convenient form in `self.partial`.

        If successfull, `self.partial` is a list of
        ``(<title>, <ingredient-quantity>)`` 2-tuples,
        where ``<ingredient-quantity>`` is a sequence
        of ``(Ingredient, <quantity>)`` pairs.

        :param HttpRequest request:
        """
        i = 0
        partial = []
        while True:
            prefix = f'partial_{i}'
            meta = NestedMixtureForm(request.POST, prefix=prefix)
            if not meta.is_valid():
                break
            ingredients = IngredientFormSet(request.POST, prefix=prefix)
            if not ingredients.is_valid():
                # TODO: More user-friendly handling
                return JsonResponse({'error': 'Invalid partial mixture',
                                     'message': ingredients.errors.as_json()})

            i += 1
            title = meta.cleaned_data['title']
            ingredient_quantity = list(ingredients.generate_cleaned_data())
            partial.append((title, ingredient_quantity))
        self.partial = partial

    @transaction.atomic
    def save_recipe(self):
        """Create new `Recipe` instance and save to the
        database.

        :return: Recipe
        """
        if self.title and self.ingredients:
            return Recipe.new(self.title, self.ingredients,
                              self.units, self.partial)


def mixture_preview(request):
    # TODO: Hanlde POST requests
    key = request.GET['key']
    mixture = get_object_or_404(Mixture, Q(id=key) | Q(hash32=key))
    return HttpResponse(f'Mixture [{mixture.id}-{mixture.hash32}]')
