from django import forms

from .models import Ingredient, Mixture, MixtureIngredient, Recipe


class NestedMixtureForm(forms.ModelForm):
    """Nested mixtures are specified as part of a higher-level
    object, such as a recipe. The unit is thus dependent on the
    latter.
    """

    class Meta:
        model = Mixture
        fields = ['title']


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


class CustomFormSet(forms.BaseFormSet):

    def generate_cleaned_data(self, field_names=None):
        """Generate the cleaned data of the specified or all the
        field names for each form of the formset.

        :param field_names: An iterable of field names.
        :type: iterable or None
        """
        if self.is_valid():
            field_names = field_names or list(self.forms[0].fields.keys())
            for cleaned in self.cleaned_data:
                yield tuple(cleaned[name] for name in field_names)


IngredientFormSet = forms.formset_factory(
    MixtureIngredientForm, formset=CustomFormSet, min_num=2,
    validate_min=True
    )
