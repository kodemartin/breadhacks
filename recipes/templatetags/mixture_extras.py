from django import template


register = template.Library()


@register.inclusion_tag('mixtures/preview_table.html')
def preview_mixture_table(mixture, factor=1., toggle_nests=False):
    """Prepare the context for the template of a table preview
    for a given mixture.

    :param models.Mixture mixture:
    :param float factor:
    :param bool toggle_nests: If `True` create a checkbox input
        to toggle nests.
    """
    nested = [m.multiply(f*factor) for m, f in mixture.iter_mixture_factor()]
    mixture.multiply(factor)
    collapsed = mixture.iter_ingredient_quantities(include_nested=False,
                                                   factor=factor)
    return {'mixture': mixture, 'nested': nested, 'collapsed': collapsed,
            'toggle_nests': toggle_nests}
