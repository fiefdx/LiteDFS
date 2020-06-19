var $warning_toast = $('#warning_toast');
var $warning_brief = $('#warning_toast #brief_info');
var $warning_detail = $('#warning_toast #detail_info');
var $log_console = $("textarea#log-console");

function logConsole(msg) {
    var log_length = 1000;
    var content = $log_console.val();
    if (content) {
        content += '\n' + msg;
    } else {
        content = msg;
    }
    var lines = content.split("\n");
    if (lines.length > log_length) {
        content = lines.slice(-log_length, lines.length).join("\n");
    }
    $log_console.val(content);
    $log_console.scrollTop($log_console[0].scrollHeight);
}

function showWarningToast(brief_info, detail_info) {
    $warning_brief[0].innerText = brief_info;
    $warning_detail[0].innerText = detail_info;
    $warning_toast.toast('show');
}

function hideWarningToast() {
    $warning_toast.toast('hide');
}

function showWaitScreen() {
    $(".wait_modal").css("display", "block");
}

function hideWaitScreen() {
    $(".wait_modal").css("display", "none");
}

function* dayOfMonthIter() {
    for (var i=0; i<32; i++) {
        if (i == 0) {
            yield '<option selected value="-1">Not Set</option>';
        } else {
            yield '<option value="' + i + '">' + i + '</option>';
        }
    }
}

function* hourIter() {
    for (var i=-1; i<24; i++) {
        if (i == -1) {
            yield '<option selected value="-1">Not Set</option>';
        } else {
            yield '<option value="' + i + '">' + i + '</option>';
        }
    }
}

function* minuteIter() {
    for (var i=-1; i<60; i++) {
        if (i == -1) {
            yield '<option selected value="-1">Not Set</option>';
        } else {
            yield '<option value="' + i + '">' + i + '</option>';
        }
    }
}

function generateSelectList(element_id, iterable_values) {
    var $select = $('select#' + element_id);
    $select.empty();
    for (const value of iterable_values) {
        $select.append(value);
    }
}

function generatePagination(selector, current_page, page_size, size, total) {
    $(selector).empty();
    $(selector).append('<li id="previous-page" class="page-item"><a class="page-link previous-page" href="#"><span aria-hidden="true">&laquo;</span></a></li>');
    for (var i=0; i<size; i++) {
        var d = size - i;
        if (current_page - d >= 1) {
            $(selector).append('<li class="page-item"><a class="page-link page-num" href="#">' + (current_page - d) + '</a></li>');
        }
    }
    $(selector).append('<li class="page-item active"><a class="page-link page-num" href="#">' + current_page + '</a></li>');
    for (var i=0; i<size; i++) {
        var d = i + 1;
        if ((current_page + d) * page_size < total + page_size) {
            $(selector).append('<li class="page-item"><a class="page-link page-num" href="#">' + (current_page + d) + '</a></li>');
        }
    }
    $(selector).append('<li id="next-page" class="page-item"><a class="page-link next-page" href="#"><span aria-hidden="true">&raquo;</span></a></li>');
    if (current_page == 1) {
        $('li#previous-page').addClass('disabled');
    }
    if (total <= page_size || current_page * page_size >= total) {
        $('li#next-page').addClass('disabled');
    }
}

function getHeaderTR(id, title, value) {
    return '<th id="' + id + '" title="' + title + '"><div class="outer"><div class="inner">&nbsp;' + value + '</div></div></th>';
}

function is_in(v, l) {
    for (var i=0; i<l.length; i++) {
        if (v == l[i]) {
            return true;
        }
    }
    return false;
}

function hasVerticalScrollBar(el) {
    var result = el.scrollHeight > el.clientHeight;
    return result;
}

function getBrowserScrollSize() {
    var css = {
        "border":  "none",
        "height":  "200px",
        "margin":  "0",
        "padding": "0",
        "width":   "200px"
    };

    var inner = $("<div>").css($.extend({}, css));
    var outer = $("<div>").css($.extend({
        "left":       "-1000px",
        "overflow":   "scroll",
        "position":   "absolute",
        "top":        "-1000px"
    }, css)).append(inner).appendTo("body")
    .scrollLeft(1000)
    .scrollTop(1000);

    var scrollSize = {
        "height": (outer.offset().top - inner.offset().top) || 0,
        "width": (outer.offset().left - inner.offset().left) || 0
    };

    outer.remove();
    return scrollSize;
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function pathJoin(parts, sep){
    var separator = sep || '/';
    var replace   = new RegExp(separator+'{1,}', 'g');
    return parts.join(separator).replace(replace, separator);
}

function namePathJoin(parts, name, sep){
    var separator = sep || '/';
    var replace   = new RegExp(separator+'{1,}', 'g');
    var clone_parts = [...parts];
    clone_parts.push(name);
    return clone_parts.join(separator).replace(replace, separator);
}
