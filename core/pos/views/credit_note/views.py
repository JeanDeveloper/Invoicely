import json

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView

from core.pos.forms import CreditNoteForm, CreditNote, CreditNoteDetail, Invoice, InvoiceDetail, INVOICE_STATUS, IDENTIFICATION_TYPE
from core.pos.models import Company
from core.report.forms import ReportForm
from core.security.mixins import GroupPermissionMixin


class CreditNoteListView(GroupPermissionMixin, ListView):
    model = CreditNote
    template_name = 'credit_note/list_admin.html'
    permission_required = 'view_credit_note_admin'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                start_date = request.POST['start_date']
                end_date = request.POST['end_date']
                filters = Q()
                if len(start_date) and len(end_date):
                    filters &= Q(date_joined__range=[start_date, end_date])
                for i in self.model.objects.filter(filters):
                    data.append(i.as_dict())
            elif action == 'search_detail_products':
                data = []
                for i in CreditNoteDetail.objects.filter(credit_note_id=request.POST['id']):
                    data.append(i.as_dict())
            elif action == 'create_electronic_credit_note':
                credit_note = self.model.objects.get(pk=request.POST['id'])
                credit_note.status = INVOICE_STATUS[1][0]
                credit_note.is_draft_invoice = False
                credit_note.save()
                credit_note.invoice.status = INVOICE_STATUS[3][0]
                credit_note.invoice.save()
            else:
                data['error'] = 'No ha seleccionado ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Listado de {self.model._meta.verbose_name_plural}'
        context['create_url'] = reverse_lazy('credit_note_create_admin')
        context['form'] = ReportForm()
        return context


class CreditNoteCreateView(GroupPermissionMixin, CreateView):
    model = CreditNote
    template_name = 'credit_note/create_admin.html'
    form_class = CreditNoteForm
    success_url = reverse_lazy('credit_note_list_admin')
    permission_required = 'add_credit_note_admin'

    def post(self, request, *args, **kwargs):
        action = request.POST['action']
        data = {}
        try:
            if action == 'add':
                with transaction.atomic():
                    credit_note = CreditNote()
                    credit_note.invoice_id = int(request.POST['invoice'])
                    credit_note.motive = request.POST['motive']
                    credit_note.company = Company.objects.first()
                    credit_note.tax = credit_note.company.tax_rate
                    credit_note.is_draft_invoice = 'is_draft_invoice' in request.POST
                    credit_note.save()
                    for i in json.loads(request.POST['products']):
                        invoice_detail = InvoiceDetail.objects.get(id=i['id'])
                        CreditNoteDetail.objects.create(
                            credit_note_id=credit_note.id,
                            invoice_detail_id=invoice_detail.id,
                            product_id=invoice_detail.product_id,
                            quantity=int(i['new_quantity']),
                            price=float(i['price']),
                            discount=float(i['discount']) / 100
                        )
                    credit_note.recalculate_invoice()
            elif action == 'search_invoice':
                data = []
                term = request.POST['term']
                for i in Invoice.objects.filter(status__in=[INVOICE_STATUS[1][0], INVOICE_STATUS[2][0]]).filter(Q(receipt_number_full__icontains=term) | Q(receipt_number__icontains=term) | Q(customer__user__names__icontains=term) | Q(customer__dni__icontains=term)).exclude(is_draft_invoice=True).order_by('date_joined')[0:10]:
                    item = i.as_dict()
                    detail = []
                    for d in i.invoicedetail_set.all():
                        info = d.as_dict()
                        info['new_quantity'] = d.quantity
                        info['selected'] = 0
                        info['total_amount'] = 0.00
                        detail.append(info)
                    item['detail'] = detail
                    data.append(item)
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
        return context


class CreditNoteDeleteView(GroupPermissionMixin, DeleteView):
    model = CreditNote
    template_name = 'delete.html'
    success_url = reverse_lazy('credit_note_admin_list')
    permission_required = 'delete_credit_note_admin'

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


class CreditNoteCustomerListView(GroupPermissionMixin, ListView):
    model = CreditNote
    template_name = 'credit_note/list_customer.html'
    permission_required = 'view_credit_note_customer'

    def post(self, request, *args, **kwargs):
        data = {}
        action = request.POST['action']
        try:
            if action == 'search':
                data = []
                start_date = request.POST['start_date']
                end_date = request.POST['end_date']
                filters = Q(invoice__customer__user=request.user)
                if len(start_date) and len(end_date):
                    filters &= Q(date_joined__range=[start_date, end_date])
                for i in self.model.objects.filter(filters):
                    data.append(i.as_dict())
            elif action == 'search_detail_products':
                data = []
                for i in CreditNoteDetail.objects.filter(credit_note_id=request.POST['id']):
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
