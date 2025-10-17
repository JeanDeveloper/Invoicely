import json

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.pos.forms import InvoiceForm, Invoice, Customer, Product, InvoiceDetail, CreditNote, CreditNoteDetail, Company, AccountReceivable, INVOICE_STATUS, PAYMENT_TYPE
from core.pos.utilities.pdf_creator import PDFCreator
from core.report.forms import ReportForm
from core.security.mixins import GroupPermissionMixin


class InvoiceListView(GroupPermissionMixin, ListView):
    model = Invoice
    template_name = 'invoice/list_admin.html'
    permission_required = 'view_invoice_admin'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                start_date = request.POST.get('start_date', '')
                end_date = request.POST.get('end_date', '')
                filters = Q()
                if len(start_date) and len(end_date):
                    filters &= Q(date_joined__range=[start_date, end_date])
                for i in self.model.objects.filter(filters):
                    data.append(i.as_dict())
            elif action == 'search_detail_products':
                data = []
                for i in InvoiceDetail.objects.filter(invoice_id=request.POST['id']):
                    data.append(i.as_dict())
            elif action == 'create_electronic_invoice':
                with transaction.atomic():
                    invoice = self.model.objects.get(pk=request.POST['id'])
                    invoice.is_draft_invoice = False
                    for detail in invoice.invoicedetail_set.all():
                        detail.deduct_product_stock()
                    invoice.cash = invoice.total_amount
                    invoice.change = 0.00
                    invoice.save()
            elif action == 'create_credit_note':
                with transaction.atomic():
                    invoice = self.model.objects.get(pk=request.POST['id'])
                    credit_note = CreditNote()
                    credit_note.invoice_id = invoice.id
                    credit_note.motive = F'NOTA DE CREDITO DE LA VENTA {invoice.receipt_number_full}'
                    credit_note.company = invoice.company
                    credit_note.tax = invoice.company.tax_rate
                    credit_note.save()
                    for invoice_detail in invoice.invoicedetail_set.all():
                        credit_note_detail = CreditNoteDetail()
                        credit_note_detail.credit_note_id = credit_note.id
                        credit_note_detail.invoice_detail_id = invoice_detail.id
                        credit_note_detail.product_id = invoice_detail.product_id
                        credit_note_detail.quantity = invoice_detail.quantity
                        credit_note_detail.price = invoice_detail.price
                        credit_note_detail.discount = invoice_detail.discount
                        credit_note_detail.save()
                    credit_note.recalculate_invoice()
                    credit_note.status = INVOICE_STATUS[1][0]
                    credit_note.save()
                    invoice.status = INVOICE_STATUS[3][0]
                    invoice.save()
            elif action == 'send_receipt_by_email':
                invoice = self.model.objects.get(pk=request.POST['id'])
                data = invoice.send_invoice_files_to_customer()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Listado de {self.model._meta.verbose_name_plural}'
        context['create_url'] = reverse_lazy('invoice_create_admin')
        context['form'] = ReportForm()
        return context


