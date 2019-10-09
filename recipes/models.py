import farmhash

from collections import defaultdict
from django.db import models, transaction, IntegrityError
from django.utils.functional import cached_property
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


class MixtureRecursive(models.Model):
    primary = models.ForeignKey('Mixture', models.CASCADE)
    nested = models.ForeignKey('Mixture', models.CASCADE, related_name='primary')
    factor = models.FloatField(default=1.)

    class Meta:
        db_table = 'mixture_nest'


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
    mixture = models.ManyToManyField('self', symmetrical=False,
                                     related_name='primary_mixture',
                                     through=MixtureRecursive)
    # TODO: Evaluate hash based on ingredients and quantities
    #       Explore pre_save, post_save signals functionality to this end
    unit = models.CharField(max_length=32, choices=UNITS, default='[gr]')

    class Meta:
        db_table = 'mixture'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ingredient_quantities = None
        self._ingredient_normquantities = None
        self._total_yield = None

    def __iter__(self):
        return self.iter_ingredient_quantities()

    def multiply(self, factor):
        """Multiply the quantities of the ingredients
        by a given factor.

        :param float factor: The multiplication factor.
        :rtype: Mixture
        """
        self.ingredient_quantities = [(i, factor*q) for i, q in self]
        self.total_yield *= factor
        return self

    @property
    def total_yield(self):
        """The sum of the ingredient quantities

        :rtype: float
        """
        if self._total_yield is None:
            self._total_yield = sum([q for _, q in self]) or None
        return self._total_yield

    @total_yield.setter
    def total_yield(self, value):
        """
        :param float value:
        """
        self._total_yield = value

    def evaluate_factor(self, *ingredient_quantity):
        """Evaluate the factor of an
        analogous set of ingredient-quantities with respect
        to this mixture.

        :param list ingredient_quantity: A sequence of
            iterables with ``(Ingredient, <quantity>)``
            2-tuples.
        :rtype: float
        """
        current = 0.
        for iq in ingredient_quantity:
            current += sum([q for _, q in iq])
        return current / self.total_yield

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
        self._ingredient_normquantities = list(
            self.normalize(self.ingredient_quantities)
            )

    def cache_ingredient_quantities(self):
        """Update cache of db-stored ingredient
        quantities.
        """
        self._ingredient_quantities = self.aggregate_ingredient_quantities(self)
        self._total_yield = None

    @staticmethod
    def sort(ingredient_quantity):
        """Wrap the sorting rule for the ingredient-quantity pairs.

        :param iterable ingredient_quantity: The iterable with the
            ingredient-quantity pairs.
        :rtype: list
        :return: The sorted sequence of the ingredient-quantity pairs.
        """
        key = lambda pair: pair[0].hash32
        return sorted(ingredient_quantity, key=key)

    @staticmethod
    def aggregate_ingredient_quantities(*ingredient_quantities):
        """Add together quantities of ingredients common
        to various mixtures, represented by iterables
        of ``(Ingredient, quantity)`` 2-tuples.

        :param ingredient_quantities: Sequence of iterables
            of ``(Ingredient, quantity)`` 2-tuples.
        :rtype: list
        :return: A sequence of the aggregated ``(Ingredient, quantity)``
            2-tuples.
        """
        aggregate_quantities = defaultdict(int)
        for ingredient_quantity in ingredient_quantities:
            for ingredient, quantity in ingredient_quantity:
                aggregate_quantities[ingredient] += quantity
        return list(aggregate_quantities.items())

    def update_properties(self):
        """Update hash and properties of the instance."""
        super().update_properties()
        self.cache_normalized()

    def evaluate_hash(self):
        """Evaluate the hash of the mixture. If ``ingredient-quantities``
        are given, evaluate the hash of that configuration.

        The evaluation takes into account the ingredients
        and their normalized quantity.

        :param ingredient_quantities: A sequence of tuples
            ``(Ingredient: <float: quantity>)``.
        :rtype: int
        """
        self.cache_ingredient_quantities()

        return self.evaluate_hash_static(self.ingredient_quantities)

    @classmethod
    def evaluate_hash_static(cls, ingredient_quantity):
        """Evaluate the hash of a mixture represented by
        a map between ``Ingredient`` instances and respective
        quantities.

        Account also for any nested mixtures given.

        :param list ingredient_quantity: A list of tuples
            ``(Ingrediend, quantity)``.
        :rtype: int
        """
        quantities = cls.normalize(cls.sort(ingredient_quantity))
        hsource = ''
        for i, norm_quantity in quantities:
            hsource += str(i.hash32) + str(norm_quantity)
        return farmhash.hash32(hsource)

    @classmethod
    def aggregate_and_hash(cls, *ingredient_quantities):
        """Aggregate common ingredients among sequences
        of ingredient-quantity pairs and evaluate
        their hash.

        :param ingredient_quantities: Sequence of iterables
            of ``(Ingredient, quantity)`` 2-tuples.
        :rtype: int
        """
        return cls.evaluate_hash_static(
            cls.aggregate_ingredient_quantities(ingredient_quantities)
            )

    def iter_mixture_ingredients(self, include_nested=True):
        through = self.ingredient.through.objects
        for mi in through.filter(mixture=self):
            yield mi
        if include_nested:
            for m in self.mixture.all():
                for mi in m.iter_mixture_ingredients():
                    yield mi

    def iter_ingredient_quantities(self, include_nested=True):
        """Iterate on couples of ingredients and
        respective quantities that make up this
        mixture.

        :return: An iterator on tuples ``(ingredient-instance, quantity)``.
        """
        for mi in self.iter_mixture_ingredients(include_nested):
            yield (mi.ingredient, mi.quantity)

    @staticmethod
    def normalize(ingredient_quantity, reference='flour'):
        """Normalize ingredient quantities w.r.t the
        total quantity of the ingredients of the
        specified ``reference`` type. If no such ingredient
        is found, quantities are normalized w.r.t.
        the maximum quantity of the existing
        ingredients.

        This conveniently yields the baker's ratio
        if we normalize w.r.t. flour-ingredients.

        :param list ingredient_quantity: A list of tuples ``(<Ingredient>: quantity)``.
        :type quantities: dict or None
        :param str reference:
        :return: An iterator of tuples ``(ingredient_instance, normalized_value)``.
        """
        total = sum((quantity for (i, quantity) in ingredient_quantity if
                     i.type == reference))
        total = total or max([quantity for _, quantity in ingredient_quantity])
        for i, quantity in ingredient_quantity:
            yield i, quantity/total

    @classmethod
    @transaction.atomic
    def new(cls, title='Overall', ingredient_quantity=None, unit='[gr]',
            mixtures=None):
        """Create a new mixture entry by specifying
        mixture ingredients.

        :param str title:
        :param ingredient_quantity: A sequence of ``(Ingredient, <quantity>)``
            pairs.
        :type ingredient_quantity: iterable or None
        :param str unit: The unit of the quantities specified.
        :param mixtures: Sequence of nested 'Mixture' instances.
        :type mixtures: iterable or None
        :rtype: Mixture
        :raises IntegrityError: If a duplicate mixture exists in the
            database.
        """
        mixture = cls(title=title, unit=unit)
        mixture.save()
        if ingredient_quantity:
            for ingredient, quantity in ingredient_quantity:
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
            self.mixture.add(m)

    @update_properties_and_save
    def add_mixtures(self, mixtures, *, atomic=False):
        """Add multiple nested mixtures.

        :param iterable mixtures: The sequence of ``Mixture`` instances
            to add.
        :param bool atomic: If ``True`` update the dependent
            properties of the mixture.
        """
        for m in mixtures:
            self.mixture.add(m)

    @classmethod
    def get_duplicate(cls, ingredient_quantity):
        """Given a map between ingredients and quantities
        check if the database contains a duplicate.

        :param ingredient_quantity: Sequence of
            ``(Ingredient, quantity)`` tuples.
        :rtype: Mixture or None
        """
        return cls.objects.filter(
            hash32=cls.evaluate_hash_static(ingredient_quantity)
            ).first()

    def __str__(self):
        return pprint.pformat(
            {f'{i}': q for i, q in self.ingredient_quantities}
            )

    def __add__(self, other):
        iq = defaultdict(int)
        for i, q in [*self.ingredient_quantities, *other.ingredient_quantities]:
            iq[i] += q
        try:
            with transaction.atomic():
                return Mixture.new(self.title, iq.items())
        except IntegrityError:
            mixture = Mixture.get_by_key(self.evaluate_hash_static(iq.items()))
            mixture.multiply(mixture.evaluate_factor(iq.items()))
            return mixture

    def __sub__(self, other):
        iq = defaultdict(int)
        for i, q in self.ingredient_quantities:
            iq[i] += q
        for i, q in other.ingredient_quantities:
            iq[i] -= q
        try:
            with transaction.atomic():
                return Mixture.new(self.title, iq.items())
        except IntegrityError:
            mixture = Mixture.get_by_key(self.evaluate_hash_static(iq.items()))
            mixture.multiply(mixture.evaluate_factor(iq.items()))
            return mixture


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


