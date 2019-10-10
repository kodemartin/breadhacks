/*
 * Handle nested mixtures
 *
 */
function updatePrefix(el, old, new_) {
    if (el.attr("for")) el.attr("for", el.attr("for").replace(old, new_));
    if (el.attr("id")) el.attr("id", el.attr("id").replace(old, new_));
    if (el.attr("name")) el.attr("name", el.attr("name").replace(old, new_));
}

function addNestedMixture(btn, form_class = 'nested-mixture') {
    let parentFormSet = btn.parents('.formset-dynamic');
    let baseForm = parentFormSet.find(`.${form_class}`).last();
    let newElement = baseForm.clone(true);
    btn.parents('.row').before(newElement);
    // Update prefix
    let parentPrefix = parentFormSet.find('[id*=TOTAL]').attr('id')
                                    .match(/id_(\w+)-TOTAL_\w+/)[1];
    let idx = parentFormSet.find('.dynamic-mixture').length - 1;

    let old = /\d+/;
    let new_ = idx;
    if (newElement.hasClass('hidden')) {
        newElement.removeClass('hidden');
        baseForm.remove();
        old = 'prefix';
        idx -= 1;
        new_ = `${parentPrefix}_nested_${idx}`;
    }
    newElement.find(':input, label').each(function() {
        updatePrefix($(this), old, new_);
    });
    return false;
}

function deleteNestedMixture(btn, form_class = 'nested-mixture') {
    btn.closest('.' + form_class).remove();
    return false;
    }

$(document).on('click', '.add-nested', function(e){
    e.preventDefault();
    addNestedMixture($(this));
    return false;
});

$(document).on('click', '.remove-nested', function(e){
    e.preventDefault();
    deleteNestedMixture($(this));
    return false;
});
