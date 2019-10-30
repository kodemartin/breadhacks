# Generated by Django 2.2.4 on 2019-09-13 14:00

import custom_fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0012_auto_20181028_0921'),
    ]

    operations = [
        migrations.CreateModel(
            name='MixtureIngredient',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', custom_fields.UnsignedIntegerField()),
                ('ingredient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='recipes.Ingredient')),
            ],
            options={
                'db_table': 'mixture_ingredient',
                'ordering': ['mixture_id', 'ingredient_id', 'quantity'],
            },
        ),
        migrations.RemoveField(
            model_name='mixture',
            name='ingredients',
        ),
        migrations.RemoveField(
            model_name='mixture',
            name='mixtures',
        ),
        migrations.AddField(
            model_name='mixture',
            name='mixture',
            field=models.ManyToManyField(related_name='_mixture_mixture_+', to='recipes.Mixture'),
        ),
        migrations.AddField(
            model_name='mixture',
            name='unit',
            field=models.CharField(choices=[('[gr]', 'grams'), ('[lb]', 'pounds'), ('[oz]', 'ounces'), ('[kg]', 'kilograms'), ('[-]', 'ratio'), ('[%]', 'percentage')], default='[gr]', max_length=32),
        ),
        migrations.DeleteModel(
            name='MixtureIngredients',
        ),
        migrations.AddField(
            model_name='mixtureingredient',
            name='mixture',
            field=models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to='recipes.Mixture'),
        ),
        migrations.AddField(
            model_name='mixture',
            name='ingredient',
            field=models.ManyToManyField(through='recipes.MixtureIngredient', to='recipes.Ingredient'),
        ),
    ]
