var input_date_range;
var tblCreditNote;

var credit_note = {
    list: function (args = {}) {
        var params = {'action': 'search'};
        if ($.isEmptyObject(args)) {
            params['start_date'] = input_date_range.data('daterangepicker').startDate.format('YYYY-MM-DD');
            params['end_date'] = input_date_range.data('daterangepicker').endDate.format('YYYY-MM-DD');
        } else {
            params = Object.assign({}, params, args);
        }
        tblCreditNote = $('#data').DataTable({
            autoWidth: false,
            destroy: true,
            deferRender: true,
            ajax: {
                url: pathname,
                type: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: params,
                dataSrc: ""
            },
            order: [[0, "desc"], [5, "desc"]],
            columns: [
                {data: "id"},
                {data: "receipt_number_full"},
                {data: "date_joined"},
                {data: "invoice.customer.user.names"},
                {data: "invoice.customer.dni"},
                {data: "status.name"},
                {data: "subtotal"},
                {data: "total_tax"},
                {data: "total_discount"},
                {data: "total_amount"},
                {data: "id"},
            ],
            columnDefs: [
                {
                    targets: [0],
                    type: 'num',
                    class: 'text-center'
                },
                {
                    targets: [1, 2],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return data;
                    }
                },
                {
                    targets: [-6],
                    class: 'text-center',
                    render: function (data, type, row) {
                        var name = row.status.name;
                        switch (row.status.id) {
                            case "without_authorizing":
                                return '<span class="badge rounded-pill bg-warning">' + name + '</span>';
                            case "authorized":
                            case "authorized_and_sent_by_email":
                                return '<span class="badge rounded-pill bg-success">' + name + '</span>';
                            case "sequential_registered_error":
                            case "canceled":
                                return '<span class="badge rounded-pill bg-danger">' + name + '</span>';
                        }
                    }
                },
                {
                    targets: [-7],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return data.toUpperCase();
                    }
                },
                {
                    targets: [-2, -3, -4, -5],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return 'S/' + data.toFixed(2);
                    }
                },
                {
                    targets: [-1],
                    class: 'text-center',
                    orderable: false,
                    render: function (data, type, row) {
                        return '<a rel="detail" data-toggle="tooltip" title="Detalle" class="btn btn-success btn-xs btn-flat"><i class="fas fa-search"></i></a> ';
                    }
                }
            ],
            initComplete: function (settings, json) {
                $(this).wrap('<div class="dataTables_scroll"><div/>');
            }
        });
    }
};

$(function () {
    input_date_range = $('input[name="date_range"]');

    $('#data tbody')
        .off()
        .on('click', 'a[rel="detail"]', function () {
            $('.tooltip').remove();
            var tr = tblCreditNote.cell($(this).closest('td, li')).index();
            var row = tblCreditNote.row(tr.row).data();
            $('#tblProducts').DataTable({
                autoWidth: false,
                destroy: true,
                ajax: {
                    url: pathname,
                    type: 'POST',
                    headers: {
                        'X-CSRFToken': csrftoken
                    },
                    data: {
                        'action': 'search_detail_products',
                        'id': row.id
                    },
                    dataSrc: ""
                },
                columns: [
                    {data: "product.code"},
                    {data: "product.name"},
                    {data: "price"},
                    {data: "quantity"},
                    {data: "total_discount"},
                    {data: "total_amount"},
                ],
                columnDefs: [
                    {
                        targets: [-4],
                        class: 'text-center',
                        render: function (data, type, row) {
                            return 'S/' + data.toFixed(2);
                        }
                    },
                    {
                        targets: [-3],
                        class: 'text-center',
                        render: function (data, type, row) {
                            return data;
                        }
                    },
                    {
                        targets: [-1, -2],
                        class: 'text-center',
                        render: function (data, type, row) {
                            return 'S/' + data.toFixed(2);
                        }
                    }
                ],
                initComplete: function (settings, json) {
                    $(this).wrap('<div class="dataTables_scroll"><div/>');
                }
            });
            $('#myModalDetail').modal('show');
        });

    $('.btnSearchDetail').on('click', function () {
        var row = tblCreditNote.row({selected: true}).data();
        credit_note.searchDetail(row);
    });

    input_date_range
        .daterangepicker({
                language: 'auto',
                startDate: new Date(),
                locale: {
                    format: 'YYYY-MM-DD',
                },
                autoApply: true,
            }
        )
        .on('change.daterangepicker apply.daterangepicker', function (ev, picker) {
            credit_note.list();
        });

    $('.drp-buttons').hide();

    credit_note.list();

    $('.btnSearchAll').on('click', function () {
        credit_note.list({'start_date': '', 'end_date': ''});
    });
});