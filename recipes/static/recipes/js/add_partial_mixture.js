function addPartialMixture(btn) {
    /**
     * Issud an AJAX request to /recipes/mixture/new
     * to fetch the html of the respective form, and
     * then add it before the `btn`.
     *
     * @param Element btn The button that triggers the action
     * @returns Boolean
     */
    let partialCount = $('.partial-mixture-template').length;
    $.get('/recipes/mixture/new', {'prefix': 'partial_' + partialCount},
          function (response) {
              let form = $(response).find('.partial-mixture-template');
              btn.parents('.row').before(form);
              form.find('input').first().attr("placeholder", "Partial mixture title");
              form.find('[id*=unit]').parent().remove();
              form.after('<hr>');
          });
};

$(document).on('click', '#add-mixture', function(e){
    e.preventDefault();
    addPartialMixture($(this));
    return false;
});

/**
 * Uncomment to bind any other 'unit' selects to the '#master-units' select
 *
 * $('#master-units').change(function() {
 *     $("select").filter("[id!=master-units][id*=unit]").val($(this).val());
 * });
 */
