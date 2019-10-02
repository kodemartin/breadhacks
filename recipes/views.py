import logging
import json

from django.http import HttpResponse, Http404, JsonResponse
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.views import defaults, View

from .forms import (NestedMixtureForm, MixtureForm, IngredientFormSet,
                    LoadableMixtureForm)
from .models import Ingredient, Mixture, Recipe


__all__ = ['list_ingredients', 'add_new_mixture', 'RecipeFormView',
           'mixture_preview']


logging.basicConfig(level=logging.DEBUG)


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


def load_mixture(request):
    if request.method == 'GET':
        raise Http404("Only POST method supported.")
    elif request.method == 'POST':
        prefix = request.POST.get('prefix')
        initial = json.loads(request.POST['initial'])
        mixture_header = {key: initial[key] for key in ('title', 'unit')}
        ingredients = initial['ingredients']

    form = MixtureForm(prefix=prefix, initial=mixture_header)
    formset = IngredientFormSet(prefix=prefix, initial=ingredients)
    return render(request, 'mixtures/load.html', {
        'formset': formset, 'form': form
        })


class LoggedView(View):
    """Subclass of `View` with a class-level
    logger cached at first instantiation.
    """
    logger = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = self.logger or logging.getLogger(self.__class__.__name__)


class RecipePreview(LoggedView):

    template_name = 'preview.html'

    def get(self, request, *args, **kwargs):
        recipe = Recipe.get_by_key(request.GET['key'])

        return render(request, self.template_name, {
            'recipe': recipe, 'header': f'Recipe: {recipe.title}'
            })