class InvoiceCreateView(GroupPermissionMixin, CreateView):
    model = Invoice
    template_name = 'invoice/create_admin.html'
    form_class = InvoiceForm
    success_url = reverse_lazy('invoice_list_admin')
    permission_required = 'add_invoice_admin'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['disabled_fields'] = ['subtotal_without_tax', 'subtotal_with_tax', 'tax', 'total_tax', 'total_discount', 'total_amount', 'change']
        return kwargs

    def get_end_consumer(self):
        customer = Customer.objects.filter(dni='9999999999999').first()
        return customer.as_dict() if customer else dict()

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'add':
                with transaction.atomic():
                    invoice = Invoice()
                    invoice.date_joined = request.POST['date_joined']
                    invoice.end_credit = request.POST['end_credit']
                    invoice.company = Company.objects.first()
                    invoice.employee_id = request.user.id
                    invoice.payment_type = request.POST['payment_type']
                    invoice.customer_id = int(request.POST['customer'])
                    invoice.tax = invoice.company.tax_rate
                    invoice.is_draft_invoice = 'is_draft_invoice' in request.POST
                    invoice.save()
                    for i in json.loads(request.POST['products']):
                        product = Product.objects.get(pk=i['id'])
                        invoice_detail = InvoiceDetail.objects.create(
                            invoice_id=invoice.id,
                            product_id=product.id,
                            quantity=int(i['quantity']),
                            price=float(i['current_price']),
                            discount=float(i['discount']) / 100
                        )
                        invoice_detail.deduct_product_stock()
                    invoice.recalculate_invoice()
                    if invoice.payment_type == PAYMENT_TYPE[1][0]:
                        AccountReceivable.objects.create(
                            invoice_id=invoice.id,
                            date_joined=invoice.date_joined,
                            end_date=invoice.end_credit,
                            debt=invoice.total_amount
                        )
                    data = {'print_url': str(reverse_lazy('invoice_print', kwargs={'pk': invoice.id}))}
            elif action == 'search_product':
                product_id = json.loads(request.POST['product_id'])
                data = []
                term = request.POST['term']
                filters = Q(Q(stock__gt=0) | Q(is_inventoried=False))
                if len(term):
                    filters &= Q(Q(name__icontains=term) | Q(code__icontains=term))
                queryset = Product.objects.filter(filters).exclude(id__in=product_id).order_by('name')
                if not filters.children:
                    queryset = queryset[0:10]
                for i in queryset:
                    item = i.as_dict()
                    item['discount'] = 0.00
                    item['total_discount'] = 0.00
                    data.append(item)
            elif action == 'search_product_code':
                code = request.POST['code']
                if len(code):
                    product = Product.objects.filter(code=code).first()
                    if product:
                        data = product.as_dict()
                        data['discount'] = 0.00
                        data['total_discount'] = 0.00
            elif action == 'search_customer':
                data = []
                term = request.POST['term']
                for i in Customer.objects.filter(Q(user__names__icontains=term) | Q(dni__icontains=term)).order_by('user__names')[0:10]:
                    data.append(i.as_dict())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['title'] = f'Creación de una {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['end_consumer'] = json.dumps(self.get_end_consumer())
        context['products'] = []
        return context


