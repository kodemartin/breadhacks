from django.db import migrations
from farmhash import hash32


def apply(apps, schema_editor):
    Ingredient = apps.get_model("recipes", "Ingredient")
    new_ingredients = [
        ("Bread flour", "flour", None),
        ("Durum wheat", "flour", None),
        ("Rye", "flour", "white"),
        ("Rye", "flour", "medium"),
        ("Rye", "flour", "dark"),
        ("Rye", "meal", "fine"),
        ("Rye", "meal", "medium"),
        ("Rye", "meal", "coarse"),
        ("Rye", "malt", "berries"),
        ("All purpose flour", "flour", None),
        ("Sun-flower seed", "seed", None),
        ("Flaxseed", "seed", None),
        ("Olive-oil", "fat", None),
        ("Water", "water", None),
        ("Salt", "other", None)
        ]

    for name, _type, variety in new_ingredients:
        ingredient = Ingredient(name=name, type=_type, variety=variety)
        ingredient.hash32 = ingredient.evaluate_hash()
        ingredient.save()


def rollback(apps, schema_editor):
    Ingredient = apps.get_model("recipes", "Ingredient")
    db_alias = schema_editor.connection.alias
    for ingredient in Ingredient.objects.all():
        ingredient.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0005_expand-ingredient-type-choices'),
    ]

    operations = [
        migrations.RunPython(apply, rollback)
    ]
