function getCookie(name) {
    /**
     * From https://docs.djangoproject.com/en/2.2/ref/csrf/
     */
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

let csrftoken = getCookie('csrftoken');

$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

function sumReducer(accumulator, currentValue) {
    /**
     * Reduce function that returns the
     * sum of the elements of an Array
     */
    return accumulator + currentValue;
}

function mapValueAdd(map, key, value) {
    /**
     *
     * @param Map map
     * @param hashable key
     * @param Float or Integer value
     *
     */
    const old = map.get(key);
    if (old) {
        map.set(key, value + old);
    } else {
        map.set(key, value);
    }
}

function mapListPush(map, key, value) {
    /**
     * Push new values to an array mapped
     * to a key.
     *
     * @param Map map
     * @param hashable key
     * @param Object value
     *
     */
     if (map.get(key)) {
         map.get(key).push(value);
     } else {
         map.set(key, [value,]);
     }
}
