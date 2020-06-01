function storageInit (manager_host) {
	var $table_header = $(".header-fixed > thead");
    var $table_header_tr = $(".header-fixed > thead > tr");
    var $table_body = $(".header-fixed > tbody");
    var scrollBarSize = getBrowserScrollSize();
    var $btn_refresh = $("#btn_refresh");
    var $btn_create = $("#btn_create");

    var local = window.location.host;
    var uri = 'ws://' + local + '/websocket';
    console.log('Uri: ' + uri)

    var WebSocket = window.WebSocket || window.MozWebSocket;
    if (WebSocket) {
        try {
            var socket = new WebSocket(uri);
        } catch (e) {}
    }

    if (socket) {
        socket.onopen = function() {
            console.log("websocket onopen");
        };

        socket.onmessage = function(msg) {
            var data = JSON.parse(msg.data);
            console.log(data);
            socket.send(JSON.stringify(data));
        };

        socket.onclose = function() {
            console.log("websocket onclose");
        };
    }
}