class RecipeFormView(LoggedView):
    template_name = 'new.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = None
        self.unit = None
        self.ingredients = None
        self.partial = []
        self.loaded = []

    def get(self, request, *args, **kwargs):
        recipe_form = MixtureForm(prefix='recipe')
        overall_formula = IngredientFormSet(prefix='overall')
        loadable_mixture = LoadableMixtureForm(
            Mixture.objects.filter(recipes__isnull=False).distinct()
            )
        return render(request, self.template_name, {
            'recipe': recipe_form, 'overall': overall_formula,
            'header': 'Add new recipe',
            'loadable_mixture': loadable_mixture
            })

    def post(self, request, *args, **kwargs):
        self.logger.debug(f"==> Posted {request.POST}")
        self.validate_overall_data(request)
        self.logger.debug("==> Validated overall_data")

        response = (self.process_partial_mixtures(request) or
                    self.process_loaded_mixtures(request))
        if response is not None:
            return response

        try:
            recipe = self.save_recipe()
        except IntegrityError:
            hash32 = Recipe.evaluate_hash_static(self.ingredients,
                                                 [m for _, m in self.partial]+
                                                 self.loaded)
            recipe = Recipe.objects.get(hash32=hash32)

        return JsonResponse({str(i): q for i, q in recipe.final})

    def validate_overall_data(self, request):
        """Validate the title, unit of the recipe,
        and the ingredients of the overall formula.

        The method stores these data in respective
        attributes of the class. More specifically::

            * self.title: Is the title string.
            * self.unit: The set of units.
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
                                     'message': form.errors})
        self.title = recipe_form.cleaned_data['title']
        self.unit = recipe_form.cleaned_data['unit']
        self.ingredients = list(overall_formula.generate_cleaned_data())

    def extract_mixtures(self, request, prefix):
        """Traverse the transmitted forms in the request, to
        retrieve information about forms with the specified
        prefix.

        The method iterates over the header info represented by
        a `NestedMixtureForm` instance and the ingredient-quantity
        pairs represented by a `IngredientFormset` instance.

        :param HttpRequest request:
        :param str prefix: The prefix of the forms to be extracted.
        :return: A generator of ``(NestedMixtureForm, IngredientFormSet)``
            2-tuples.
        """
        i = 0
        while True:
            current_prefix = f'{prefix}_{i}'
            meta = NestedMixtureForm(request.POST, prefix=current_prefix)
            if not meta.is_valid():
                break
            ingredients = IngredientFormSet(request.POST, prefix=current_prefix)
            yield meta, ingredients
            i += 1

    @staticmethod
    def validate_mixture(header, ingredients):
        """Check that the partial mixture represented
        by the specified ingredients is valid.

        :param NestedMixtureForm header:
        :param IngredientFormSet ingredients:
        :rtype: None or JsonResponse
        """
        if not ingredients.is_valid():
            # TODO: More user-friendly handling
            return JsonResponse({'error': 'Invalid partial mixture',
                                 'message': ingredients.errors})

    def classify_loaded_mixture(self, header, ingredients):
        """Check if the loaded mixture has been changed. On this event,
        check if the mixture is a duplicate and if not classify
        along with any new mixtures in `self.partial`. Otherwise,
        the mixture is classified in `self.loaded`.

        New mixtures with changed titles are not accepted
        so that to avoid storing different partial mixtures by
        the same name.

        :param NestedMixtureForm header:
        :param IngredientFormSet ingredients:
        :rtype: None
        :raises Http404: If the mixture is a duplicate
            and has a modified title.
        """
        title, ingredient_quantity = self.analyze_mixture(header, ingredients)
        duplicate = Mixture.get_duplicate(ingredient_quantity)
        if duplicate is None:
            if Mixture.objects.filter(title__iexact=title):
                raise Http404((f'Please provide a different title '
                               f'for edit mixture "{title}"'))
            return self.partial.append((title, ingredient_quantity))
        return self.loaded.append(duplicate)

    @staticmethod
    def analyze_mixture(header, ingredients):
        """Analyze the mixture represented by the forms
        passed as arguments to its title and ingredient-quantity
        pairs.

        :param NestedMixtureForm header:
        :param IngredientFormSet ingredients:
        :rtype: tuple
        :return: A ``(<title>, <ingredient-quantity>)``
            2-tuples, where ``<ingredient-quantity>`` is a
            sequence of ``(Ingredient, <quantity>)`` 2-tuples.
        """
        title = header.cleaned_data['title']
        ingredient_quantity = list(ingredients.generate_cleaned_data())
        return title, ingredient_quantity

    def process_partial_mixtures(self, request, prefix='partial'):
        """Retrieve all data from any partial mixture
        forms, validate them, and store them in a
        convenient form in `self.partial`.

        If successfull, `self.partial` is assigned a list of
        ``(<title>, <ingredient-quantity>)`` 2-tuples,
        where ``<ingredient-quantity>`` is a sequence
        of ``(Ingredient, <quantity>)`` pairs.

        :param HttpRequest request:
        :param str prefix: The prefix that identifies partial forms.
        """
        self.logger.debug("==> Processing partial mixtures..")
        for header, ingredients in self.extract_mixtures(request, prefix):
            response = self.validate_mixture(header, ingredients)
            if response is not None:
                return response
            self.partial.append(self.analyze_mixture(header, ingredients))

    def process_loaded_mixtures(self, request, prefix='loadable'):
        """Retrieve all data from any loaded mixture
        forms, validate them, and store them in a
        convenient form in `self.loaded`.

        Validation involves checking if the loaded mixture
        has been changed. In that case, the quantities
        have been edited and the mixture might be a new
        mixture.

        If successfull, `self.loaded` is assigned a list of
        ``(<title>, <ingredient-quantity>)`` 2-tuples,
        where ``<ingredient-quantity>`` is a sequence
        of ``(Ingredient, <quantity>)`` pairs.

        :param HttpRequest request:
        :param str prefix: The prefix that identifies partial forms.
        :rtype: None or `JsonResponse`
        """
        self.logger.debug("==> Processing loaded mixtures")
        for header, ingredients in self.extract_mixtures(request, prefix):
            response = self.validate_mixture(header, ingredients)
            if response is not None:
                return response
            self.classify_loaded_mixture(header, ingredients)

    @transaction.atomic
    def save_recipe(self):
        """Create new `Recipe` instance and save to the
        database.

        :return: Recipe or None
        """
        if self.title and self.ingredients:
            return Recipe.new(self.title, self.ingredients, self.unit,
                              self.partial, loaded=self.loaded)


def mixture_preview(request):
    # TODO: Hanlde POST requests
    key = request.GET['key']
    mixture = get_object_or_404(Mixture, Q(id=key) | Q(hash32=key))
    return HttpResponse(f'Mixture [{mixture.id}-{mixture.hash32}]')

def list_partial_mixtures(request):
    term = request.GET.get('q', '')
    results = [m.title for m in Mixture.objects.filter(title__startswith=term)]
    return JsonResponse(results, safe=False)


def list_mixture_ingredients(request):
    m_id = request.GET['id']
    mixture = Mixture.objects.get(id=m_id)
    response = {
        'title': mixture.title,
        'unit': mixture.unit,
        'ingredients': [{'ingredient': i.id, 'quantity': q} for i, q in mixture]
        }
    return JsonResponse(response)
