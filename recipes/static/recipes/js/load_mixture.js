$('.basicAutoComplete').autoComplete({
    resolverSettings: {
            url: '/recipes/mixture/list/partial/'
        }
});

$('#loadable-mixture').change(function (){
    /**
     * Upon selection of a mixture
     * this function loads a form with initial
     * data the title, and ingredients of the loaded form.
     */
    let select = $(this);
    let id = select.val();
    $.get(
        '/recipes/mixture/list/ingredients', {'id': id}
    ).then(function (data) {
        // Request the html of the form from the API
        let loadableCount = $('.partial-mixture-template').filter(
            function(){
                return $(this).find(":input").filter("[id*=loadable]").length > 0;
            }).length;
        return $.post('/recipes/mixture/load/',
                      {'prefix': 'loadable_' + loadableCount,
                       'initial': JSON.stringify(data)});
    }).then(function (response) {
        // Insert the form
        let form = $(response);
        $(select).parents('.row').before(form);
        form.find('[id*=unit]').parent().remove();
        form.after('<hr>');
        // Remove extra form-rows
        let to_remove = form.find("select").filter(function() {
            return $(this).val() === "";
        }).parents('.form-row');
        let decr = to_remove.length;
        to_remove.remove();
        // Update management form
        let total = form.find('input').filter('[id*=TOTAL_FORMS]');
        console.log(total);
        total.val(total.val() - decr);
        select.val("");
    });
});
