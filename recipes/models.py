import farmhash

from django.db import models, transaction
from custom_fields import UnsignedIntegerField
from custom_models import Hash32Model

class Ingredient(Hash32Model):
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

    class Meta:
        db_table = 'ingredient'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        _type = '[' + self.type + ']' if self.type else ''
        return ' '.join(filter(None, [self.name, self.variety or '', _type]))

    def evaluate_hash(self):
        return farmhash.hash32(str(self))

    @classmethod
    def get(cls, name, variety=None, _type=None):
        """Return the instance with the given name,
        and optionally variety and type.
        
        :param str name: The name of the ingredient.
        :param variety: Filter any results to match
            the specified variety.
        :type variety: str or None
        :param _type: Filter any results to match
            the specified type.
        :type type: str or None
        """
        q = cls.objects.filter(name=name)
        if variety:
            q = q.filter(variety=variety)
        if type:
            q = q.filter(type=_type)
        return q.first()


class Mixture(Hash32Model):
    title = models.CharField(max_length=128)
    ingredients = models.ManyToManyField(
        Ingredient,
        through='MixtureIngredients',
        )
    # TODO: Evaluate hash based on ingredients and quantities
    #       Explore pre_save, post_save signals functionality to this end
    hash32 = UnsignedIntegerField(default=None, unique=True, null=True)

    class Meta:
        db_table = 'mixture'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ingredient_quantities = None
        self._ingredient_normquantities = None

    @property
    def ingredient_normquantities(self):
        """List of tuples ``(ingredient-instance, normquantity)``.

        :rtype: list
        """
        if self._ingredient_normquantities is None:
            self.normalize_ingredients()
        return self._ingredient_normquantities

    @property
    def ingredient_quantities(self):
        """List of tuples ``(ingredient-instance, quantity)``.

        :rtype: list
        """
        if self._ingredient_quantities is None:
            self.fetch_ingredient_quantities()
        return self._ingredient_quantities

    @ingredient_quantities.setter
    def ingredient_quantities(self, value):
        self._ingredient_quantities = value

    def update_properties(self):
        """Update hash and properties of the instance."""
        self.update_hash()
        self.fetch_ingredient_quantities()
        self.normalize_ingredients()

    @staticmethod
    def hash(ingredient_quantity):
        pass
        
    def evaluate_hash(self):
        """Evaluate the hash of the mixture.

        The evaluation takes into account the ingredients
        of the mixture and their normalized quantity.

        :rtype: int
        """
        hsource = ''
        for i, norm_quantity in self.iter_normalize_ingredients():
            hsource += str(i.hash32) + str(norm_quantity)
        return farmhash.hash32(hsource)

    def iter_ingredient_quantities(self):
        """Iterate on couples of ingredients and
        respective quantities that make up this
        mixture.

        :return: An iterator on tuples ``(ingredient-instance, quantity)``.
        """
        for mi in self.ingredients.through.objects.filter(mixture=self):
            yield (mi.ingredient, mi.quantity)

    def fetch_ingredient_quantities(self):
        """Update cache of db-stored ingredient
        quantities.
        """
        self._ingredient_quantities = list(self.iter_ingredient_quantities())

    def normalize_ingredients(self, quantities=None, reference='flour'):
        """Normalize ingredient quantities w.r.t the
        total quantity of the ingredients of the
        specified ``reference`` type. If no such ingredient
        is found, quantities are normalized w.r.t.
        the maximum quantity of the existing
        ingredients.

        This conveniently yields the baker's ratio
        if we normalize w.r.t. flour-ingredients.

        :param quantities: A map ``{<Ingredient>: quantity}``.
        :type quantities: dict or None
        :param str reference:
        :return: An iterator of tuples ``(ingredient_instance, normalized_value)``.
        """
        quantities = quantities or dict(self.iter_ingredient_quantities())
        total = sum(quantity for (i, quantity) in self.quantities if
                    i.type==ingredient_type)
        total = total or max(self.ingredient_quantities, key=lambda t: t[1])[1]
        for i, quantity in self.iter_ingredient_quantities():
            yield i, quantity/total

    def normalize_ingredients(self):
        self._ingredient_normquantities = list(self.iter_normalize_ingredients())

    @classmethod
    @transaction.atomic
    def new(cls, title='Overall', ingredient_quantity=None, unit='[gr]'):
        """Create a new mixture entry by specifying
        mixture ingredients.

        :param str title:
        :param ingredient_quantity: A map between ingredients
            and quantities for this mixture.
        :type ingredient_quantity: dict or None
        :rtype: Mixture
        """
        mixture = cls(title=title)
        mixture.save()
        if ingredient_quantity:
            for ingredient, quantity in ingredient_quantity.items():
                i = Ingredient.objects.get(name=ingredient)
                mi = MixtureIngredients(mixture=mixture, ingredient=i,
                                        quantity=quantity, unit=unit)
                mi.save()
        return mixture


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
