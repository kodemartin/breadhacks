from django.db import IntegrityError
from django.test import TestCase
from farmhash import hash32

from recipes.models import Ingredient, Mixture, Recipe


class TestIngredient(TestCase):

    def test_get(self):
        bread_flour = Ingredient.get(name='Bread flour')
        self.assertIsInstance(bread_flour, Ingredient)
        self.assertEqual(bread_flour.name, 'Bread flour')
        self.assertEqual(bread_flour.type, 'flour')
        null = Ingredient.get(name='Bread flour', _type='meal')
        self.assertIsNone(null)


class TestMixture(TestCase):

    def setUp(self):
        ingredients = [Ingredient.objects.get(name__istartswith=f'{n}')
                       for n in ('bread', 'water', 'salt', 'durum')]
        self.m1 = list(zip(ingredients, (1000, 700, 20)))
        self.m2 = list(zip(ingredients, (1000, 700, 18)))
        self.m3 = self.m1 + [(ingredients[-1], 110)]

    def test_new(self):
        m = Mixture.new(ingredient_quantity=self.m1)
        self.assertIsInstance(m, Mixture)
        mstored = Mixture.objects.get(pk=m.id)
        actual = list(mstored)
        self.assertListEqual(actual, self.m1)
        m2 = Mixture.new(ingredient_quantity=self.m2)
        self.assertIsInstance(m2, Mixture)

    def test_get_duplicate(self):
        m1 = Mixture.new(ingredient_quantity=self.m1)
        m = Mixture.get_duplicate(m1)
        self.assertEqual(m.id, m1.id)
        self.assertEqual(m.hash32, m1.hash32)

    def test_new_extension(self):
        m1 = Mixture.new(ingredient_quantity=self.m1)
        m2 = Mixture.new(ingredient_quantity=self.m3)
        self.assertIsInstance(m2, Mixture)

    def test_new_assert_raises(self):
        iq = {
            ('Bread flour',): 1000,
            ('Unknown',): 700,
            ('Salt',): 18
            }
        with self.assertRaises(ValueError):
            m = Mixture.new(ingredient_quantity=iq)

    def test_new_rollbacked(self):
        iq = {
            ('Bread flour',): 1000,
            ('Water',): 'inconsistent',
            ('Salt',): 18
            }
        with self.assertRaises(Exception):
            m = Mixture.new(ingredient_quantity=iq)
        self.assertIsNone(Mixture.objects.all().first())

    def test_new_nested_mixtures(self):
        m1 = Mixture.new(ingredient_quantity=self.m1)
        m2 = Mixture.new(ingredient_quantity=self.m2, mixtures=(m1, ))
        m3 = Mixture.new(ingredient_quantity=self.m3, mixtures=(m2, ))
        expected = {
            Ingredient.get('Bread flour'): 3000,
            Ingredient.get('Water'): 2100,
            Ingredient.get('Salt'): 58,
            Ingredient.get('Durum wheat'): 110.
            }
        self.assertDictEqual(dict(m3.ingredient_quantities), expected)

    def test_add(self):
        m1 = Mixture.new(ingredient_quantity=self.m1)
        m2 = Mixture.new(ingredient_quantity=self.m2)
        m = m1 + m2
        expected = {
            Ingredient.get('Bread flour'): 2000, 
            Ingredient.get('Water'): 1400,
            Ingredient.get('Salt'): 38
            }
        self.assertDictEqual(dict(m.ingredient_quantities), expected)

    def test_sub(self):
        m1 = Mixture.new(ingredient_quantity=self.m1)
        m2 = Mixture.new(ingredient_quantity=self.m2)
        m = m1 - m2
        expected = {
            Ingredient.get('Bread flour'): 0,
            Ingredient.get('Water'): 0,
            Ingredient.get('Salt'): 2
            }
        self.assertDictEqual(dict(m.ingredient_quantities), expected)

    def test_nested_mixture(self):
        m1 = Mixture.new(ingredient_quantity=self.m1)
        initial_hash = m1.hash32
        m2 = Mixture.new(ingredient_quantity=self.m2)
        m1.add_mixtures((m2, ), atomic=True)
        expected = {
            Ingredient.get('Bread flour'): 2000,
            Ingredient.get('Water'): 1400,
            Ingredient.get('Salt'): 38
            }
        self.assertDictEqual(dict(m1.ingredient_quantities), expected)
        self.assertNotEqual(m1.hash32, initial_hash)

    def test_evaluate_factor(self):
        m1 = Mixture.new(ingredient_quantity=self.m1)
        factor = 2.
        duplicate = [(i, factor*q) for i, q in self.m1]
        self.assertEqual(m1.evaluate_factor(duplicate), factor)


