function storageInit (manager_host) {
	var $local_table_header = $("#local-manager > .header-fixed > thead");
    var $local_table_header_tr = $("#local-manager > .header-fixed > thead > tr");
    var $local_table_body = $("#local-manager > .header-fixed > tbody");
    var $local_btn_home = $("#local-manager #btn_home");
    var $local_btn_parent = $("#local-manager #btn_parent");
    var $local_btn_refresh = $("#local-manager #btn_refresh");
    var $local_btn_rename = $("#local-manager #btn_rename");
    var $local_btn_rename_ok = $("#local-rename-modal #btn-local-rename");
    var $local_btn_create = $("#local-manager #btn_create");
    var $local_btn_create_ok = $("#local-create-modal #btn-local-create");
    var $local_btn_upload = $("#local-manager #btn_upload");
    var $local_btn_copy = $("#local-manager #btn_copy");
    var $local_btn_copy_ok = $("#local-copy-modal #btn-local-copy");
    var $local_btn_cut = $("#local-manager #btn_cut");
    var $local_btn_cut_ok = $("#local-cut-modal #btn-local-cut");
    var $local_btn_paste = $("#local-manager #btn_paste");
    var $local_btn_paste_ok = $("#local-paste-modal #btn-local-paste");
    var $local_btn_delete = $("#local-manager #btn_delete");
    var $local_btn_delete_ok = $("#local-delete-modal #btn-local-delete");

    var $remote_table_header = $("#remote-manager > .header-fixed > thead");
    var $remote_table_header_tr = $("#remote-manager > .header-fixed > thead > tr");
    var $remote_table_body = $("#remote-manager > .header-fixed > tbody");

    var $log_console = $("textarea#log-console");
    var scrollBarSize = getBrowserScrollSize();

    var local = window.location.host;
    var uri = 'ws://' + local + '/websocket';

    var dir_path = [];
    var home_path = [];
    var dirs = [];
    var files = [];

    var WebSocket = window.WebSocket || window.MozWebSocket;
    if (WebSocket) {
        try {
            var socket = new WebSocket(uri);
        } catch (e) {}
    }

    if (socket) {
        socket.onopen = function() {
            $local_btn_home.bind('click', goHomeDir);
            $local_btn_parent.bind('click', goParentDir);
            $local_btn_refresh.bind('click', refreshDir);
            $local_btn_rename.bind('click', showRename);
            $local_btn_rename_ok.bind('click', renameFileDir);
            $local_btn_create.bind('click', showCreateDir);
            $local_btn_create_ok.bind('click', createDir);
            $local_btn_delete.bind('click', showDelete);
            $local_btn_delete_ok.bind('click', deleteFileDir);
            $local_btn_copy.bind('click', showCopy);
            $local_btn_copy_ok.bind('click', copyFileDir);
            $local_btn_cut.bind('click', showCut);
            $local_btn_cut_ok.bind('click', cutFileDir);
            $local_btn_paste.bind('click', showPaste);
            $local_btn_paste_ok.bind('click', pasteFileDir);

            $local_btn_paste.attr("disabled", true);

            $("#local-rename-modal").on("hidden.bs.modal", resetModal);
            $("#local-create-modal").on("hidden.bs.modal", resetModal);
        };

        socket.onmessage = function(msg) {
            var data = JSON.parse(msg.data);

            if (data.cmd == "init") {
                getStorageList(data);
            } else if (data.cmd == "info") {
                $log_console.val($log_console.val() + '\nInfo: ' + data.info);
                $log_console.scrollTop($log_console[0].scrollHeight);
            } else if (data.cmd == "warning") {
                $log_console.val($log_console.val() + '\nWarning: ' + data.info);
                $log_console.scrollTop($log_console[0].scrollHeight);
            } else if (data.cmd == "error") {
                $log_console.val($log_console.val() + '\nError: ' + data.info);
                $log_console.scrollTop($log_console[0].scrollHeight);
            } else if (data.cmd == "paste") {
                $local_btn_paste.attr("disabled", false);
            }

            socket.send(JSON.stringify(data));
        };

        socket.onclose = function() {
            $log_console.val($log_console.val() + '\nError: Lost connection, please, refresh page!');
            $log_console.scrollTop($log_console[0].scrollHeight);
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
                    tr += '<input class="dir-item" name="dir" type="checkbox" id="dir_' + index + '">';
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
        dirs = data.dirs;
        data.files.forEach(function (value, index, arrays) {
            var tr = '<tr id="table_item">';
            for (var i=0; i<columns.length; i++) {
                var col = columns[i];
                if (col == 'name') {
                    tr += '<td id="' + col + '" title="' + value[col] + '">';
                    tr += '<div class="outer">';
                    tr += '<div class="inner">';
                    tr += '<span>';
                    tr += '<input class="file-item" name="file" type="checkbox" id="file_' + index + '">';
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
        files = data.files;

        dir_path = data.dir_path;
        home_path = data.home_path;
        $("#local-manager a.dir-item").bind('click', openDir);
        $("#local-manager input[type=checkbox][name=dir]").bind('click', inputSelect);
        $("#local-manager input[type=checkbox][name=file]").bind('click', inputSelect);

        var tbody = document.getElementById("local_table_body");
        if (hasVerticalScrollBar(tbody)) {
            $local_table_header.css({"margin-right": scrollBarSize.width});
        }
        else {
            $local_table_header.css({"margin-right": 0});
        }

        addColumnsCSS(columns);
        $("a.dir-item").css("cursor", "pointer");

        checkSelect();
    }

    function goHomeDir() {
        var data = {};
        data.cmd = "cd";
        data.dir_path = home_path;
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
        socket.send(JSON.stringify(data));
    }

    function refreshDir() {
        var data = {};
        data.cmd = "refresh";
        data.dir_path = dir_path;
        socket.send(JSON.stringify(data));
    }

    function openDir(event) {
        var dir_name = $(this).attr("id");
        var data = {};
        data.cmd = "cd";
        dir_path.push(dir_name);
        data.dir_path = dir_path;
        socket.send(JSON.stringify(data));
        event.stopPropagation()
    }

    function showCreateDir() {
        $('#local-create-modal').modal('show');
    }

    function createDir() {
        $('#local-create-modal').modal('hide');
        var name = $("#local-create-modal input#name").val();
        var data = {};
        data.cmd = "mkdir";
        data.name = name;
        data.dir_path = dir_path;
        socket.send(JSON.stringify(data));
    }

    function showRename() {
        var num = Number($("#local-manager input[type=checkbox]:checked").attr("id").split("_")[1]);
        var type = $("#local-manager input[type=checkbox]:checked").attr("id").split("_")[0];
        var file_name = "";
        if (type == "dir") {
            file_name = dirs[num].name;
        } else if (type == "file") {
            file_name = files[num].name;
        }
        $('#local-rename-modal input#new_name').val(file_name);
        $('#local-rename-modal').modal('show');
    }

    function renameFileDir() {
        $('#local-rename-modal').modal('hide');
        var num = Number($("#local-manager input[type=checkbox]:checked").attr("id").split("_")[1]);
        var type = $("#local-manager input[type=checkbox]:checked").attr("id").split("_")[0];
        var old_name = "";
        if (type == "dir") {
            old_name = dirs[num].name;
        } else if (type == "file") {
            old_name = files[num].name;
        }
        var new_name = $("#local-rename-modal input#new_name").val();
        var data = {};
        data.cmd = "rename";
        data.old_name = old_name;
        data.new_name = new_name;
        data.dir_path = dir_path;
        socket.send(JSON.stringify(data));
    }

    function showDelete() {
        $('#local-delete-modal').modal('show');
    }

    function deleteFileDir() {
        $('#local-delete-modal').modal('hide');
        var delete_dirs = [];
        var delete_files = [];
        var data = {}
        $("#local-manager input[type=checkbox][name=dir]:checked").each(function () {
            var num = Number($(this).attr("id").split("_")[1])
            delete_dirs.push({"name":dirs[num].name, "sha1":dirs[num].sha1});
        });
        $("#local-manager input[type=checkbox][name=file]:checked").each(function () {
            var num = Number($(this).attr("id").split("_")[1])
            delete_files.push({"name":files[num].name, "sha1":files[num].sha1});
        });
        data.cmd = "delete";
        data.dirs = delete_dirs;
        data.files = delete_files;
        data.dir_path = dir_path;
        socket.send(JSON.stringify(data));
    }

    function showCopy() {
        $('#local-copy-modal').modal('show');
    }

    function copyFileDir() {
        $('#local-copy-modal').modal('hide');
        var copy_dirs = [];
        var copy_files = [];
        var data = {}
        $("#local-manager input[type=checkbox][name=dir]:checked").each(function () {
            var num = Number($(this).attr("id").split("_")[1])
            copy_dirs.push({"name":dirs[num].name, "sha1":dirs[num].sha1});
        });
        $("#local-manager input[type=checkbox][name=file]:checked").each(function () {
            var num = Number($(this).attr("id").split("_")[1])
            copy_files.push({"name":files[num].name, "sha1":files[num].sha1});
        });
        data.cmd = "copy";
        data.dirs = copy_dirs;
        data.files = copy_files;
        data.dir_path = dir_path;
        socket.send(JSON.stringify(data));
    }

    function showCut() {
        $('#local-cut-modal').modal('show');
    }

    function cutFileDir() {
        $('#local-cut-modal').modal('hide');
        var cut_dirs = [];
        var cut_files = [];
        var data = {}
        $("#local-manager input[type=checkbox][name=dir]:checked").each(function () {
            var num = Number($(this).attr("id").split("_")[1])
            cut_dirs.push({"name":dirs[num].name, "sha1":dirs[num].sha1});
        });
        $("#local-manager input[type=checkbox][name=file]:checked").each(function () {
            var num = Number($(this).attr("id").split("_")[1])
            cut_files.push({"name":files[num].name, "sha1":files[num].sha1});
        });
        data.cmd = "cut";
        data.dirs = cut_dirs;
        data.files = cut_files;
        data.dir_path = dir_path;
        socket.send(JSON.stringify(data));
    }

    function showPaste() {
        $('#local-paste-modal').modal('show');
    }

    function pasteFileDir() {
        $('#local-paste-modal').modal('hide');
        var data = {}
        data.cmd = "paste";
        data.dir_path = dir_path;
        socket.send(JSON.stringify(data));
    }

    function inputSelect(event) {
        if (this.checked) {
            $(this).parent("span").parent("div").parent("div").parent("td").parent("tr").addClass("success");
        } else {
            $(this).parent("span").parent("div").parent("div").parent("td").parent("tr").removeClass("success");
        }
        checkSelect();
        event.stopPropagation()
    }

    function checkSelect(event) {
        var num_dir = 0;
        var num_file = 0;
        $("#local-manager input[type=checkbox][name=dir]:checked").each(function () {
            num_dir++;
        });
        $("#local-manager input[type=checkbox][name=file]:checked").each(function () {
            num_file++;
        });
        if (num_file == 1 && num_dir == 0) {
            $local_btn_rename.attr("disabled", false);
            $local_btn_create.attr("disabled", true);
            $local_btn_upload.attr("disabled", false);
            // $local_btn_paste.attr("disabled", false);
            $local_btn_copy.attr("disabled", false);
            $local_btn_cut.attr("disabled", false);
            $local_btn_delete.attr("disabled", false);
            
        }
        else if (num_file > 1) {
            $local_btn_rename.attr("disabled", true);
            $local_btn_create.attr("disabled", true);
            $local_btn_upload.attr("disabled", false);
            // $local_btn_paste.attr("disabled", false);
            $local_btn_copy.attr("disabled", false);
            $local_btn_cut.attr("disabled", false);
            $local_btn_delete.attr("disabled", false);
        }
        else if (num_file == 0 && num_dir == 1) {
            $local_btn_rename.attr("disabled", false);
            $local_btn_create.attr("disabled", true);
            $local_btn_upload.attr("disabled", false);
            // $local_btn_paste.attr("disabled", false);
            $local_btn_copy.attr("disabled", false);
            $local_btn_cut.attr("disabled", false);
            $local_btn_delete.attr("disabled", false);
        }
        else if (num_file == 0 && num_dir == 0) {
            $local_btn_rename.attr("disabled", true);
            $local_btn_create.attr("disabled", false);
            $local_btn_upload.attr("disabled", true);
            // $local_btn_paste.attr("disabled", false);
            $local_btn_copy.attr("disabled", true);
            $local_btn_cut.attr("disabled", true);
            $local_btn_delete.attr("disabled", true);
        }
        else { // multiple dirs
            $local_btn_rename.attr("disabled", true);
            $local_btn_create.attr("disabled", true);
            $local_btn_upload.attr("disabled", false);
            // $local_btn_paste.attr("disabled", false);
            $local_btn_copy.attr("disabled", false);
            $local_btn_cut.attr("disabled", false);
            $local_btn_delete.attr("disabled", false);
        }
        if (event){
            event.stopPropagation()
        }
    }

    function resetModal(e) {
        $("#" + e.target.id).find("input:text").val("");
        $("#" + e.target.id).find("input:file").val(null);
        $("#" + e.target.id).find(".custom-file-label").html("Choose file");
        $("#" + e.target.id).find("textarea").val("");
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