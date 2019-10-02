function validateIngredient(ingredientField, valid_ingredients, parentForm) {
    /**
     * Check if the ingredient provided in the field
     * is contained in the set of valid ingredients.
     *
     * @param jQuery ingredientField A form field element with the ingredient.
     * @param Set valid_ingredients Set of the valid ingredient ids
     */
    if (! valid_ingredients.has(ingredientField.val())) {
        if (! parentForm.hasClass("was-validated")) {
            parentForm.addClass("was-validated");
        }
        ingredientField.get(0).setCustomValidity(
            "Must be one of the ingredients in the overall formula"
        );
    } else {
        ingredientField.get(0).setCustomValidity("");
    }
};

function validateIngredients(form) {
    /**
     * Validate ingredients of the partial mixtures
     * within the recipe
     *
     * @param jQuery The form element of the recipe
     */
    let overall = new Set();
    let ingredients = $("[id*=ingredient]");
    // Assume valid ingredients
    ingredients.each(function() {$(this).get(0).setCustomValidity("");});
    // Create set of valid ingredients
    ingredients.filter("[id*=overall]").each(function() {
        if ($(this).val() !== "") {
            overall.add($(this).val());
        }
    });
    // Cross validate ingredients of partial and loaded
    // mixtures
    ingredients.filter("[id*=partial]").each(function() {
        validateIngredient($(this), overall, form);
    });
    ingredients.filter("[id*=loadable]").each(function() {
        validateIngredient($(this), overall, form);
    });
};

function validateQuantities(form) {
    /**
     * Ensure that the sum quantity of the overall formula
     * is greater than or equal to the sum of the quantities
     * of all partial and loaded mixtures.
     *
     * @param jQuery form
     */
    let quantities = form.find("[id*=quantity]");
    // Evaluate the total sum
    let overall = quantities.filter("[id*=overall]").map(function() {
        return parseFloat($(this).val())
    }).get();
    let totalSum = overall.reduce(sumReducer, 0.);
    alert(JSON.stringify(totalSum));
    // Find the sum of all partial mixtures
    let partialQuantities = quantities.filter(":not([id*=overall])");
    let partial = partialQuantities.map(function() {
        return parseFloat($(this).val());
    }).get();
    let partialSum = partial.reduce(sumReducer, 0.);
    alert(JSON.stringify(partialSum));
    if (partialSum > totalSum) {
        if (! form.hasClass("was-validated")) {
            form.addClass("was-validated");
        }
        partialQuantities.each(function() {
            $(this).get(0).setCustomValidity(
                "Quantities greater than total sum of overall formula"
            )
        })
    } else {
        partialQuantities.each(function() {
            $(this).get(0).setCustomValidity("")
        });
    }
};

function validatePartialIngredients(form) {
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
    console.log(JSON.stringify(Array.from(overallIQ.keys())));
    let partial = ingredients.filter(":not([id*='overall'])");
    let errorCount = 0;
    partial.each(function() {
        let i = $(this).val();
        console.log(i);
        console.log(overallIQ.has(i));
        if (overallIQ.has(i)) {
            let q = $(this).parent().next().find("[id*='quantity']");
            console.log(q);
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
