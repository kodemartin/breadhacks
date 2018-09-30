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
            'Bread flour': 1000,
            'Water': 700,
            'Salt': 20
            }
        self.m2 = {
            'Bread flour': 1000,
            'Water': 700,
            'Salt': 18
            }

    def test_new(self):
        m = Mixture.new(ingredient_quantity=self.m1)
