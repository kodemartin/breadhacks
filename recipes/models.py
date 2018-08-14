from django.db import models
from farmhash import hash32
from myfields import UnsignedIntegerField

# Create your models here.
class Ingredient(models.Model):
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
    hash32 = UnsignedIntegerField(null=True)

    class Meta:
        db_table = 'ingredient'

    def save(self, *args, **kwargs):
        self.hash32 = hash32(self.name + (self.type or '') +
                             (self.variety or ''))
        super().save(*args, **kwargs)