class InvoiceUpdateView(GroupPermissionMixin, UpdateView):
    model = Invoice
    template_name = 'invoice/create_admin.html'
    form_class = InvoiceForm
    success_url = reverse_lazy('invoice_list_admin')
    permission_required = 'change_invoice_admin'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['disabled_fields'] = ['subtotal_without_tax', 'subtotal_with_tax', 'tax', 'total_tax', 'total_discount', 'total_amount', 'change']
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['customer'].queryset = Customer.objects.filter(id=self.object.customer.id)
        return form

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'edit':
                with transaction.atomic():
                    invoice = self.get_object()
                    invoice.date_joined = request.POST['date_joined']
                    invoice.end_credit = request.POST['end_credit']
                    invoice.employee_id = request.user.id
                    invoice.payment_type = request.POST['payment_type']
                    invoice.customer_id = int(request.POST['customer'])
                    invoice.tax = invoice.company.tax_rate
                    invoice.is_draft_invoice = 'is_draft_invoice' in request.POST
                    invoice.save()
                    invoice.invoicedetail_set.all().delete()
                    invoice.accountreceivable_set.all().delete()
                    for i in json.loads(request.POST['products']):
                        product = Product.objects.get(pk=i['id'])
                        invoice_detail = InvoiceDetail.objects.create(
                            invoice_id=invoice.id,
                            product_id=product.id,
                            quantity=int(i['quantity']),
                            price=float(i['current_price']),
                            discount=float(i['discount']) / 100
                        )
                        invoice_detail.deduct_product_stock()
                    invoice.recalculate_invoice()
                    if invoice.payment_type == PAYMENT_TYPE[1][0]:
                        AccountReceivable.objects.create(
                            invoice_id=invoice.id,
                            date_joined=invoice.date_joined,
                            end_date=invoice.end_credit,
                            debt=invoice.total_amount
                        )
                    data = {'print_url': str(reverse_lazy('invoice_print', kwargs={'pk': invoice.id}))}
            elif action == 'search_product':
                product_id = json.loads(request.POST['product_id'])
                data = []
                term = request.POST['term']
                filters = Q(Q(stock__gt=0) | Q(is_inventoried=False))
                if len(term):
                    filters &= Q(Q(name__icontains=term) | Q(code__icontains=term))
                queryset = Product.objects.filter(filters).exclude(id__in=product_id).order_by('name')
                if not filters.children:
                    queryset = queryset[0:10]
                for i in queryset:
                    item = i.as_dict()
                    item['discount'] = 0.00
                    item['total_discount'] = 0.00
                    data.append(item)
            elif action == 'search_product_code':
                code = request.POST['code']
                if len(code):
                    product = Product.objects.filter(code=code).first()
                    if product:
                        data = product.as_dict()
                        data['discount'] = 0.00
                        data['total_discount'] = 0.00
            elif action == 'search_customer':
                data = []
                term = request.POST['term']
                for i in Customer.objects.filter(Q(user__names__icontains=term) | Q(dni__icontains=term)).order_by('user__names')[0:10]:
                    data.append(i.as_dict())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_products(self):
        data = []
        for detail in self.object.invoicedetail_set.all():
            item = detail.product.as_dict()
            item['quantity'] = detail.quantity
            item['current_price'] = float(detail.price)
            item['discount'] = float(detail.discount_rate)
            item['total_discount'] = float(detail.total_discount)
            data.append(item)
        return json.dumps(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['title'] = f'Edición de una {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['end_consumer'] = dict()
        context['products'] = self.get_products()
        return context


class InvoiceDeleteView(GroupPermissionMixin, DeleteView):
    model = Invoice
    template_name = 'delete.html'
    success_url = reverse_lazy('invoice_list_admin')
    permission_required = 'delete_invoice_admin'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.get_object().delete()
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Eliminación de una {self.model._meta.verbose_name}'
        context['list_url'] = self.success_url
        return context


class InvoicePrintView(GroupPermissionMixin, ListView):
    model = Invoice
    template_name = 'invoice/ticket_pdf.html'
    success_url = reverse_lazy('invoice_list_admin')
    permission_required = 'print_invoice'

    def get(self, request, *args, **kwargs):
        invoice = self.model.objects.filter(id=self.kwargs['pk']).first()
        if invoice:
            context = {'object': invoice, 'height': 450 + invoice.invoicedetail_set.all().count() * 10}
            pdf_file = PDFCreator(template_name=self.template_name).create(context=context)
            return HttpResponse(pdf_file, content_type='application/pdf')
        return HttpResponseRedirect(self.success_url)


class InvoiceCustomerListView(GroupPermissionMixin, ListView):
    model = Invoice
    template_name = 'invoice/list_customer.html'
    permission_required = 'view_invoice_customer'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                start_date = request.POST.get('start_date', '')
                end_date = request.POST.get('end_date', '')
                filters = Q(customer__user=request.user)
                if len(start_date) and len(end_date):
                    filters &= Q(date_joined__range=[start_date, end_date])
                for i in self.model.objects.filter(filters):
                    item = i.as_dict()
                    item['print_url'] = str(reverse_lazy('invoice_print', kwargs={'pk': i.id}))
                    data.append(item)
            elif action == 'search_detail_products':
                data = []
                for i in InvoiceDetail.objects.filter(invoice_id=request.POST['id']):
                    item = i.as_dict()
                    item['print_url'] = str(reverse_lazy('invoice_print', kwargs={'pk': i.id}))
                    data.append(i.as_dict())
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Listado de {self.model._meta.verbose_name_plural}'
        context['form'] = ReportForm()
        return context
