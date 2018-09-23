from django.db import models

from custom_fields import UnsignedIntegerField


class Hash32Model(models.Model):

    hash32 = UnsignedIntegerField(unique=True, null=True)

    class Meta:
        abstract = True

    def evaluate_hash(self):
        NotImplemented

    def update_hash(self):
        self.hash32 = self.evaluate_hash()
