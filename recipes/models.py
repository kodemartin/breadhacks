import farmhash

from django.db import models, transaction
from custom_fields import UnsignedIntegerField
from custom_models import Hash32Model, update_properties_and_save

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
    UNITS = [
        ('[gr]', 'grams'),
        ('[lb]', 'pounds'),
        ('[oz]', 'ounces'),
        ('[kg]', 'kilograms'),
        ('[-]', 'ratio'),
        ('[%]', 'percentage'),
        ]
    title = models.CharField(max_length=128)
    ingredient = models.ManyToManyField(
        Ingredient,
        through='MixtureIngredient',
        )
    mixture = models.ManyToManyField('self')
    # TODO: Evaluate hash based on ingredients and quantities
    #       Explore pre_save, post_save signals functionality to this end
    hash32 = UnsignedIntegerField(default=None, unique=True, null=True)
    unit = models.CharField(max_length=32, choices=UNITS, default='[gr]')

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
        super().update_properties()
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

    def iter_mixture_ingredients(self):
        through = self.ingredient.through.objects
        for mi in through.filter(mixture=self):
            yield mi
        for m in self.mixture.all():
            for mi in through.filter(mixture=m):
                yield mi

    def iter_ingredient_quantities(self):
        """Iterate on couples of ingredients and
        respective quantities that make up this
        mixture.

        :return: An iterator on tuples ``(ingredient-instance, quantity)``.
        """
        for mi in self.iter_mixture_ingredients():
            yield (mi.ingredient, mi.quantity)

    def aggregate_ingredient_quantities(self):
        """Add together quantities of ingredients common
        to nested mixtures.

        :rtype: dict
        """
        aggregate_quantities = {}
        for ingredient, quantity in self.iter_ingredient_quantities():
            if ingredient in aggregate_quantities:
                aggregate_quantities[ingredient] += quantity
            else:
                aggregate_quantities[ingredient] = quantity
        return aggregate_quantities

    def cache_ingredient_quantities(self):
        """Update cache of db-stored ingredient
        quantities.
        """
        self._ingredient_quantities = list(
            self.aggregate_ingredient_quantities().items()
            )

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
    def new(cls, title='Overall', ingredient_quantity=None, unit='[gr]',
            mixtures=None):
        """Create a new mixture entry by specifying
        mixture ingredients.

        :param str title:
        :param ingredient_quantity: A map between `Ingredient` instances
            and quantities for this mixture.
        :type ingredient_quantity: dict or None
        :param str unit: The unit of the quantities specified.
        :param mixtures: Sequence of nested 'Mixture' instances.
        :type mixtures: iterable or None
        :rtype: Mixture
        """
        mixture = cls.get_duplicate(ingredient_quantity)
        if mixture:
            return mixture

        mixture = cls(title=title, unit=unit)
        mixture.save()
        if ingredient_quantity:
            for ingredient, quantity in ingredient_quantity.items():
                mixture.add(ingredient, quantity)
        if mixtures:
            mixture.add_mixtures(mixtures)
        mixture.update_properties()
        mixture.save()
        return mixture

    @update_properties_and_save
    def add(self, ingredient, quantity, *, atomic=False):
        """Add an ingredient-quantity pair to the mix.

        :param Ingredient ingredient:
        :param float quantity:
        :param bool atomic: If ``True`` update the dependent
            properties of the mixture.
        :rtype: None
        """
        mi = MixtureIngredient(mixture=self, ingredient=ingredient,
                               quantity=quantity)
        mi.save()

    @update_properties_and_save
    def add_mixture(self, mixtures, *, atomic=False):
        """Add a nested mixture.

        :param Mixture mixture: The ``Mixture`` instance
            to add.
        :param bool atomic: If ``True`` update the dependent
            properties of the mixture.
        """
        for m in mixtures:
            self.mixtures.add(m)

    @classmethod
    def get_by_key(cls, key):
        """Return an object by querying the database
        for the specified key. The method first
        checks the `id` and then the `hash32` field.

        :param key: The key to lookup
        :type key: int or str
        :rtype: Mixture
        :raises DoesNotExist: If not object is found
            in the database.
        """
        Q = models.Q
        return cls.objects.get(Q(id=key) | Q(hash32=key))


    @update_properties_and_save
    def add_mixtures(self, mixtures, *, atomic=False):
        """Add multiple nested mixtures.

        :param iterable mixtures: The sequence of ``Mixture`` instances
            to add.
        :param bool atomic: If ``True`` update the dependent
            properties of the mixture.
        """
        for m in mixtures:
            self.mixtures.add(m)

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

    @transaction.atomic
    def __add__(self, other):
        result = Mixture(title=self.title)
        result.save()
        iqself = dict(self.ingredient_quantities)
        iqother = dict(other.ingredient_quantities)
        for ingredient in set(iqself).union(iqother):
            quantity = iqself.get(ingredient, 0.) + iqother.get(ingredient, 0.)
            result.add(ingredient, quantity)
        result.update_properties()
        result.save()
        return result

    @transaction.atomic
    def __sub__(self, other):
        result = Mixture(title=self.title)
        result.save()
        iqother = dict(other.ingredient_quantities)
        for ingredient, quantity in self.ingredient_quantities:
            quantity = quantity - iqother.get(ingredient, 0.)
            result.add(ingredient, quantity)
        result.update_properties()
        result.save()
        return result


class MixtureIngredient(models.Model):
    mixture = models.ForeignKey(Mixture, on_delete=models.CASCADE, blank=True)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = UnsignedIntegerField()

    class Meta:
        db_table = 'mixture_ingredient'
        ordering = ['mixture_id', 'ingredient_id', 'quantity']


class Instruction(models.Model):
    title = models.CharField(max_length=128)
    text = models.TextField()

    class Meta:
        db_table = 'instruction'


class Recipe(Hash32Model):
    title = models.CharField(max_length=128)
    mixtures = models.ManyToManyField(
        Mixture,
        db_table='recipe_mixture'
        )
    instructions = models.ManyToManyField(
        Instruction,
        db_table='recipe_instruction'
        )
    # TODO: Evaluate hash based on mixtures and instructions
    hash32 = UnsignedIntegerField(default=None, unique=True, null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.overall = None
        self.final = None
        self.deductible = []

    class Meta:
        db_table = 'recipe'

    def evaluate_hash(self):
        if self.overall:
            h = self.overall.hash32
            return h

    @update_properties_and_save
    def add_overall_formula(self, ingredient_quantity, unit='[gr]',
                            mixtures=None, *, atomic=True):
        """Instantiate the overall formula of the recipe.

        :param dict ingredient_quantity:
        :param str unit:
        :param mixtures:
        :type mixtures: iterable(Mixture) or None
        """
        self.overall = Mixture.new('Overall formula', ingredient_quantity, unit,
                                   mixtures)
        self.mixtures.add(self.overall)

    @update_properties_and_save
    def add_deductible_mixture(self, title, ingredient_quantity, unit='[gr]',
                               mixtures=None, *, atomic=True):
        """Add a mixture that needs to be prepared independently, and can
        be deducted from the overall formula.

        :param str title: Title of the mixture.
        :param dict ingredient_quantity:
        :param str unit:
        :param mixtures:
        :type mixtures: iterable(Mixture) or None
        """
        to_add = Mixture.new(title, ingredient_quantity, unit)
        self.mixtures.add(to_add)
        self.deductible.append(to_add)

    def calculate_final(self):
        # TODO: Probably need to deep-copy here
        self.final = self.overall
        for mixture in self.deductible:
            self.final -= mixture
        self.final.title = 'Final'
        self.final.update_properties()
        self.final.save()


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
