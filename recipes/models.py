from django.db import models
from farmhash import hash32

# Create your models here.
class Ingredient(models.Model):
    TYPES = (
            ('flour', 'flour'),
            ('water', 'water'),
            ('liquid', 'liquid'),
            ('dry', 'other')
            )
    name = models.CharField(max_length=60)
    variety = models.CharField(max_length=60, null=True, default=None)
    type = models.CharField(max_length=60, choices=TYPES)
    hash32 = models.BigIntegerField(null=True)

    def save(self, *args, **kwargs):
        self.hash32 = hash32(self.name + (self.variety or ''))
        super().save(*args, **kwargs)
