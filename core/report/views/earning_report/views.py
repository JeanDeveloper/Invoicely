import json

from django.db.models import Q, Sum
from django.views.generic import FormView

from core.pos.models import PurchaseDetail, InvoiceDetail
from core.report.forms import ReportForm
from core.security.mixins import GroupModuleMixin
from collections import defaultdict
from decimal import Decimal
from django.http import JsonResponse

class EarningReportView(GroupModuleMixin, FormView):
    template_name = 'earning_report/report.html'
    form_class = ReportForm

    def post(self, request, *args, **kwargs):

        action = request.POST.get('action')
        data = {}

        try:

            if action not in ['search', 'search_graph']:
                return JsonResponse({'error': 'No ha seleccionado ninguna opción'}, safe=False)

            product_ids = json.loads(request.POST.get('product_id', '[]'))

            filters = Q()
            if product_ids:
                filters &= Q(product_id__in=product_ids)

            # -------------------------
            # 1️⃣ VENTAS
            # -------------------------

            ventas_query = (
                InvoiceDetail.objects
                .filter(filters)
                .order_by('product_id', "id")
            )

            # -------------------------
            # 2️⃣ COMPRAS (LOTES FIFO)
            # -------------------------

            compras = (
                PurchaseDetail.objects
                .filter(filters)
                .select_related('product', 'product__category')
                .order_by('product_id', 'id')
            )

            # Agrupamos lotes por producto
            lotes_por_producto = defaultdict(list)

            for compra in compras:
                lotes_por_producto[compra.product_id].append({
                    'price': compra.price,
                    'quantity': compra.quantity,
                    'name': compra.product.name,
                    'category': compra.product.category.name if compra.product.category else 'S/C'
                })

            reporte_final = []

            # -------------------------
            # 3️⃣ PROCESO FIFO
            # -------------------------

            for venta in ventas_query:

                product_id = venta.product_id
                pvp = venta.price
                cantidad_restante = venta.quantity

                lotes = lotes_por_producto.get(product_id)

                if not lotes:
                    continue

                # usamos índice para no recorrer siempre desde el inicio
                i = 0

                while cantidad_restante > 0 and i < len(lotes):

                    lote = lotes[i]

                    if lote['quantity'] <= 0:
                        i += 1
                        continue

                    cantidad_a_tomar = min(lote['quantity'], cantidad_restante)

                    ganancia = cantidad_a_tomar * (pvp - lote['price'])

                    reporte_final.append({
                        'product__name': lote['name'],
                        'product__category__name': lote['category'],
                        'product__price': lote['price'],
                        'product__pvp': pvp,
                        'total_qty': cantidad_a_tomar,
                        'total_benefit': ganancia
                    })

                    # descontamos cantidades
                    lote['quantity'] -= cantidad_a_tomar
                    cantidad_restante -= cantidad_a_tomar

                    if lote['quantity'] <= 0:
                        i += 1

            # -------------------------
            # 4️⃣ CONVERTIR DECIMAL A FLOAT PARA JSON
            # -------------------------

            for r in reporte_final:
                r['product__price'] = float(r['product__price'])
                r['product__pvp'] = float(r['product__pvp'])
                r['total_qty'] = float(r['total_qty'])
                r['total_benefit'] = float(r['total_benefit'])

            # -------------------------
            # 5️⃣ RESPUESTA
            # -------------------------

            if action == 'search':
                data = reporte_final
            else:
                data = self.get_graph_data(reporte_final)

        except Exception as e:
            data = {'error': str(e)}

        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Reporte de Ganancias de Productos'
        return context

    def get_graph_data(self, reporte_final):
        # Diccionario para acumular beneficios por nombre de producto
        graph_data = {}
        for item in reporte_final:
            nombre = item['product__name']
            beneficio = item['total_benefit']
            graph_data[nombre] = graph_data.get(nombre, 0) + beneficio

        # Formatear para Highcharts (formato: [['Prod 1', 100], ['Prod 2', 200]])
        return [[nombre, beneficio] for nombre, beneficio in graph_data.items()]