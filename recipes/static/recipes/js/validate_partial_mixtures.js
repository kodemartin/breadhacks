function factorNestIngredients(data_factor) {
    /**
     *
     * Factor flatten mixture data fetched from mixture/list/ingredients
     *
     * The function returns a Promise so that it can be used
     * in an asynchronous context
     *
     * @param Array data_factor A 2-element array containing the
     *  response from mixture/list/ingredients and the factor
     *  to scale the respective flatten ingredient quantities.
     */
    return new Promise(resolve => {
        const [data, factor] = data_factor;
        const f = parseFloat(factor) / data['yield'];
        resolve(new Map(data['flatten'].map(p => [p[0], p[1]*f])));
    });
}

function listIngredients(mixtureId) {
    return $.get(
        '/recipes/mixture/list/ingredients',
        {'id': mixtureId}
    )
}

async function flattenNests(nests) {
    console.log("==> Start flattening..");
    const data = await Promise.all(
        Array.from(nests, m => listIngredients(m.value))
    );
    const data_factor = data.map(
        (d, i) => [d, $(nests[i]).parent().next().find("input").val()]
    );
    let iqs = await Promise.all(
        Array.from(data_factor, df => factorNestIngredients(df))
    );
    console.log("==> ..Flattening ended");
    return iqs;
}

async function validatePartialIngredients(form) {
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
    const ingredients = form.find("[id*='ingredient']");

    const nests = form.find("[id*='mixture'][id*=nested]");
    const overall_nests = nests.filter("[id*=overall]");
    const partial_nests = nests.filter(":not([id*=overall])");
    /*
     * Construct the overall ingredient-quantity map
     */
    const overall = ingredients.filter("[id*='overall']");
    const overallIQ = new Map();
    overall.each(function() {
        let I = parseInt($(this).val());
        let Q = parseFloat(
            $(this).parent().next().find("[id*='quantity']").val()
        );
        mapValueAdd(overallIQ, I, Q);
    });
    // Flatten nests
    const [overall_nest_iqs, partial_nest_iqs] = await Promise.all(
        [flattenNests(overall_nests), flattenNests(partial_nests)]
    );
    // Incorporate any nested mixture present
    overall_nest_iqs.forEach(map => {
        map.forEach((v, k) => { mapValueAdd(overallIQ, k, v); });
    });
    // Validate partial mixtures
    const partial = ingredients.filter(":not([id*='overall'])");
    const partialIQ = new Map(); // Map ingredient values to an iterable
                                 // of Arrays with quantity and field pairs.
    let errorCount = 0;

    function validateQuantity(parent, quantity, i, v, pmsg, qmsg) {
        /**
         *
         * @param jQuery parent
         * @param jQuery quantity
         * @param Integer i
         * @param Float v
         *
         */
        qmsg = qmsg ? qmsg : "Exceeds the quantities in the overall formula"
        pmsg = pmsg ? pmsg : "Not present in the overall formula"
        if (overallIQ.has(i)) {
            mapListPush(partialIQ, i, [quantity, v]);
            if (overallIQ.get(i) < v) {
                quantity.get(0).setCustomValidity(qmsg);
                errorCount += 1;
            }
        } else {
            parent.get(0).setCustomValidity(pmsg);
            errorCount += 1;
        }
    };

    // Validate individual ingredients
    partial.each(function() {
        let i = parseInt($(this).val());
        let q = $(this).parent().next().find('[id*=quantity]');
        let v = parseFloat(q.val());
        validateQuantity($(this), q, i, v);
    });

    // Validate nests
    partial_nests.each((index, nest) => {
        let iq = partial_nest_iqs[index];
        let q = $(nest).parent().next().find('[id*=quantity]');
        iq.forEach((v, i) => {
            validateQuantity(
                $(nest), q, i, v,
                "Mixture has ingredients not present in overall formula",
            );
        })
    });

    // Ensure that the sum of ingredients in the partial mixtures
    // is less than or equal to the respective quantity in the
    // overall formula
    partialIQ.forEach(function(v, k, map) {
        let pSum = v.reduce(
            (acc, cur) => acc + cur[1], 0.
        );
        if (pSum > overallIQ.get(k)) {
            v.forEach(function(item) {
                item[0].get(0).setCustomValidity(
                    "Sum should be less that the quantity in the overall formula"
                );
            });
            errorCount += 1;
        }
    });
    if (errorCount > 0) {
        form.addClass('was-validated');
    } else {
        form.submit();
    }
}

$(document).on('click', '[type=submit]', function(e){
    e.preventDefault();
    // Get the elements of interest
    let form = $('form');
    form.find(":input").each(function() {
        $(this).get(0).setCustomValidity("");
    });

    validatePartialIngredients(form);
});
