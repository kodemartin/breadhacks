import farmhash

from django.db import models, transaction
from custom_fields import UnsignedIntegerField
from custom_models import Hash32Model

import pprint


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
        if _type:
            q = q.filter(type=_type)
        return q.first()

    def __hash__(self):
        return self.hash32


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
            self.cache_normalized()
        return self._ingredient_normquantities

    def cache_normalized(self):
        """Cache the normalized ingredient-quantity pairs."""
        self.cache_ingredient_quantities()
        self._ingredient_normquantities = self.normalize_ingredients(
            dict(self.ingredient_quantities)
            )

    @property
    def ingredient_quantities(self):
        """List of tuples ``(ingredient-instance, quantity)``.

        :rtype: list
        """
        if self._ingredient_quantities is None:
            self.cache_ingredient_quantities()
        return self._ingredient_quantities

    @ingredient_quantities.setter
    def ingredient_quantities(self, value):
        self._ingredient_quantities = value

    def update_properties(self):
        """Update hash and properties of the instance."""
        self.update_hash()
        self.cache_normalized()

    @classmethod
    def evaluate_hash_static(cls, ingredient_quantities):
        """Evaluate the hash of a mixture represented by
        a map between ``Ingredient`` instances and respective
        quantities.

        :param dict ingredient_quantities:
        :rtype: int
        """
        quantities = cls.normalize_ingredients(ingredient_quantities)
        hsource = ''
        for i, norm_quantity in quantities:
            hsource += str(i.hash32) + str(norm_quantity)
        return farmhash.hash32(hsource)

    def evaluate_hash(self, ingredient_quantities=None):
        """Evaluate the hash of the mixture. If ``ingredient-quantities``
        are given, evaluate the hash of that configuration.

        The evaluation takes into account the ingredients
        and their normalized quantity.

        :param ingredient_quantities: A ``{Ingredient: <float: quantity>}`` map.
        :rtype: int
        """
        if ingredient_quantities is None:
            self.cache_normalized()
            quantities = self.ingredient_normquantities
        else:
            quantities = self.normalize_ingredients(ingredient_quantities)

        return self.evaluate_hash_static(dict(quantities))

    def iter_ingredient_quantities(self):
        """Iterate on couples of ingredients and
        respective quantities that make up this
        mixture.

        :return: An iterator on tuples ``(ingredient-instance, quantity)``.
        """
        for mi in self.ingredients.through.objects.filter(mixture=self):
            yield (mi.ingredient, mi.quantity)

    def cache_ingredient_quantities(self):
        """Update cache of db-stored ingredient
        quantities.
        """
        self._ingredient_quantities = list(self.iter_ingredient_quantities())

    @staticmethod
    def normalize_ingredients(quantities, reference='flour'):
        """Normalize ingredient quantities w.r.t the
        total quantity of the ingredients of the
        specified ``reference`` type. If no such ingredient
        is found, quantities are normalized w.r.t.
        the maximum quantity of the existing
        ingredients.

        This conveniently yields the baker's ratio
        if we normalize w.r.t. flour-ingredients.

        :param dict quantities: A map ``{<Ingredient>: quantity}``.
        :type quantities: dict or None
        :param str reference:
        :return: An iterator of tuples ``(ingredient_instance, normalized_value)``.
        """
        total = sum((quantity for (i, quantity) in quantities.items() if
                    i.type==reference))
        total = total or max(quantities.values())
        for i, quantity in quantities.items():
            yield i, quantity/total

    @classmethod
    @transaction.atomic
    def new(cls, title='Overall', ingredient_quantity=None, unit='[gr]'):
        """Create a new mixture entry by specifying
        mixture ingredients.

        :param str title:
        :param ingredient_quantity: A map between ingredient properties
            ``(name, [variety, type])`` and quantities for this mixture.
        :type ingredient_quantity: dict or None
        :rtype: Mixture
        """
        instance_quantity = cls.construct_instance_quantity(ingredient_quantity)
        mixture = cls.get_duplicate(instance_quantity)
        if mixture:
            return mixture

        mixture = cls(title=title)
        mixture.save()
        if ingredient_quantity:
            for instance, quantity in instance_quantity.items():
                mixture.add(instance, quantity, unit)
        mixture.update_properties()
        mixture.save()
        return mixture

    def add(self, ingredient, quantity, unit='[gr]', atomic=False):
        """Add an ingredient-quantity pair to the mix.

        :param Ingredient ingredient:
        :param float quantity:
        :param str unit:
        :param bool atomic: If ``True`` update the dependent
            properties of the mixture.
        :rtype: None
        """
        mi = MixtureIngredients(mixture=self, ingredient=ingredient,
                                quantity=quantity, unit=unit)
        mi.save()
        if atomic:
            self.update_properties()
            self.save()

    @staticmethod
    def construct_instance_quantity(ingredient_quantity):
        """Given a map between data representing an ingredient
        and a quantity return the map between the respective
        ``Ingredient`` instances and the corresponding quantities.

        :param dict ingredient_quantity: A map between ingredient properties
            ``(name, [variety, type])`` and quantities for this mixture.
        :rtype: {Ingredient: float}
        :raises ValueError: If an ingredient description is not recognized.
        """
        instance_quantity = {}
        for ingredient, quantity in ingredient_quantity.items():
            instance = Ingredient.get(*ingredient)
            if instance is None:
                raise ValueError(f'Unknown ingredient {ingredient}')
            instance_quantity[instance] = quantity
        return instance_quantity

    @classmethod
    def get_duplicate(cls, ingredient_quantity):
        """Given a map between ingredients and quantities
        check if the database contains a duplicate.

        :param dict ingredient_quantity: A map between ``Ingredient``
            instances and quantities for this mixture.
        :rtype: Mixture or None
        """
        return cls.objects.filter(
            hash32=cls.evaluate_hash_static(ingredient_quantity)
            ).first()

    def __str__(self):
        return pprint.pformat({f'{i}': q for i, q in self.ingredient_quantities })


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
