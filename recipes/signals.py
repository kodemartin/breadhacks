import farmhash

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Ingredient, MixtureIngredients


@receiver(pre_save, sender=Ingredient)
def evaluate_hash(sender, instance, **kwargs):
    instance.update_hash()

@receiver(post_save, sender=MixtureIngredients)
def update_mixture_hash(sender, instance, **kwargs):
    instance.mixture.update_properties()
    instance.mixture.save()
