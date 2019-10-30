from django.db import models
from functools import wraps
from inspect import signature

from custom_fields import UnsignedIntegerField


def update_properties_and_save(method):
    """Decorate a model-instance
    method to update cached properties
    and update the respective entry
    to the database.

    The model should have an
    ``update_properties`` method.

    For the decoration to take effect,
    the key-word argument ``atomic`` should
    be set to True while calling the decorated
    method.
    """
    sig = signature(method)

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        method(self, *args, **kwargs)
        if kwargs.get('atomic', sig.parameters['atomic'].default):
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

    @classmethod
    def get_by_key(cls, key):
        """Return an object by querying the database
        for the specified key. The method first
        checks the `id` and then the `hash32` field.

        :param key: The key to lookup
        :type key: int or str
        :rtype: Mixture
        :raises DoesNotExist: If not object is found
            in the database.
        """
        Q = models.Q
        return cls.objects.get(Q(id=key) | Q(hash32=key))
