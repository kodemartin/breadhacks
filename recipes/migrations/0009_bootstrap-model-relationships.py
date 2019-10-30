# Generated by Django 2.1 on 2018-08-17 13:59

import custom_fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0008_use-unsigned-integer-for-ingredient-hash'),
    ]

    operations = [
        migrations.CreateModel(
            name='Implementation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'implementation',
            },
        ),
        migrations.CreateModel(
            name='ImplementationNotes',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('implementation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='recipes.Implementation')),
            ],
            options={
                'db_table': 'implementation_notes',
            },
        ),
        migrations.CreateModel(
            name='Instruction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=128)),
                ('text', models.TextField()),
            ],
            options={
                'db_table': 'instruction',
            },
        ),
        migrations.CreateModel(
            name='Mixture',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=128)),
                ('hash32', custom_fields.UnsignedIntegerField(default=None, null=True, unique=True)),
            ],
            options={
                'db_table': 'mixture',
            },
        ),
        migrations.CreateModel(
            name='MixtureIngredients',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', custom_fields.UnsignedIntegerField()),
                ('unit', models.CharField(choices=[('[gr]', 'grams'), ('[lb]', 'pounds'), ('[oz]', 'ounces'), ('[kg]', 'kilograms'), ('[-]', 'ratio'), ('[%]', 'percentage')], default='[gr]', max_length=32)),
                ('ingredient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='recipes.Ingredient')),
                ('mixture', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='recipes.Mixture')),
            ],
            options={
                'db_table': 'mixture_ingredients',
                'ordering': ['mixture_id', 'ingredient_id', 'quantity'],
            },
        ),
        migrations.CreateModel(
            name='Note',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=64)),
            ],
            options={
                'db_table': 'note',
            },
        ),
        migrations.CreateModel(
            name='Recipe',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=128)),
                ('hash32', custom_fields.UnsignedIntegerField(default=None, null=True, unique=True)),
                ('instruction', models.ManyToManyField(db_table='recipe_instructions', to='recipes.Instruction')),
                ('mixture', models.ManyToManyField(db_table='recipe_mixtures', to='recipes.Mixture')),
            ],
            options={
                'db_table': 'recipe',
            },
        ),
        migrations.AddField(
            model_name='mixture',
            name='ingredients',
            field=models.ManyToManyField(through='recipes.MixtureIngredients', to='recipes.Ingredient'),
        ),
        migrations.AddField(
            model_name='implementationnotes',
            name='notes',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='recipes.Note'),
        ),
        migrations.AddField(
            model_name='implementation',
            name='mixture',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='recipes.Mixture'),
        ),
        migrations.AddField(
            model_name='implementation',
            name='recipe',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='recipes.Recipe'),
        ),
    ]
