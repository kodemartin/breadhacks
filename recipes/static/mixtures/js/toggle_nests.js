$('#expandNest').change(function(){
    collapsed = $('.m-collapsed');
    expanded = $('.m-expanded');
    if (collapsed.hasClass('hidden')) {
        collapsed.removeClass('hidden');
        expanded.addClass('hidden');
    } else {
        collapsed.addClass('hidden');
        expanded.removeClass('hidden');
    }
    return false;
})
