/*
 *
 * Adapted from
 * https://medium.com/all-about-django/adding-forms-dynamically-to-a-django-formset-375f1090c2b0
 *
 */
function updateElementIndex(el, prefix, ndx) {
    var id_regex = new RegExp('(' + prefix + '-\\d+)');
    var replacement = prefix + '-' + ndx;
    if ($(el).attr("for")) $(el).attr("for", $(el).attr("for").replace(id_regex, replacement));
    if (el.id) el.id = el.id.replace(id_regex, replacement);
    if (el.name) el.name = el.name.replace(id_regex, replacement);
}

function addForm(btn, form_class = 'form-dynamic') {
    const [formset, form_total, prefix] = closestFormsetInfo(btn);
    const base_form = formset.children('.' + form_class).last();
    const newElement = base_form.clone(true);
    let total = form_total.val();
    newElement.find(
        ':input:not([type=button]:not([type=submit]:not([type=reset])))'
        ).each(function() {
            let name = $(this).prop('name').replace('-' + (total-1) + '-', '-' + total + '-');
            let id = 'id_' + name;
            $(this).attr({'name': name, 'id': id});
        });
    newElement.find('label').each(function() {
            let forValue = $(this).prop('for');
            if (forValue) {
                  forValue = forValue.replace('-' + (total-1) + '-', '-' + total + '-');
                  $(this).attr({'for': forValue});
                  }
        });
    total++;
    $('#' + form_total.prop('id')).val(total);
    base_form.after(newElement);
    return false;
}

function deleteForm(btn, form_class = 'form-dynamic') {
    const [formset, form_total, prefix] = closestFormsetInfo(btn);
    let total = parseInt(form_total.val());
    if (total > 2){
        btn.closest('.' + form_class).remove();
        let forms = formset.children('.form-dynamic');
        $('#' + form_total.prop('id')).val(forms.length);
        for (let i=0, formCount=forms.length; i<formCount; i++) {
                $(forms.get(i)).find(':input').each(function() {
                    updateElementIndex(this, prefix, i);
                    });
                }
    } else {
        alert("More than two ingredients are required...");
    }
    return false;
}

function closestFormsetInfo(btn, formset_class = 'formset-dynamic') {
    /**
     * Find the closest formset to the specified `btn`, and
     * aggregate related information.
     *
     *  @param {Element} btn The reference button.
     *  @param {String} formset_class The class of the parent formset.
     *  @returns {Array} A tuple with the following elements:
     *      - The jQuery object of the parent formset.
     *      - The jQuery object with the ``*TOTAL_FORMS`` component
     *        of the management form.
     *      - The prefix used for the parent formset.
     */
    const formset = btn.closest('.' + formset_class);
    const form_total = formset.children('[id*=TOTAL_FORMS]');
    const prefix = /id_(\w+)-TOTAL_FORMS/ig.exec(form_total.prop('id'))[1];
    return [formset, form_total, prefix];
}

$(document).on('click', '.add-ingredient', function(e){
    e.preventDefault();
    addForm($(this));
    return false;
});

$(document).on('click', '.remove-ingredient', function(e){
    e.preventDefault();
    deleteForm($(this));
    return false;
});
