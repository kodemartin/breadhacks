from django import forms

from .models import Ingredient, Mixture, MixtureIngredient


class MixtureForm(forms.ModelForm):

    class Meta:
        model = Mixture
        fields = ['title', 'unit']


class MixtureIngredientForm(forms.ModelForm):

    ingredient = forms.ModelChoiceField(Ingredient.objects,
                                        empty_label='Choose ingredient...')
    quantity = forms.IntegerField(min_value=1, initial=100)

    class Meta:
        model = MixtureIngredient
        fields = ['ingredient', 'quantity']


IngredientFormset = forms.formset_factory(
    MixtureIngredientForm, min_num=2, validate_min=True
    )
