import json
from datetime import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, FloatField
from django.db.models.functions import Coalesce
from django.views.generic import TemplateView

from core.pos.models import Product, Invoice, Customer, Provider, Category, Purchase
from core.security.models import Dashboard
from django.http import JsonResponse

class DashboardView(LoginRequiredMixin, TemplateView):
    def get_template_names(self):
        dashboard = Dashboard.objects.first()
        if dashboard and dashboard.layout == 1:
            return 'vtc_dashboard_client.html' if self.request.user.is_customer else 'vtc_dashboard_admin.html'
        return 'hzt_dashboard.html'

    def get(self, request, *args, **kwargs):
        request.user.set_group_session()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST.get('action')
        try:
            if action == 'get_top_stock_products':
                data = []
                for i in Product.objects.filter(stock__gt=0).order_by('-stock')[0:10]:
                    data.append([i.name, i.stock])
            elif action == 'get_monthly_sales_and_purchases':
                data = []
                year = datetime.now().year
                rows = []
                # for month in range(1, 13):
                #     result = Invoice.objects.filter(date_joined__month=month, date_joined__year=year).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result']
                #     rows.append(float(result))
                rows = [float(Invoice.objects.filter(date_joined__month=m, date_joined__year=year)
                              .aggregate(r=Coalesce(Sum('total_amount'), 0.0, output_field=FloatField()))['r'])
                        for m in range(1, 13)]
                data.append({'name': 'Ventas', 'data': rows})
                rows = []
                # Compras
                rows = [float(Purchase.objects.filter(date_joined__month=m, date_joined__year=year)
                              .aggregate(r=Coalesce(Sum('total_amount'), 0.0, output_field=FloatField()))['r'])
                        for m in range(1, 13)]
                data.append({'name': 'Compras', 'data': rows})
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Panel de administración'
        if not self.request.user.is_customer:
            context['customers'] = Customer.objects.all().count()
            context['providers'] = Provider.objects.all().count()
            context['categories'] = Category.objects.filter().count()
            context['products'] = Product.objects.all().count()
            context['invoices'] = Invoice.objects.filter().order_by('-id')[0:10]
        return context