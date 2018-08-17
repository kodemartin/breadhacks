import farmhash

from django.db import models
from customfields import UnsignedIntegerField

class Ingredient(models.Model):
    TYPES = (
        ('flour', 'flour'),
        ('water', 'water'),
        ('liquid', 'liquid'),
        ('fat', 'fat'),
        ('seed', 'seed'),
        ('other', 'other'),
        ('meal', 'meal'),
        ('malt', 'malt')
        )
    name = models.CharField(max_length=60)
    variety = models.CharField(max_length=60, null=True, default=None)
    type = models.CharField(max_length=60, choices=TYPES)
    hash32 = UnsignedIntegerField(null=True)

    class Meta:
        db_table = 'ingredient'

    def save(self, *args, **kwargs):
        self.hash32 = farmhash.hash32(self)
        super().save(*args, **kwargs)

    def __str__(self):
        _type = '[' + self.type + ']' if self.type else ''
        return ' '.join(filter(None, [self.name, self.variety or '', _type]))


class Mixture(models.Model):
    label = models.CharField(max_length=128)
    ingredients = models.ManyToManyField(
            Ingredient,
            through='MixtureIngredients',
            )
    # TODO: Evaluate hash based on ingredients and quantities
    hash32 = UnsignedIntegerField(default=None, unique=True, null=True)

    class Meta:
        db_table = 'mixture'


class MixtureIngredients(models.Model):
    UNITS = [
        ('[gr]', 'grams'),
        ('[lb]', 'pounds'),
        ('[oz]', 'ounces'),
        ('[kg]', 'kilograms'),
        ('[-]', 'ratio'),
        ('[%]', 'percentage'),
        ]
    mixture = models.ForeignKey(Mixture, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = UnsignedIntegerField()
    unit = models.CharField(max_length=32, choices=UNITS, default='[gr]')

    class Meta:
        db_table = 'mixture_ingredients'
        ordering = ['mixture_id', 'ingredient_id', 'quantity']

    #TODO: Populate ingredient_quantities and derived properties
    #      in the ``mixture`` instance
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ingredient_quantities = None
        self._ingredient_normquantities = None

    def update_mixture_hash(self):
        hsource = ''
        self.fetch_ingredient_quantities()
        self.normalize_ingredients()
        for i, norm_quantity in self.ingredient_normquantities:
            hsource += str(i.hash32) + str(norm_quantity)
        self.mixture.hash32 = farmhash.hash32(hsource)

    def iter_ingredient_quantities(self):
        """Iterate on couples of ingredients and
        respective quantities that make up this
        mixture.

        :return: An iterator on tuples ``(ingredient-instance, quantity)``.
        """
        for mi in self.__class__.objects.filter(mixture=self.mixture):
            yield (mi.ingredient, mi.quantity)

    def fetch_ingredient_quantities(self):
        """Update cache of db-stored ingredient
        quantities.
        """
        self._ingredient_quantities = list(self.iter_ingredient_quantities())

    @property
    def ingredient_quantities(self):
        """List of tuples ``(ingredient-instance, quantity)``.

        :rtype: list
        """
        if self._ingredient_quantities is None:
            self.fetch_ingredient_quantities()
        return self._ingredient_quantities

    def iter_normalize_ingredients(self, ingredient_type='flour'):
        """Normalize ingredient quantities w.r.t the
        total quantity of the ingredients of the
        specified ``ingredient_type``. If no such ingredient
        is found, quantities are normalized w.r.t.
        the maximum quantity of the existing
        ingredients.

        This conveniently yields the baker's ratio
        if we normalize w.r.t. flour-ingredients.

        :param str ingredient_type:
        :return: An iterator of tuples ``(ingredient_instance, normalized_value)``.
        """
        total = sum(quantity for (i, quantity) in self.ingredient_quantities if
                    i.type==ingredient_type)
        total = total or max(self.ingredient_quantities, key=lambda t: t[1])[1]
        for i, quantity in self.ingredient_quantities:
            yield i, quantity/total

    def normalize_ingredients(self):
        self._ingredient_normquantities = list(self.iter_normalize_ingredients())

    @property
    def ingredient_normquantities(self):
        """List of tuples ``(ingredient-instance, normquantity)``.

        :rtype: list
        """
        if self._ingredient_normquantities is None:
            self.normalize_ingredients()
        return self._ingredient_normquantities

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.update_mixture_hash()
        self.mixture.save()

class Instruction(models.Model):
    label = models.CharField(max_length=128)
    text = models.TextField()

    class Meta:
        db_table = 'instruction'


class Recipe(models.Model):
    title = models.CharField(max_length=128)
    mixture = models.ManyToManyField(
            Mixture,
            db_table='recipe_mixtures'
            )
    instruction = models.ManyToManyField(
            Instruction,
            db_table='recipe_instructions'
            )
    # TODO: Evaluate hash based on mixtures and instructions
    hash32 = UnsignedIntegerField(default=None, unique=True, null=True)

    class Meta:
        db_table = 'recipe'


class Implementation(models.Model):

    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    mixture = models.ForeignKey(Mixture, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'implementation'

class Note(models.Model):
    label = models.CharField(max_length=64)
    text = models.TextField

    class Meta:
        db_table = 'note'

class ImplementationNotes(models.Model):

    implementation = models.ForeignKey(Implementation, on_delete=models.CASCADE)
    notes = models.ForeignKey(Note, on_delete=models.CASCADE)

    class Meta:
        db_table = 'implementation_notes'
