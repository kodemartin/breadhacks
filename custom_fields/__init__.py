from django.core import validators
from django.db import models
from django.utils.functional import cached_property


class UnsignedIntegerField(models.IntegerField):

    MAX_INT = 4294967295

    @cached_property
    def validators(self):
        # These validators can't be added at field initialization time since
        # they're based on values retrieved from `connection`.
        validators_ = [*self.default_validators, *self._validators]
        min_value, max_value = 0, self.MAX_INT
        if (min_value is not None and not
            any(isinstance(validator, validators.MinValueValidator) and
                validator.limit_value >= min_value for validator in validators_)):
            validators_.append(validators.MinValueValidator(min_value))
        if (max_value is not None and not
            any(isinstance(validator, validators.MaxValueValidator) and
                validator.limit_value <= max_value for validator in validators_)):
            validators_.append(validators.MaxValueValidator(max_value))
        return validators_

    def db_type(self, connection):
        return "INTEGER UNSIGNED"

    def get_internal_type(self):
        return "UnsignedIntegerField"

    def formfield(self, **kwargs):
        return super().formfield(**{
            'min_value': 0,
            'max_value': self.MAX_INT,
            **kwargs,
        })
