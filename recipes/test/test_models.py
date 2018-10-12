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
        self.m1 = {
            ('Bread flour',): 1000,
            ('Water',): 700,
            ('Salt',): 20
            }
        self.m2 = {
            ('Bread flour',): 1000,
            ('Water',): 700,
            ('Salt',): 18
            }

    def test_new(self):
        m = Mixture.new(ingredient_quantity=self.m1)
        self.assertIsInstance(m, Mixture)
        mstored = Mixture.objects.get(id=1)
        actual = {(i.name,): q for i, q in mstored.ingredient_quantities}
        self.assertDictEqual(actual, self.m1)
        m2 = Mixture.new(ingredient_quantity=self.m2)
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
