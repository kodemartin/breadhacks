from django.test import TestCase
from farmhash import hash32

from recipes.models import Ingredient, Mixture


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


class TestRecipe(TestCase):

    def setUp(self):
        self.overall = {
            ('Bread flour',): 1000,
            ('Water',): 700,
            ('Salt',): 20
            }
        self.culture = {
            ('Bread flour',): 1000,
            ('Water',): 600,
            }
