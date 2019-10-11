$('#expandNest').change(function(){
    let url = new URL(document.location);
    let params = new URLSearchParams(url.search);
    let val = params.has('expand_nests') ? parseInt(params.get('expand_nests')) : 0
    new_val = ~val & 1;
    params.set('expand_nests', new_val);
    url.search = params;
    document.location.assign(url);
    return false;
})