class TestRecipe(TestCase):

    def setUp(self):
        self.ingredients = [Ingredient.objects.get(name__istartswith=f'{n}')
                            for n in ('bread', 'water', 'salt', 'durum')]
        self.overall = list(zip(self.ingredients, (1000, 700, 20)))

    def create_test_recipe(self):
        recipe = Recipe(title='test')
        recipe.save()
        return recipe

    def create_mixture(self, ingredient_quantity, title='test'):
        """Save an instance of a Mixture relation
        to the test database.

        :param iterable ingredient_quantity: ``(Ingredient, <quantity>)``
        :rtype: Mixture
        """
        return Mixture.new(title, ingredient_quantity)

    def test_add_overall_formula(self):
        recipe = self.create_test_recipe()
        recipe.add_overall_formula(self.overall)

        self.assertIsInstance(recipe.overall, Mixture)

        expected_hash = Mixture.evaluate_hash_static(self.overall)
        actual_hash = recipe.overall.hash32
        self.assertEqual(expected_hash, actual_hash)

    def test_add_duplicate_overall_formula(self):
        factor = 2.
        overall = [(i, factor*q) for i, q in self.overall]

        m = self.create_mixture(self.overall, 'prior')

        recipe = self.create_test_recipe()
        recipe.add_overall_formula(overall)
        self.assertEqual(recipe.overall_factor, factor)

        partial = list(zip(self.ingredients[:2], (100, 100)))
        recipe.add_deductible_mixture('partial', partial)

        recipe.calculate_final()
        expected = dict(zip(self.ingredients[:3], (1900., 1300, 40)))
        actual = dict(recipe.final)
        self.assertDictEqual(expected, actual)

    def test_add_deductible_mixture(self):
        recipe = self.create_test_recipe()
        recipe.add_overall_formula(self.overall)

        partial = list(zip(self.ingredients[:2], (300., 300.)))
        recipe.add_deductible_mixture('test-partial', partial)

        deductibles = recipe.deductible.all()
        self.assertEqual(len(deductibles), 1)

        hash32 = Mixture.evaluate_hash_static(partial)
        self.assertEqual(deductibles[0].hash32, hash32)

    def test_add_duplicate_deductible_mixture(self):
        recipe = self.create_test_recipe()
        recipe.add_overall_formula(self.overall)

        prior = list(zip(self.ingredients[:2], (300., 300.)))
        m = self.create_mixture(prior, 'prior')

        factor = 2.
        partial = [(i, factor*q) for i, q in prior]
        recipe.add_deductible_mixture('test-partial', partial)

        deductible = list(recipe.iter_deductible_factor())
        self.assertEqual(len(deductible), 1)
        stored_mixture, stored_factor = deductible[0]
        self.assertAlmostEqual(stored_mixture.hash32, m.hash32)
        self.assertAlmostEqual(stored_factor, factor)

    def test_calculate_final(self):
        recipe = self.create_test_recipe()
        recipe.add_overall_formula(self.overall)

        partial = list(zip(self.ingredients[:2], (300., 300.)))
        recipe.add_deductible_mixture('test-partial', partial)

        recipe.calculate_final()
        expected = dict(zip(self.ingredients[:3], (700, 400, 20)))
        actual = dict(recipe.final)
        self.assertDictEqual(actual, expected)

    def test_calculate_duplicate_final(self):
        recipe = self.create_test_recipe()
        recipe.add_overall_formula(self.overall)

        partial = list(zip(self.ingredients[:2], (300., 300.)))
        recipe.add_deductible_mixture('test-partial', partial)

        prior_iq = zip(self.ingredients[:3], (350, 200, 10))
        prior = self.create_mixture(prior_iq, 'prior')

        recipe.calculate_final()

        expected = dict(zip(self.ingredients[:3], (350, 200, 10)))
        actual = dict(recipe.final)
        self.assertDictEqual(actual, expected)

        self.assertEqual(recipe.final_factor, 2.)

    def test_add_loaded_deductible(self):
        recipe = self.create_test_recipe()
        recipe.add_overall_formula(self.overall)

        prior = zip(self.ingredients[:2], (300., 300.))
        m = self.create_mixture(prior, 'prior')

        factor = 2.
        recipe.add_deductible_mixture(None, m.multiply(factor), atomic=False,
                                      is_loaded=True)
        deductible = list(recipe.iter_deductible_factor())
        self.assertEqual(len(deductible), 1)
        stored_mixture, stored_factor = deductible[0]
        self.assertEqual(stored_mixture.hash32, m.hash32)
        self.assertEqual(stored_factor, factor)

    def test_calculate_final_avoid_saving_intermediate_mixtures(self):
        recipe = self.create_test_recipe()
        recipe.add_overall_formula(self.overall)

        partial0 = zip(self.ingredients[:2], (312., 300.))
        partial1 = zip(self.ingredients, (112., 111., 3.))
        for p in (partial0, partial1):
            recipe.add_deductible_mixture('test_p', p, atomic=False)
        recipe.calculate_final()
        self.assertEqual(len(Mixture.objects.all()), 4)
