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
function cloneMore(selector, prefix) {
    console.log($(selector));
    var newElement = $(selector).clone(true);
    var total = $('#id_' + prefix + '-TOTAL_FORMS').val();
    newElement.find(':input:not([type=button]):not([type=submit]):not([type=reset])').each(function() {
            var name = $(this).prop('name').replace('-' + (total-1) + '-', '-' + total + '-');
            var id = 'id_' + name;
            $(this).attr({'name': name, 'id': id}).val('').removeAttr('checked');
        });
    newElement.find('label').each(function() {
            var forValue = $(this).attr('for');
            if (forValue) {
                      forValue = forValue.replace('-' + (total-1) + '-', '-' + total + '-');
                      $(this).attr({'for': forValue});
                    }
        });
    total++;
    $('#id_' + prefix + '-TOTAL_FORMS').val(total);
    $(selector).after(newElement);
    /*var conditionRow = $('.form-row:not(:last)');
    *conditionRow.find('.btn.add-ingredient')
    *.removeClass('btn-success').addClass('btn-danger')
    *.removeClass('add-ingredient').addClass('remove-ingredient')
    *.html('<span class="fa fa-minus"></span>')
    */
    return false;
}
function deleteForm(prefix, btn) {
    var total = parseInt($('#id_' + prefix + '-TOTAL_FORMS').val());
    console.log(total);
    if (total > 2){
            btn.closest('.form-dynamic').remove();
            var forms = $('.form-dynamic');
            $('#id_' + prefix + '-TOTAL_FORMS').val(forms.length);
            for (var i=0, formCount=forms.length; i<formCount; i++) {
                        $(forms.get(i)).find(':input').each(function() {
                                        updateElementIndex(this, prefix, i);
                                    });
                    }
    } else {
        alert("More than two ingredients are required...");
    }
    return false;
}
$(document).on('click', '.add-ingredient', function(e){
    e.preventDefault();
    cloneMore('.form-dynamic:last', 'form');
    return false;
});
$(document).on('click', '.remove-ingredient', function(e){
    e.preventDefault();
    deleteForm('form', $(this));
    return false;
});
