function storageInit (manager_host) {
	var $table_header = $("#remote-manager > .header-fixed > thead");
    var $table_header_tr = $("#remote-manager > .header-fixed > thead > tr");
    var $table_body = $("#remote-manager > .header-fixed > tbody");
    var $btn_home = $("#remote-manager #btn_home");
    var $btn_parent = $("#remote-manager #btn_parent");
    var $btn_refresh = $("#remote-manager #btn_refresh");
    var $btn_rename = $("#remote-manager #btn_rename");
    var $btn_rename_ok = $("#remote-rename-modal #btn-remote-rename");
    var $btn_create = $("#remote-manager #btn_create");
    var $btn_create_ok = $("#remote-create-modal #btn-remote-create");
    var $btn_download = $("#remote-manager #btn_download");
    var $btn_download_ok = $("#remote-download-modal #btn-remote-download");
    var $btn_cut = $("#remote-manager #btn_cut");
    var $btn_cut_ok = $("#remote-cut-modal #btn-remote-cut");
    var $btn_paste = $("#remote-manager #btn_paste");
    var $btn_paste_ok = $("#remote-paste-modal #btn-remote-paste");
    var $btn_update = $("#remote-manager #btn_update");
    var $btn_update_ok = $("#remote-update-modal #btn-remote-update");
    var $btn_delete = $("#remote-manager #btn_delete");
    var $btn_delete_ok = $("#remote-delete-modal #btn-remote-delete");

    var dir_path = [];
    var home_path = [];
    var dirs = [];
    var files = [];

    var $log_console = $("textarea#log-console");
    var scrollBarSize = getBrowserScrollSize();

    var remote = window.location.host;
    var uri = 'ws://' + remote + '/websocket/remote';

    var WebSocket = window.WebSocket || window.MozWebSocket;
    if (WebSocket) {
        try {
            var socket = new WebSocket(uri);
        } catch (e) {}
    }

    if (socket) {
        socket.onopen = function() {
            $btn_home.bind('click', goHomeDir);
            $btn_parent.bind('click', goParentDir);
            $btn_refresh.bind('click', refreshDir);
            $btn_rename.bind('click', showRename);
            $btn_rename_ok.bind('click', renameFileDir);
            $btn_create.bind('click', showCreateDir);
            $btn_create_ok.bind('click', createDir);
            $btn_delete.bind('click', showDelete);
            $btn_delete_ok.bind('click', deleteFileDir);
            $btn_download.bind('click', showDownload);
            $btn_download_ok.bind('click', downloadFileDir);
            $btn_cut.bind('click', showCut);
            $btn_cut_ok.bind('click', cutFileDir);
            $btn_paste.bind('click', showPaste);
            $btn_paste_ok.bind('click', pasteFileDir);

            $btn_paste.attr("disabled", true);

            $("#remote-rename-modal").on("hidden.bs.modal", resetModal);
            $("#remote-create-modal").on("hidden.bs.modal", resetModal);
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
                $btn_paste.attr("disabled", false);
            }
        };

        socket.onclose = function() {
            $log_console.val($log_console.val() + '\nError: Lost connection, please, refresh page!');
            $log_console.scrollTop($log_console[0].scrollHeight);
        };
    }

    function getStorageList(data) {
        $table_header_tr.empty();
        $table_body.empty();
        $('#remote-manager input.dir-path').val(pathJoin(data.dir_path));
        $table_header_tr.append(getHeaderTR('num', 'num', '#'));
        $table_header_tr.append(getHeaderTR('name', 'name', 'name'));
        $table_header_tr.append(getHeaderTR('type', 'type', 'type'));
        $table_header_tr.append(getHeaderTR('size', 'size', 'size'));
        $table_header_tr.append(getHeaderTR('ctime', 'create at', 'create at'));
        $table_header_tr.append(getHeaderTR('mtime', 'update at', 'update at'));
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
            $table_body.append(tr);
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
            $table_body.append(tr);
        });
        files = data.files;

        dir_path = data.dir_path;
        home_path = data.home_path;
        $("#remote-manager a.dir-item").bind('click', openDir);
        $("#remote-manager input[type=checkbox][name=dir]").bind('click', inputSelect);
        $("#remote-manager input[type=checkbox][name=file]").bind('click', inputSelect);

        var tbody = document.getElementById("remote_table_body");
        if (hasVerticalScrollBar(tbody)) {
            $table_header.css({"margin-right": scrollBarSize.width});
        }
        else {
            $table_header.css({"margin-right": 0});
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
        $('#remote-create-modal').modal('show');
    }

    function createDir() {
        $('#remote-create-modal').modal('hide');
        var name = $("#remote-create-modal input.name").val();
        var data = {};
        data.cmd = "mkdir";
        data.name = name;
        data.dir_path = dir_path;
        socket.send(JSON.stringify(data));
    }

    function showRename() {
        var num = Number($("#remote-manager input[type=checkbox]:checked").attr("id").split("_")[1]);
        var type = $("#remote-manager input[type=checkbox]:checked").attr("id").split("_")[0];
        var file_name = "";
        if (type == "dir") {
            file_name = dirs[num].name;
        } else if (type == "file") {
            file_name = files[num].name;
        }
        $('#remote-rename-modal input.new-name').val(file_name);
        $('#remote-rename-modal').modal('show');
    }

    function renameFileDir() {
        $('#remote-rename-modal').modal('hide');
        var num = Number($("#remote-manager input[type=checkbox]:checked").attr("id").split("_")[1]);
        var type = $("#remote-manager input[type=checkbox]:checked").attr("id").split("_")[0];
        var old_name = "";
        if (type == "dir") {
            old_name = dirs[num].name;
        } else if (type == "file") {
            old_name = files[num].name;
        }
        var new_name = $("#remote-rename-modal input.new-name").val();
        var data = {};
        data.cmd = "rename";
        data.old_name = old_name;
        data.new_name = new_name;
        data.dir_path = dir_path;
        socket.send(JSON.stringify(data));
    }

    function showDelete() {
        $('#remote-delete-modal').modal('show');
    }

    function deleteFileDir() {
        $('#remote-delete-modal').modal('hide');
        var delete_dirs = [];
        var delete_files = [];
        var data = {}
        $("#remote-manager input[type=checkbox][name=dir]:checked").each(function () {
            var num = Number($(this).attr("id").split("_")[1])
            delete_dirs.push({"name":dirs[num].name, "sha1":dirs[num].sha1});
        });
        $("#remote-manager input[type=checkbox][name=file]:checked").each(function () {
            var num = Number($(this).attr("id").split("_")[1])
            delete_files.push({"name":files[num].name, "sha1":files[num].sha1});
        });
        data.cmd = "delete";
        data.dirs = delete_dirs;
        data.files = delete_files;
        data.dir_path = dir_path;
        socket.send(JSON.stringify(data));
    }

    function showDownload() {
        $('#remote-download-modal').modal('show');
    }

    function downloadFileDir() {
        $('#remote-download-modal').modal('hide');
        var download_dirs = [];
        var download_files = [];
        var data = {}
        $("#remote-manager input[type=checkbox][name=dir]:checked").each(function () {
            var num = Number($(this).attr("id").split("_")[1])
            download_dirs.push({"name":dirs[num].name, "sha1":dirs[num].sha1});
        });
        $("#remote-manager input[type=checkbox][name=file]:checked").each(function () {
            var num = Number($(this).attr("id").split("_")[1])
            download_files.push({"name":files[num].name, "sha1":files[num].sha1});
        });
        data.cmd = "download";
        data.dirs = download_dirs;
        data.files = download_files;
        data.remote_path = $('#remote-manager input.dir-path').val();;
        data.local_path = $('#local-manager input.dir-path').val();
        socket.send(JSON.stringify(data));
    }

    function showCut() {
        $('#remote-cut-modal').modal('show');
    }

    function cutFileDir() {
        $('#remote-cut-modal').modal('hide');
        var cut_dirs = [];
        var cut_files = [];
        var data = {}
        $("#remote-manager input[type=checkbox][name=dir]:checked").each(function () {
            var num = Number($(this).attr("id").split("_")[1])
            cut_dirs.push({"name":dirs[num].name, "sha1":dirs[num].sha1});
        });
        $("#remote-manager input[type=checkbox][name=file]:checked").each(function () {
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
        $('#remote-paste-modal').modal('show');
    }

    function pasteFileDir() {
        $('#remote-paste-modal').modal('hide');
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
        $("#remote-manager input[type=checkbox][name=dir]:checked").each(function () {
            num_dir++;
        });
        $("#remote-manager input[type=checkbox][name=file]:checked").each(function () {
            num_file++;
        });
        if (num_file == 1 && num_dir == 0) {
            $btn_rename.attr("disabled", false);
            $btn_create.attr("disabled", true);
            $btn_download.attr("disabled", false);
            // $btn_paste.attr("disabled", false);
            $btn_update.attr("disabled", false);
            $btn_cut.attr("disabled", false);
            $btn_delete.attr("disabled", false);
            
        }
        else if (num_file > 1) {
            $btn_rename.attr("disabled", true);
            $btn_create.attr("disabled", true);
            $btn_download.attr("disabled", false);
            // $btn_paste.attr("disabled", false);
            $btn_update.attr("disabled", true);
            $btn_cut.attr("disabled", false);
            $btn_delete.attr("disabled", false);
        }
        else if (num_file == 0 && num_dir == 1) {
            $btn_rename.attr("disabled", false);
            $btn_create.attr("disabled", true);
            $btn_download.attr("disabled", false);
            // $btn_paste.attr("disabled", false);
            $btn_update.attr("disabled", true);
            $btn_cut.attr("disabled", false);
            $btn_delete.attr("disabled", false);
        }
        else if (num_file == 0 && num_dir == 0) {
            $btn_rename.attr("disabled", true);
            $btn_create.attr("disabled", false);
            $btn_download.attr("disabled", true);
            // $btn_paste.attr("disabled", false);
            $btn_update.attr("disabled", true);
            $btn_cut.attr("disabled", true);
            $btn_delete.attr("disabled", true);
        }
        else { // multiple dirs
            $btn_rename.attr("disabled", true);
            $btn_create.attr("disabled", true);
            $btn_download.attr("disabled", false);
            // $btn_paste.attr("disabled", false);
            $btn_update.attr("disabled", true);
            $btn_cut.attr("disabled", false);
            $btn_delete.attr("disabled", false);
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