class RecipeMixture(models.Model):
    recipe = models.ForeignKey('Recipe', on_delete=models.CASCADE)
    mixture = models.ForeignKey(Mixture, on_delete=models.CASCADE)
    factor = models.FloatField(default=1.)

    class Meta:
        db_table = 'recipe_deductible'


class Recipe(Hash32Model):
    title = models.CharField(max_length=128)
    overall = models.ForeignKey(Mixture, models.CASCADE, null=True,
                                db_index=False)
    overall_factor = models.FloatField(default=1.)
    final = models.ForeignKey(Mixture, models.SET_NULL, null=True,
                              db_index=False, related_name='+')
    final_factor = models.FloatField(default=1.)
    deductible = models.ManyToManyField(
        Mixture,
        through=RecipeMixture,
        related_name='recipes'
        )
    instructions = models.ManyToManyField(
        Instruction,
        db_table='recipe_instruction'
        )
    # TODO: Evaluate hash based on mixtures and instructions
    hash32 = UnsignedIntegerField(default=None, unique=True, null=True)

    class Meta:
        db_table = 'recipe'

    def evaluate_hash(self, *args, **kwargs):
        args = args or list(filter(None, (self.overall, self.deductible.all())))
        return self.evaluate_hash_static(*args, **kwargs)

    def iter_deductible_factor(self):
        for instance in self.deductible.through.objects.filter(recipe=self):
            yield instance.mixture, instance.factor

    @update_properties_and_save
    def add_overall_formula(self, ingredient_quantity, unit='[gr]',
                            mixtures=None, *, atomic=True):
        """Instantiate the overall formula of the recipe.

        :param iterable ingredient_quantity:
        :param str unit:
        :param mixtures:
        :type mixtures: iterable(Mixture) or None
        """
        try:
            with transaction.atomic():
                self.overall = Mixture.new(
                    'Overall formula', ingredient_quantity, unit, mixtures
                    )
        except IntegrityError:
            # We allow here duplicate overall formula, for the case
            # of different deductible mixtures included. The integrity
            # check is delegated to `Recipe.new`.
            ingredients = Mixture.aggregate_ingredient_quantities(
                ingredient_quantity, *(mixtures or [])
                )
            self.overall = Mixture.get_duplicate(ingredients)
            self.overall_factor = self.overall.evaluate_factor(ingredients)

    @update_properties_and_save
    def add_deductible_mixture(self, title, ingredient_quantity, unit='[gr]',
                               mixtures=None, *, atomic=True, is_loaded=False):
        """Add a mixture that needs to be prepared independently, and can
        be deducted from the overall formula.

        :param str title: Title of the mixture.
        :param iterable ingredient_quantity: Iterable of ``(Ingredient,
            <quantity>)`` pairs.
        :param str unit:
        :param mixtures:
        :type mixtures: iterable(Mixture) or None
        :param bool atomic: Update properties and save instance if `True`.
        :param bool is_loaded: If `True` the mixture already exists in the
            database, so we can avoid the attempt to save it.
        """
        if is_loaded:
            to_add = ingredient_quantity
            to_add.total_yield = None
            factor = to_add.evaluate_factor(to_add.ingredient_quantities)
        else:
            try:
                with transaction.atomic():
                    to_add = Mixture.new(title, ingredient_quantity, unit,
                                         mixtures=mixtures)
                    factor = 1.
            except IntegrityError:
                # Mixture exists, but we allow recipes with identical mixture
                # components. We delegate the integrity check to `Recipe.new`.
                ingredient_quantity = Mixture.aggregate_ingredient_quantities(
                    ingredient_quantity, *(mixtures or [])
                    )
                to_add = Mixture.get_duplicate(ingredient_quantity)
                factor = to_add.evaluate_factor(ingredient_quantity)

        self.deductible.add(to_add, through_defaults={'factor': factor})

    def calculate_final(self):
        self.final = self.overall.multiply(self.overall_factor)
        for mixture, factor in self.iter_deductible_factor():
            self.final = self.final - mixture.multiply(factor)
        self.final.title = 'Final'
        calculated_analogy = self.final.ingredient_quantities
        self.final.cache_ingredient_quantities()
        self.final_factor = self.final.evaluate_factor(calculated_analogy)

    @classmethod
    @transaction.atomic
    def new(cls, title, overall, unit='[gr]', partial=None, nested=None,
            loaded=None, *, atomic=True):
        """Create a new `Recipe` instance and save the respective record
        to the database, if no duplicate is found.

        :param str title: The title of the recipe.
        :param iterable overall: A sequence of ``(Ingredient, <quantity>)``
            2-tuples that represent the overall mixture.
        :param str unit: The unit of measurement for the quantities.
        :param partial: A sequence of
            ``(<title>, [(Ingredient, <quantity>),...])`` 2-tuples
            representing the deductible mixtures of the recipe that
            might not already exist in the database.
        :type partial: iterable or None
        :param nested: A dictionary map::

                {'overall': [<nested_mixture>,...],
                 'partial': [[<nested_mixture>,...],...]}

            to infer on any nested mixtures with respect
            to the overall formula, and the deductible
            mixtures of the recipe.

            The cardinality of the nested mixtures in ``nested['partial']``
            should be of course consistent with the cardinality in
            ``partial``.
        :param loaded: A sequence of `Mixture` instances
            corresponding to partial mixtures within the recipe
            that exist in the database.
        :rtype: Recipe
        :raises IntegrityError: In case of a duplicate recipe
        """
        recipe = cls(title=title)
        recipe.save()

        nested = nested or {}
        recipe.add_overall_formula(ingredient_quantity=overall, unit=unit,
                                   mixtures=nested.get('overall'), atomic=False)
        i = 0
        nested_deductible = nested.get('partial', [])
        for _title, ingredients in (partial or []):
            nested_deductible.append(None) # Satisfy existence
                                           # of the index in the function call
                                           # below
            recipe.add_deductible_mixture(
                title=_title, ingredient_quantity=ingredients, unit=unit,
                mixtures=nested_deductible[i], atomic=False
                )
            i += 1
        for mixture in (loaded or []):
            recipe.add_deductible_mixture(None, mixture, unit=unit,
                                          atomic=False, is_loaded=True)
        recipe.calculate_final()
        recipe.update_properties()
        recipe.save()
        return recipe

    @staticmethod
    def evaluate_hash_static(overall, deductible=None, nested=None):
        """Evaluate the hash of a recipe given the information
        on the included mixtures.

        :param iterable overall: A sequence of ``(Ingredient, <quantity>)``
            2-tuples that represent the overall mixture.
        :param deductible: A sequence of deductible mixtures
            ``[[(Ingredient, <quantity>),...]]``
            representing the deductible mixtures of the recipe.
        :type deductible: iterable or None
        :param nested: A dictionary map following the signature of
            `Recipe.new`.
        :rtype: int
        """
        nested = nested or {}
        hashes = [
            Mixture.evaluate_hash_static(overall, *nested.get('overall', []))
            ]

        nested_deductible = nested.get('deductible', [])
        i = 0
        for ingredients in (deductible or []):
            nested_deductible.append([])
            hashes.append(
                Mixture.evaluate_hash_static(ingredients, *nested_deductible[i])
                )
            i += 1
        hashes.sort()
        return farmhash.hash32(''.join(map(str, hashes)))


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
