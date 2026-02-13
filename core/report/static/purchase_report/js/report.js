var input_date_range;
var tblReport;
var columns = [];
var report = {
    initTable: function () {
        tblReport = $('#tblReport').DataTable({
            autoWidth: false,
            destroy: true,
        });
        tblReport.settings()[0].aoColumns.forEach(function (value, index, array) {
            columns.push(value.sWidthOrig);
        });
    },
    list: function (args = {}) {
        var params = {'action': 'search'};
        if ($.isEmptyObject(args)) {
            params['start_date'] = input_date_range.data('daterangepicker').startDate.format('YYYY-MM-DD');
            params['end_date'] = input_date_range.data('daterangepicker').endDate.format('YYYY-MM-DD');
        } else {
            params = Object.assign({}, params, args);
        }
        tblReport = $('#tblReport').DataTable({
            destroy: true,
            autoWidth: false,
            ajax: {
                url: pathname,
                type: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: params,
                dataSrc: ''
            },
            order: [[0, 'asc']],
            paging: true,
            ordering: true,
            searching: true,
            dom: 'Bfrtip',
            buttons: [
                {
                    extend: 'excelHtml5',
                    text: ' <i class="fas fa-file-excel"></i> Descargar Excel',
                    titleAttr: 'Excel',
                    className: 'btn btn-success btn-flat btn-sm',
                    footer: true
                },
                {
                    extend: 'pdfHtml5',
                    text: '<i class="fas fa-file-pdf"></i> Descargar Pdf',
                    titleAttr: 'PDF',
                    className: 'btn btn-danger btn-flat btn-sm',
                    download: 'open',
                    orientation: 'landscape',
                    pageSize: 'LEGAL',
                    customize: function (doc) {
                        doc.styles = {
                            header: {
                                fontSize: 18,
                                bold: true,
                                alignment: 'center'
                            },
                            subheader: {
                                fontSize: 13,
                                bold: true
                            },
                            quote: {
                                italics: true
                            },
                            small: {
                                fontSize: 8
                            },
                            tableHeader: {
                                bold: true,
                                fontSize: 11,
                                color: 'white',
                                fillColor: '#2d4154',
                                alignment: 'center'
                            }
                        };
                        var total_footer = $('#tblReport tfoot th:last').text();
                        var footerRow = [
                            { text: 'Total FinalL:', colSpan: 8, alignment: 'right', bold: true, fillColor: '#f1f1f1' },
                            {}, {}, {}, {}, {}, {}, {},// Celdas vacías por el colSpan
                            { text: total_footer, alignment: 'center', bold: true, fillColor: '#f1f1f1' }
                        ];
                        doc.content[1].table.body.push(footerRow);
                        doc.content[1].table.widths = columns;
                        doc.content[1].margin = [0, 35, 0, 0];
                        doc.content[1].layout = {};
                        doc['footer'] = (function (page, pages) {
                            return {
                                columns: [
                                    {
                                        alignment: 'left',
                                        text: ['Fecha de creación: ', {text: new moment().format('YYYY-MM-DD')}]
                                    },
                                    {
                                        alignment: 'right',
                                        text: ['página ', {text: page.toString()}, ' de ', {text: pages.toString()}]
                                    }
                                ],
                                margin: 20
                            }
                        });

                    }
                }
            ],
            columns: [
                {data: "number"},
                {data: "date_joined"},
                {data: "provider.name"},
                {data: "provider.ruc"},
                {data: "payment_type.name"},
                {data: "subtotal"},
                {data: "total_tax"},
                {data: "total_discount"},
                {data: "total_amount"},
            ],
            columnDefs: [
                {
                    targets: [-5, -6, -7],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return data;
                    }
                },
                {
                    targets: [-1, -2, -3, -4],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return 'S/' + data.toFixed(2);
                    }
                }
            ],
            fnFooterCallback: function (row, data, start, end, display) {
                var api = this.api();

                var intVal = function (i) {
                    return typeof i === 'string' ? i.replace(/[\$,]/g, '') * 1 : typeof i === 'number' ? i : 0;
                };

                var total = api
                .column(8, { search: 'applied' })
                .data()
                .reduce(function (a, b) {
                    return intVal(a) + intVal(b);
                }, 0);

                $(api.column(8).footer()).html(
                    'S/' + total.toFixed(2)
                );
                
            },
            rowCallback: function (row, data, index) {

            },
            initComplete: function (settings, json) {
                $(this).wrap('<div class="dataTables_scroll"><div/>');
            }
        });
    }
};

$(function () {
    input_date_range = $('input[name="date_range"]');

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
            report.list();
        });

    $('.drp-buttons').hide();

    report.initTable();

    report.list();

    $('.btnSearchAll').on('click', function () {
        report.list({'start_date': '', 'end_date': ''});
    });
});