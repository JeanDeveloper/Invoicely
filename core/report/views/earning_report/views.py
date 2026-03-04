import json

from django.db.models import Q
from django.http import HttpResponse
from django.views.generic import FormView

from core.pos.models import PurchaseDetail, InvoiceDetail, CreditNoteDetail
from core.report.forms import ReportForm
from core.security.mixins import GroupModuleMixin
from django.db.models import Sum, F
from collections import defaultdict

class EarningReportView(GroupModuleMixin, FormView):
    template_name = 'earning_report/report.html'
    form_class = ReportForm

    def post(self, request, *args, **kwargs):
        action = request.POST['action']
        data = {}
        try:
            if action == 'search' or action == 'search_graph':
                product_id = json.loads(request.POST['product_id'])
                filters = Q()
                if len(product_id):
                    filters &= Q(product_id__in=product_id)

                ventas_query = InvoiceDetail.objects.filter(filters).values(
                    'product_id',
                    'price'
                ).annotate(
                    total_vendido=Sum('quantity')
                ).order_by('product_id')

                devoluciones_query = CreditNoteDetail.objects.filter(filters).values(
                    'product_id'
                ).annotate(
                    total_devuelto=Sum('quantity')
                )

                devoluciones_map = {}
                for dev in devoluciones_query:
                    devoluciones_map[dev['product_id']] = float(dev['total_devuelto'])

                compras = PurchaseDetail.objects.filter(filters).select_related(
                    'purchase', 'product', 'product__category'
                ).order_by('product_id', 'purchase__time_joined')

                lotes_por_producto = defaultdict(list)
                for c in compras:
                    # IMPORTANTE: Convertimos a objeto o dict para poder restar la cantidad en memoria
                    lotes_por_producto[c.product_id].append({
                        'id': c.id,
                        'price': float(c.price),
                        'quantity_original': float(c.quantity),
                        'quantity': float(c.quantity),
                        'name': c.product.name,
                        'category': c.product.category.name if c.product.category else 'S/C'
                    })

                # 2. LÓGICA DE DEVOLUCIÓN ORDENADA (Reversa)
                for p_id, cant_devuelta in devoluciones_map.items():
                    if p_id in lotes_por_producto and cant_devuelta > 0:
                        # Recorremos los lotes DE ATRÁS HACIA ADELANTE (el más reciente primero)
                        for lote in reversed(lotes_por_producto[p_id]):
                            if cant_devuelta <= 0:
                                break

                            # ¿Cuánto le falta a este lote para estar lleno como al principio?
                            espacio_disponible = lote['quantity_original'] - lote['quantity']

                            if espacio_disponible > 0:
                                # Devolvemos solo lo que quepa o lo que tengamos
                                reponer = min(espacio_disponible, cant_devuelta)
                                lote['quantity'] += reponer
                                cant_devuelta -= reponer

                reporte_final = []

                # 3. Procesamos las ventas
                for venta in ventas_query:
                    p_id = venta['product_id']
                    pvp_cobrado = float(venta['price'])  # <--- El precio editado por el usuario
                    cantidad_restante_venta = float(venta['total_vendido'])

                    lotes = lotes_por_producto.get(p_id, [])

                    for lote in lotes:
                        if cantidad_restante_venta <= 0:
                            break

                        if lote['quantity'] <= 0:
                            continue  # Este lote ya se agotó con una venta anterior

                        # Cantidad a tomar de este lote para esta venta específica
                        cantidad_a_tomar = min(lote['quantity'], cantidad_restante_venta)

                        if cantidad_a_tomar > 0:
                            ganancia_tramo = cantidad_a_tomar * (pvp_cobrado - lote['price'])

                            reporte_final.append({
                                'product__name': lote['name'],
                                'product__category__name': lote['category'],
                                'product__price': lote['price'],
                                'product__pvp': pvp_cobrado,  # <--- Mostrará el precio real de la venta
                                'total_qty': cantidad_a_tomar,
                                'total_benefit': float(ganancia_tramo)
                            })

                            # Descontamos del lote para que la siguiente venta no use lo mismo
                            lote['quantity'] -= cantidad_a_tomar
                            cantidad_restante_venta -= cantidad_a_tomar

                # 4. Respuesta para la tabla o gráfico
                if action == 'search':
                    data = reporte_final
                elif action == 'search_graph':
                    # Aquí llamamos a la función que acabamos de crear
                    data = self.get_graph_data(reporte_final)
                else:
                    # Para el gráfico, quizás prefieras agrupar por nombre para no tener mil barras
                    data = self.get_graph_data(reporte_final)  # Función opcional para agrupar

            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

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