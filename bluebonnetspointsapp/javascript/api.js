UserList = (function() {
    var init = function() {
        console.log("Initializing UserList");
    };

    var get_users = function(filter, callback) {
        status_map = {true: 'Active', false: 'Inactive'};

        var params = {
            filter: filter
        };
        var params_str = $.param(params);
        $.get("/api/users?" + params_str, callback);
    };

    return {
        init: init,
        get_users: get_users,
    };
})();

EventList = (function() {
    var init = function() {
        console.log("Initializing EventList");
    };

    var get_events = function(callback) {
        $.get("/api/events", callback);
    };

    return {
        init: init,
        get_events: get_events,
    };
})();


PointCategories = (function() {
    var init = function() {
        console.log("Initializing PointCategories");
    };

    var get_point_categories = function(callback) {
        $.ajax({
            url: "/api/point-categories",
        }).success(callback);
    };

    return {
        init: init,
        get_point_categories: get_point_categories,
    };
})();
