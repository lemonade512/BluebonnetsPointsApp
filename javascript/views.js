PointCategorySelectView = (function() {

    var init = function(el, default_selected) {
        this.el = el;
        this.default_selected = default_selected;
    };

    var render = function(data) {
        $(PointCategorySelectView.el).empty();

        $.each(data, function(key, value) {
            // Add as an option for the select element
            opt_group = $('<optgroup label="' + key + '"></opt-group>');
            $.each(value.sub_categories, function(index, sub_cat) {
                option = $('<option value="' + sub_cat.name + '">' + sub_cat.name + "</option>");
                opt_group.append(option);
            });
            $(PointCategorySelectView.el).append(opt_group);
            $(PointCategorySelectView.el).val(PointCategorySelectView.default_selected);
        });
    };

    return {
        init: init,
        render: render,
    };

})();
