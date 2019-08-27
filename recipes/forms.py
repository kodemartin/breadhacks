from django.forms import (ModelForm, CharField, modelformset_factory,
                          formset_factory)

from .models import Mixture, MixtureIngredients


class MixtureForm(ModelForm):

    class Meta:
        model = Mixture
        fields = ['title']


class MixtureIngredientForm(ModelForm):

    auto_id = False

    class Meta:
        model = MixtureIngredients
        fields = ['ingredient', 'quantity', 'unit']


IngredientFormset = formset_factory(
    MixtureIngredientForm, min_num=2, validate_min=True
    )
