function storageInit (manager_host) {
	var $local_table_header = $("#local-manager > .header-fixed > thead");
    var $local_table_header_tr = $("#local-manager > .header-fixed > thead > tr");
    var $local_table_body = $("#local-manager > .header-fixed > tbody");
    var $local_btn_home = $("#local-manager >> #btn_home");
    var $local_btn_parent = $("#local-manager >> #btn_parent");
    var $local_btn_refresh = $("#local-manager >> #btn_refresh");

    var $remote_table_header = $("#remote-manager > .header-fixed > thead");
    var $remote_table_header_tr = $("#remote-manager > .header-fixed > thead > tr");
    var $remote_table_body = $("#remote-manager > .header-fixed > tbody");
    var scrollBarSize = getBrowserScrollSize();

    var local = window.location.host;
    var uri = 'ws://' + local + '/websocket';
    console.log('Uri: ' + uri)

    var dir_path = [];
    var home_path = [];

    var WebSocket = window.WebSocket || window.MozWebSocket;
    if (WebSocket) {
        try {
            var socket = new WebSocket(uri);
        } catch (e) {}
    }

    if (socket) {
        socket.onopen = function() {
            console.log("websocket onopen");
            $local_btn_home.bind('click', goHomeDir);
            $local_btn_parent.bind('click', goParentDir);
            $local_btn_refresh.bind('click', refreshDir);
        };

        socket.onmessage = function(msg) {
            var data = JSON.parse(msg.data);
            console.log(data);

            if (data.cmd == "init") {
                getStorageList(data);
            }

            socket.send(JSON.stringify(data));
        };

        socket.onclose = function() {
            console.log("websocket onclose");
        };
    }

    function getStorageList(data) {
        $local_table_header_tr.empty();
        $local_table_body.empty();
        $('#local-manager input#dir-path').val(pathJoin(data.dir_path));
        $local_table_header_tr.append(getHeaderTR('num', 'num', '#'));
        $local_table_header_tr.append(getHeaderTR('name', 'name', 'name'));
        $local_table_header_tr.append(getHeaderTR('type', 'type', 'type'));
        $local_table_header_tr.append(getHeaderTR('size', 'size', 'size'));
        $local_table_header_tr.append(getHeaderTR('ctime', 'create at', 'create at'));
        $local_table_header_tr.append(getHeaderTR('mtime', 'update at', 'update at'));
        var columns = [
            "num",
            "name",
            "type",
            "size",
            "ctime",
            "mtime"
        ];
        data.dirs.forEach(function (value, index, arrays) {
            var tr = '<tr id="table_item">';
            for (var i=0; i<columns.length; i++) {
                var col = columns[i];
                if (col == 'name') {
                    tr += '<td id="' + col + '" title="' + value[col] + '">';
                    tr += '<div class="outer">';
                    tr += '<div class="inner">';
                    tr += '<span>';
                    tr += '<input class="dir-item" type="checkbox" id="dir_' + value[col] + '">';
                    tr += '</span>&nbsp;';
                    tr += '<span class="oi oi-folder" aria-hidden="true">';
                    tr += '</span>'
                    tr += '<a class="dir-item" id="' + value[col] + '">&nbsp;' + value[col] + '</a>';
                    tr += '</div>';
                    tr += '</div>';
                    tr += '</td>';
                } else {
                    tr += '<td id="' + col + '"><div class="outer"><div class="inner">&nbsp;' + value[col] + '</div></div></td>';
                }
            }
            tr += '</tr>';
            $local_table_body.append(tr);
        });
        data.files.forEach(function (value, index, arrays) {
            var tr = '<tr id="table_item">';
            for (var i=0; i<columns.length; i++) {
                var col = columns[i];
                if (col == 'name') {
                    tr += '<td id="' + col + '" title="' + value[col] + '">';
                    tr += '<div class="outer">';
                    tr += '<div class="inner">';
                    tr += '<span>';
                    tr += '<input class="file-item" type="checkbox" id="file_' + value[col] + '">';
                    tr += '</span>&nbsp;';
                    tr += '<span class="oi oi-file" aria-hidden="true">';
                    tr += '</span>'
                    tr += '<span>';
                    tr += '&nbsp;' + value[col];
                    tr += '</span>'
                    tr += '</div>';
                    tr += '</div>';
                    tr += '</td>';
                } else {
                    tr += '<td id="' + col + '"><div class="outer"><div class="inner">&nbsp;' + value[col] + '</div></div></td>';
                }
            }
            tr += '</tr>';
            $local_table_body.append(tr);
        });

        dir_path = data.dir_path;
        home_path = data.home_path;
        $("a.dir-item").bind('click', openDir);

        var tbody = document.getElementById("local_table_body");
        if (hasVerticalScrollBar(tbody)) {
            $local_table_header.css({"margin-right": scrollBarSize.width});
        }
        else {
            $local_table_header.css({"margin-right": 0});
        }

        addColumnsCSS(columns);
        $("a.dir-item").css("cursor", "pointer");
    }

    function goHomeDir() {
        var data = {};
        data.cmd = "cd";
        data.dir_path = home_path;
        console.log(data);
        socket.send(JSON.stringify(data));
    }

    function goParentDir() {
        var index = dir_path.length - 1;
        var data = {};
        data.cmd = "cd";
        if (index == 0) {
            index = 1;
        }
        data.dir_path = dir_path.slice(0, index);
        console.log(data);
        socket.send(JSON.stringify(data));
    }

    function refreshDir() {
        var data = {};
        data.cmd = "refresh";
        data.dir_path = dir_path;
        console.log(data);
        socket.send(JSON.stringify(data));
    }

    function openDir(event) {
        var dir_name = $(this).attr("id");
        console.log("dir_name: " + dir_name);
        var data = {};
        data.cmd = "cd";
        dir_path.push(dir_name);
        data.dir_path = dir_path;
        console.log(data);
        socket.send(JSON.stringify(data));
        event.stopPropagation()
    }

    function addColumnsCSS(keys) {
        var percent = 100.00;
        if (is_in('num', keys)) {
            $('th#num').css("width", "5%");
            $('td#num').css("width", "5%");
            percent -= 5.0;
        }
        if (is_in('create_at', keys)) {
            $('th#create_at').css("width", "10%");
            $('td#create_at').css("width", "10%");
            percent -= 10.0;
        }
        if (is_in('update_at', keys)) {
            $('th#update_at').css("width", "10%");
            $('td#update_at').css("width", "10%");
            percent -= 10.0;
        }
        if (is_in('type', keys)) {
            $('th#type').css("width", "5%");
            $('td#type').css("width", "5%");
            percent -= 5.0;
        }
        if (is_in('size', keys)) {
            $('th#size').css("width", "8%");
            $('td#size').css("width", "8%");
            percent -= 8.0;
        }
        if (is_in('name', keys)) {
            var width = percent;
            $('th#name').css("width", width + "%");
            $('td#name').css("width", width + "%");
        }
    }
}