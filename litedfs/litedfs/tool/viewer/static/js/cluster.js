function clusterInit (manager_host) {
	var $table_header = $(".header-fixed > thead");
    var $table_header_tr = $(".header-fixed > thead > tr");
    var $table_body = $(".header-fixed > tbody");
    var scrollBarSize = getBrowserScrollSize();
    var $btn_refresh = $("#btn_refresh");
    var $btn_manager_detail = $("#btn_manager_detail");
    var cluster_info = {};

    getClusterInfo();
    $btn_refresh.bind('click', refreshPage);
    $btn_manager_detail.bind('click', showManagerInfo);

    function getClusterInfo(node_id) {
        $.ajax({
            dataType: "json",
            url: "http://" + manager_host + "/cluster/info",
            success: function(data) {
                if (data.result != "ok") {
                    showWarningToast("operation failed", data.message);
                }
                $table_header_tr.empty();
                $table_body.empty();
                $table_header_tr.append(getHeaderTR('num', 'num', '#'));
                $table_header_tr.append(getHeaderTR('id', 'id', 'id'));
                $table_header_tr.append(getHeaderTR('node_id', 'node id', 'node id'));
                $table_header_tr.append(getHeaderTR('http_host', 'http host', 'http host'));
                $table_header_tr.append(getHeaderTR('http_port', 'http port', 'http port'));
                $table_header_tr.append(getHeaderTR('version', 'version', 'version'));
                $table_header_tr.append(getHeaderTR('status', 'status', 'status'));
                $table_header_tr.append(getHeaderTR('operation', 'operation', 'operation'));
                var columns = [
                    "num",
                    "id",
                    "node_id",
                    "http_host",
                    "http_port",
                    "version",
                    "status",
                    "operation"
                ];
                cluster_info = {};
                cluster_info["manager"] = {
                    "actions": data.info.actions,
                    "version": data.version
                };
                var item_index = 0;
                data.info.online_nodes.forEach(function (value, index, arrays) {
                    value.status = "online";
                    cluster_info[value["node_id"]] = value;
                    var tr = '<tr id="table_item">';
                    for (var i=0; i<columns.length; i++) {
                        var col = columns[i];
                        if (col == 'num') {
                            tr += '<td id="' + col + '"><div class="outer"><div class="inner">&nbsp;' + (item_index + 1) + '</div></div></td>';
                        } else if (col == 'operation') {
                            tr += '<td id="' + col + '"><div class="outer"><div class="inner">';
                            tr += '<button id="' + value["node_id"] + '" type="button" class="btn btn-secondary btn-sm btn-operation btn-detail" onclick="this.blur();"><span class="oi oi-spreadsheet" title="detail" aria-hidden="true"></span></button>';
                            tr += '</div></div></td>';
                        } else if (col == 'node_id') {
                            tr += '<td id="' + col + '"><div class="outer"><div class="inner"><span class="span-pre">' + value[col] + '</span></div></div></td>';
                        } else {
                            tr += '<td id="' + col + '"><div class="outer"><div class="inner">&nbsp;' + value[col] + '</div></div></td>';
                        }
                    }
                    tr += '</tr>';
                    $table_body.append(tr);
                    item_index += 1;
                });
                data.info.offline_nodes.forEach(function (value, index, arrays) {
                    value.status = "offline";
                    cluster_info[value["node_id"]] = value;
                    var tr = '<tr id="table_item">';
                    for (var i=0; i<columns.length; i++) {
                        var col = columns[i];
                        if (col == 'num') {
                            tr += '<td id="' + col + '"><div class="outer"><div class="inner">&nbsp;' + (item_index + 1) + '</div></div></td>';
                        } else if (col == 'operation') {
                            tr += '<td id="' + col + '"><div class="outer"><div class="inner">';
                            tr += '<button id="' + value["node_id"] + '" type="button" class="btn btn-secondary btn-sm btn-operation btn-detail" onclick="this.blur();"><span class="oi oi-spreadsheet" title="detail" aria-hidden="true"></span></button>';
                            tr += '</div></div></td>';
                        } else if (col == 'node_id') {
                            tr += '<td id="' + col + '"><div class="outer"><div class="inner"><span class="span-pre">' + value[col] + '</span></div></div></td>';
                        } else {
                            tr += '<td id="' + col + '"><div class="outer"><div class="inner">&nbsp;' + value[col] + '</div></div></td>';
                        }
                    }
                    tr += '</tr>';
                    $table_body.append(tr);
                    item_index += 1;
                });

                var tbody = document.getElementById("table_body");
                if (hasVerticalScrollBar(tbody)) {
                    $table_header.css({"margin-right": scrollBarSize.width});
                }
                else {
                    $table_header.css({"margin-right": 0});
                }

                addColumnsCSS(columns);
                $(".btn-detail").bind('click', showNodeDetail);

                if (node_id) {
                    var info = {};
                    if (cluster_info[node_id]) {
                        info = cluster_info[node_id];
                    }
                    document.getElementById("node_info_json").textContent = JSON.stringify(info, undefined, 4);
                }

                document.getElementById("manager_info_json").textContent = JSON.stringify(cluster_info["manager"], undefined, 4);
                $btn_refresh.removeAttr("disabled");
                $('#node_info_refresh').removeAttr("disabled");
            },
            error: function() {
                showWarningToast("error", "request service failed");
                $btn_refresh.removeAttr("disabled");
                $('#node_info_refresh').removeAttr("disabled");
            }
        });
    }

    function showManagerInfo() {
        document.getElementById("manager_info_json").textContent = JSON.stringify(cluster_info["manager"], undefined, 4);
        $('#manager_info_refresh').bind('click', getClusterInfo);
        $('#manager_info_modal').modal('show');
    }

    function refreshPage() {
        $btn_refresh.attr("disabled", "disabled");
        getClusterInfo();
    }

    function refreshNodeInfo(event) {
        $('#node_info_refresh').attr("disabled", "disabled");
        var node_id = event.data.node_id;
        getClusterInfo(node_id);
    }

    function showNodeDetail() {
        var node_id = $(this).attr("id");
        document.getElementById("node_info_json").textContent = JSON.stringify(cluster_info[node_id], undefined, 4);
        $('#node_info_refresh').bind('click', {"node_id": node_id}, refreshNodeInfo);
        $('#node_info_modal').modal('show');
    }

    function addColumnsCSS(keys) {
        var percent = 100.00;
        if (is_in('num', keys)) {
            $('th#num').css("width", "5%");
            $('td#num').css("width", "5%");
            percent -= 5.0;
        }
        if (is_in('id', keys)) {
            $('th#id').css("width", "5%");
            $('td#id').css("width", "5%");
            percent -= 5.0;
        }
        if (is_in('http_host', keys)) {
            $('th#http_host').css("width", "10%");
            $('td#http_host').css("width", "10%");
            percent -= 10.0;
        }
        if (is_in('http_port', keys)) {
            $('th#http_port').css("width", "5%");
            $('td#http_port').css("width", "5%");
            percent -= 5.0;
        }
        if (is_in('version', keys)) {
            $('th#version').css("width", "10%");
            $('td#version').css("width", "10%");
            percent -= 10.0;
        }
        if (is_in('status', keys)) {
            $('th#status').css("width", "10%");
            $('td#status').css("width", "10%");
            percent -= 10.0;
        }
        if (is_in('operation', keys)) {
            $('th#operation').css("width", "8%");
            $('td#operation').css("width", "8%");
            percent -= 8.0;
        }
        if (is_in('node_id', keys)) {
            var width = percent;
            $('th#node_id').css("width", width + "%");
            $('td#node_id').css("width", width + "%");
        }
    }
}