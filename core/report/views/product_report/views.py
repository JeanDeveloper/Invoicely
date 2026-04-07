from core.security.mixins import GroupModuleMixin
from django.views.generic import FormView
from core.report.forms import ReportForm
from django.http import JsonResponse
from django.db.models import Q, F
from core.pos.models import InvoiceDetail

class ProductReportView(GroupModuleMixin, FormView):
    template_name = 'product_report/report.html'
    form_class = ReportForm

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        data = {}
        try:
            if action == 'search':
                data = []
                start_date = request.POST['start_date']
                end_date = request.POST['end_date']
                filters = Q()
                if len(start_date) and len(end_date):
                    filters &= Q(invoice__date_joined__range=[start_date, end_date])

                queryset = InvoiceDetail.objects.filter(filters).values(
                    'product__name',
                    'product__category__name',
                    'invoice__customer__dni',
                    'invoice__date_joined',
                    'quantity',
                ).order_by('invoice__time_joined')

                for item in queryset:
                    data.append({
                        'product_nam': item['product__name'],
                        'category_nam': item['product__category__name'],
                        'customer_dni': item['invoice__customer__dni'],
                        'date': item['invoice__date_joined'].strftime('%d/%m/%Y'),
                        'quantity': item['quantity'],
                    })

            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data = {'error': str(e)}
        return JsonResponse(data, safe=False)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Reporte de Productos'
        return context
