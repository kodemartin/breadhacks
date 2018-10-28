from django.db import models
from functools import wraps

from custom_fields import UnsignedIntegerField


def update_properties_and_save(method):
    """Decorate a model-instance
    method to update cached properties
    and update the respective entry
    to the database.

    The model should have an
    ``update_properties`` method.

    For the decoration to take effect,
    a key-word argument ``atomic`` should
    be passed to the decorated method.
    """
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        method(self, *args, **kwargs)
        if kwargs.get('atomic'):
            self.update_properties()
            self.save()

    return wrapper


class Hash32Model(models.Model):

    hash32 = UnsignedIntegerField(unique=True, null=True)

    class Meta:
        abstract = True

    def evaluate_hash(self):
        NotImplemented

    def update_hash(self):
        self.hash32 = self.evaluate_hash()

    def update_properties(self):
        self.update_hash()
