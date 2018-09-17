import farmhash

from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import Ingredient


@receiver(pre_save, sender=Ingredient)
def evaluate_hash(sender, instance, **kwargs):
    instance.hash32 = 13
