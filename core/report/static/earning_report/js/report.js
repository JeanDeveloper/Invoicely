var select_product;
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

    list: function () {
        var params = {
            'action': 'search',
            'product_id': JSON.stringify(select_product.select2('data').map(value => value.id)),
        };
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
            paging: false,
            ordering: true,
            searching: false,
            dom: 'Bfrtip',
            buttons: [
                {
                    extend: 'excelHtml5',
                    text: 'Descargar Excel <i class="fas fa-file-excel"></i>',
                    titleAttr: 'Excel',
                    className: 'btn btn-success btn-xs btn-flat',
                    footer:true
                },
                {
                    extend: 'pdfHtml5',
                    text: 'Descargar Pdf <i class="fas fa-file-pdf"></i>',
                    titleAttr: 'PDF',
                    className: 'btn btn-danger btn-xs btn-flat',
                    download: 'open',
                    orientation: 'landscape',
                    pageSize: 'LEGAL',
                    exportOptions: {
                        columns: [0, 1, 2, 3, 4, 5],
                        footer: true
                    },
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
                            { text: 'Total Final:', colSpan: 5, alignment: 'right', bold: true, fillColor: '#f1f1f1' },
                            {}, {}, {}, {},
                            { text: total_footer, alignment: 'center', bold: true, fillColor: '#f1f1f1' }
                        ];
                        doc.content[1].table.body.push(footerRow);
                        doc.content[1].table.widths = ['*', '*', '*', '*', '*', '*'];

                        var rowCount = doc.content[1].table.body.length;
                        for (var i = 0; i < rowCount; i++) {
                            for (var j = 0; j < 6; j++) {
                                // SOLUCIÓN: Solo aplicar alineación si la celda existe y tiene contenido
                                var cell = doc.content[1].table.body[i][j];
                                if (cell && cell.text !== undefined) {
                                    cell.alignment = 'center';
                                }
                            }
                        }

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
                {data: "product__name"},
                {data: "product__category__name"},
                {data: "product__price"},
                {data: "product__pvp"},
                {data: "total_qty"},
                {data: "total_benefit"},
            ],
            columnDefs: [
                {
                    targets: [-1, -3, -4],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return 'S/' + data.toFixed(2);
                    }
                },
                {
                    targets: [-2],
                    class: 'text-center',
                    render: function (data, type, row) {
                        return data;
                    }
                }
            ],
            fnFooterCallback: function (row, data, start, end, display) {
                var api = this.api()

                var intVal = function (i) {
                    return typeof i === 'string' ? i.replace(/[\$,]/g, '') * 1 : typeof i === 'number' ? i : 0;
                };

                var total = api
                    .column(5, { search: 'applied' })
                    .data()
                    .reduce(function (a, b) {
                        return intVal(a) + intVal(b);
                    }, 0);

                $(api.column(5).footer()).html(
                    'S/' + total.toFixed(2)
                );

            },
            rowCallback: function (row, data, index) {

            },
            initComplete: function (settings, json) {
                $(this).wrap('<div class="dataTables_scroll"><div/>');
                // report.graph();
            }
        });
    },

};

$(function () {
    select_product = $('select[name="product"]');

    $('.select2').select2({
        placeholder: 'Buscar..',
        language: 'es',
        theme: 'bootstrap4'
    });

    $('.btnSearch').on('click', function () {
        report.list();
    });
});