function validatePartialIngredients(form) {
    /**
     * Check that the ingredients in any partial or
     * loaded mixture satisfy the following constraints:
     *
     *  - They are included in the overall formula.
     *  - Their quantity in any single mixture is
     *    less than the overall quantity.
     *  - The sum of their quantities throughout all
     *    partial or loaded mixtures is less than
     *    the overall quantity.
     *
     *  Otherwise the respective fields are marked
     *  as invalid, following bootstrap form-validation
     *  rules, with the help of `Field.setCustomValidity`
     *  method.
     *
     *  @param jQuery form
     */
    let ingredients = form.find("[id*='ingredient']");
    // Construct the overall ingredient-quantity map
    let overall = ingredients.filter("[id*='overall']");
    let overallIQ = new Map();
    overall.each(function() {
        let I = $(this).val();
        let Q = $(this).parent().next().find("[id*='quantity']").val();
        overallIQ.set(I, Q);
        });
    // Validate ingredients of the partial mixture
    let partial = ingredients.filter(":not([id*='overall'])");
    let partialIQ = new Map(); // Map ingredient values to an iterable
                               // of quantity-field elements.
    let errorCount = 0;
    partial.each(function() {
        let i = $(this).val();
        if (overallIQ.has(i)) {
            let q = $(this).parent().next().find("[id*='quantity']");
            if (partialIQ.get(i)) {
                partialIQ.get(i).push(q);
            } else {
                partialIQ.set(i, [q,]);
            }
            if (overallIQ.get(i) < parseFloat(q.val())) {
                q.get(0).setCustomValidity(
                    "Should be less that the quantity in the overall formula"
                );
                errorCount += 1;
            }
        } else {
            $(this).get(0).setCustomValidity(
                "Must be one of the ingredients in the overall formula"
            );
            errorCount += 1;
        }
    });
    // Ensure that the sum of ingredients in the partial mixture
    // is less than or equal to the respective quantity in the
    // overall formula
    partialIQ.forEach(function(v, k, map) {
        let pSum = v.reduce(
            (acc, cur) => acc + parseFloat(cur.val()), 0.
        );
        if (pSum > overallIQ.get(k)) {
            v.forEach(function(item) {
                item.get(0).setCustomValidity(
                    "Sum should be less that the quantity in the overall formula"
                );
            });
            errorCount += 1;
        }
    });
    if (errorCount > 0) {
        form.addClass('was-validated');
    }
}

$(document).on('click', '[type=submit]', function(e){
    // Get the elements of interest
    let form = $('form');
    form.removeClass('was-validated');
    form.find(":input").each(function() {
        $(this).get(0).setCustomValidity("");
    });

    validatePartialIngredients(form);
    if (form.hasClass('was-validated')) {
        e.preventDefault();
    } else {
        return true;
    }
});
