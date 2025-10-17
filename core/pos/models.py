import base64
import math
import os
import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import BytesIO

import barcode
from barcode import writer
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.db import models
from django.db.models import F, Sum, FloatField
from django.db.models.functions import Coalesce
from django.forms import model_to_dict

from config import settings
from core.pos.choices import *
from core.pos.utilities.pdf_creator import PDFCreator
from core.user.models import User


class Company(models.Model):
    ruc = models.CharField(max_length=13, help_text='Ingrese un número de RUC', verbose_name='Número de RUC')
    name = models.CharField(max_length=50, help_text='Ingrese el nombre comercial', verbose_name='Nombre Comercial')
    address = models.CharField(max_length=200, help_text='Ingrese la dirección del Establecimiento Matriz', verbose_name='Dirección del Establecimiento Matriz')
    image = models.ImageField(upload_to='company/%Y/%m/%d', null=True, blank=True, verbose_name='Logotipo')
    mobile = models.CharField(max_length=10, null=True, blank=True, help_text='Ingrese el teléfono celular', verbose_name='Teléfono celular')
    phone = models.CharField(max_length=9, null=True, blank=True, help_text='Ingrese el teléfono convencional', verbose_name='Teléfono convencional')
    email = models.CharField(max_length=50, help_text='Ingrese la dirección de correo electrónico', verbose_name='Email')
    website = models.CharField(max_length=250, help_text='Ingrese la dirección de la página web', verbose_name='Dirección de página web')
    description = models.CharField(max_length=500, null=True, blank=True, help_text='Ingrese una breve descripción', verbose_name='Descripción')
    establishment_code = models.CharField(max_length=3, help_text='Ingrese el código del Establecimiento Emisor', verbose_name='Código del Establecimiento Emisor')
    issuing_point_code = models.CharField(max_length=3, help_text='Ingrese el código del Punto de Emisión', verbose_name='Código del Punto de Emisión')
    tax = models.DecimalField(default=0.00, decimal_places=2, max_digits=9, verbose_name='Impuesto IVA')
    email_host = models.CharField(max_length=30, default='smtp.gmail.com', verbose_name='Servidor de correo')
    email_port = models.IntegerField(default=587, verbose_name='Puerto del servidor de correo')
    email_host_user = models.CharField(max_length=100, help_text='Ingrese el nombre de usuario del servidor de correo', verbose_name='Username del servidor de correo')
    email_host_password = models.CharField(max_length=30, help_text='Ingrese la contraseña del servidor de correo', verbose_name='Password del servidor de correo')

    def __str__(self):
        return self.name

    @property
    def base64_image(self):
        try:
            if self.image:
                with open(self.image.path, 'rb') as image_file:
                    base64_data = base64.b64encode(image_file.read()).decode('utf-8')
                    extension = os.path.splitext(self.image.name)[1]
                    content_type = f'image/{extension.lstrip(".")}'
                    return f"data:{content_type};base64,{base64_data}"
        except:
            pass
        return None

    @property
    def tax_rate(self):
        return float(self.tax) / 100

    def get_image(self):
        if self.image:
            return f'{settings.MEDIA_URL}{self.image}'
        return f'{settings.STATIC_URL}img/default/empty.png'

    def get_full_path_image(self):
        if self.image:
            return self.image.path
        return f'{settings.BASE_DIR}{settings.STATIC_URL}img/default/empty.png'

    def as_dict(self):
        item = model_to_dict(self)
        item['image'] = self.get_image()
        item['tax'] = float(self.tax)
        return item

    class Meta:
        verbose_name = 'Compañia'
        verbose_name_plural = 'Compañias'
        default_permissions = ()
        permissions = (
            ('change_company', 'Can change Compañia'),
        )


class Provider(models.Model):
    name = models.CharField(max_length=50, unique=True, help_text='Ingrese un nombre', verbose_name='Nombre')
    ruc = models.CharField(max_length=13, unique=True, help_text='Ingrese un RUC', verbose_name='RUC')
    mobile = models.CharField(max_length=10, unique=True, help_text='Ingrese un número de teléfono celular', verbose_name='Teléfono celular')
    address = models.CharField(max_length=500, null=True, blank=True, help_text='Ingrese una dirección', verbose_name='Dirección')
    email = models.CharField(max_length=50, unique=True, help_text='Ingrese un email', verbose_name='Email')

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return f'{self.name} ({self.ruc})'

    def as_dict(self):
        item = model_to_dict(self)
        item['text'] = self.get_full_name()
        return item

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True, help_text='Ingrese un nombre', verbose_name='Nombre')

    def __str__(self):
        return self.name

    def as_dict(self):
        item = model_to_dict(self)
        return item

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'


class Product(models.Model):
    name = models.CharField(max_length=150, help_text='Ingrese un nombre', verbose_name='Nombre')
    code = models.CharField(max_length=50, unique=True, help_text='Ingrese un código', verbose_name='Código')
    description = models.CharField(max_length=500, null=True, blank=True, help_text='Ingrese una descripción', verbose_name='Descripción')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name='Categoría')
    price = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Precio de Compra')
    pvp = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Precio de Venta Sin Impuesto')
    image = models.ImageField(upload_to='product/%Y/%m/%d', null=True, blank=True, verbose_name='Imagen')
    barcode = models.ImageField(upload_to='barcode/%Y/%m/%d', null=True, blank=True, verbose_name='Código de barra')
    is_inventoried = models.BooleanField(default=True, verbose_name='¿Es inventariado?')
    stock = models.IntegerField(default=0)
    has_tax = models.BooleanField(default=True, verbose_name='¿Se cobra impuesto?')

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return f'{self.name} ({self.code}) ({self.category.name})'

    def get_short_name(self):
        return f'{self.name} ({self.category.name})'

    def get_price_promotion(self):
        promotion = self.promotiondetail_set.filter(promotion__active=True).first()
        if promotion:
            return promotion.final_price
        return 0.00

    def get_current_price(self):
        price_promotion = self.get_price_promotion()
        return price_promotion if price_promotion else self.pvp

    def get_image(self):
        if self.image:
            return f'{settings.MEDIA_URL}{self.image}'
        return f'{settings.STATIC_URL}img/default/empty.png'

    def get_barcode(self):
        if self.barcode:
            return f'{settings.MEDIA_URL}{self.barcode}'
        return f'{settings.STATIC_URL}img/default/empty.png'

    def get_benefit(self):
        return round(float(self.pvp) - float(self.price), 2)

    def generate_barcode(self):
        try:
            image_io = BytesIO()
            barcode.Gs1_128(self.code, writer=barcode.writer.ImageWriter()).write(image_io)
            filename = f'{self.code}.png'
            self.barcode.save(filename, content=ContentFile(image_io.getvalue()), save=False)
        except:
            pass

    def as_dict(self):
        item = model_to_dict(self)
        item['value'] = self.get_full_name()
        item['full_name'] = self.get_full_name()
        item['short_name'] = self.get_short_name()
        item['category'] = self.category.as_dict()
        item['price'] = float(self.price)
        item['price_promotion'] = float(self.get_price_promotion())
        item['current_price'] = float(self.get_current_price())
        item['pvp'] = float(self.pvp)
        item['image'] = self.get_image()
        item['barcode'] = self.get_barcode()
        return item

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.generate_barcode()
        super(Product, self).save()

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        default_permissions = ()
        permissions = (
            ('view_product', 'Can view Producto'),
            ('add_product', 'Can add Producto'),
            ('change_product', 'Can change Producto'),
            ('delete_product', 'Can delete Producto'),
            ('adjust_product_stock', 'Can adjust_product_stock Producto'),
        )


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    dni = models.CharField(max_length=13, unique=True, help_text='Ingrese un número de cédula o RUC', verbose_name='Número de cédula o RUC')
    mobile = models.CharField(max_length=10, null=True, blank=True, help_text='Ingrese un teléfono', verbose_name='Teléfono')
    birthdate = models.DateField(default=datetime.now, verbose_name='Fecha de nacimiento')
    address = models.CharField(max_length=500, null=True, blank=True, help_text='Ingrese una dirección', verbose_name='Dirección')
    send_email_invoice = models.BooleanField(default=True, verbose_name='¿Enviar email de factura?')

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return f'{self.user.names} ({self.dni})'

    def formatted_birthdate(self):
        return self.birthdate.strftime('%Y-%m-%d')

    def as_dict(self):
        item = model_to_dict(self)
        item['text'] = self.get_full_name()
        item['user'] = self.user.as_dict()
        item['birthdate'] = self.formatted_birthdate()
        return item

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'


class ExpenseType(models.Model):
    name = models.CharField(max_length=50, unique=True, help_text='Ingrese un nombre', verbose_name='Nombre')

    def __str__(self):
        return self.name

    def as_dict(self):
        item = model_to_dict(self)
        return item

    class Meta:
        verbose_name = 'Tipo de Gasto'
        verbose_name_plural = 'Tipos de Gastos'
        default_permissions = ()
        permissions = (
            ('view_expense_type', 'Can view Tipo de Gasto'),
            ('add_expense_type', 'Can add Tipo de Gasto'),
            ('change_expense_type', 'Can change Tipo de Gasto'),
            ('delete_expense_type', 'Can delete Tipo de Gasto'),
        )


class Expense(models.Model):
    expense_type = models.ForeignKey(ExpenseType, on_delete=models.PROTECT, verbose_name='Tipo de Gasto')
    description = models.CharField(max_length=500, null=True, blank=True, help_text='Ingrese una descripción', verbose_name='Detalles')
    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha de Registro')
    amount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Monto')

    def __str__(self):
        return self.description

    def as_dict(self):
        item = model_to_dict(self)
        item['expense_type'] = self.expense_type.as_dict()
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['amount'] = float(self.amount)
        return item

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.description:
            self.description = 's/n'
        super(Expense, self).save()

    class Meta:
        verbose_name = 'Gasto'
        verbose_name_plural = 'Gastos'


class Promotion(models.Model):
    start_date = models.DateField(default=datetime.now)
    end_date = models.DateField(default=datetime.now)
    active = models.BooleanField(default=True)

    def __str__(self):
        return str(self.id)

    def as_dict(self):
        item = model_to_dict(self)
        item['start_date'] = self.start_date.strftime('%Y-%m-%d')
        item['end_date'] = self.end_date.strftime('%Y-%m-%d')
        return item

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.active = self.end_date > self.start_date
        super(Promotion, self).save()

    class Meta:
        verbose_name = 'Promoción'
        verbose_name_plural = 'Promociones'


class PromotionDetail(models.Model):
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    current_price = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    total_discount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    final_price = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)

    def __str__(self):
        return self.product.name

    def calculate_total_discount(self):
        total_dscto = float(self.current_price) * float(self.discount)
        return math.floor(total_dscto * 10 ** 2) / 10 ** 2

    def as_dict(self):
        item = model_to_dict(self, exclude=['promotion'])
        item['product'] = self.product.as_dict()
        item['current_price'] = float(self.current_price)
        item['discount'] = float(self.discount)
        item['total_discount'] = float(self.total_discount)
        item['final_price'] = float(self.final_price)
        return item

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.total_discount = self.calculate_total_discount()
        self.final_price = float(self.current_price) - float(self.total_discount)
        super(PromotionDetail, self).save()

    class Meta:
        verbose_name = 'Detalle Promoción'
        verbose_name_plural = 'Detalle de Promociones'
        default_permissions = ()


class TransactionSummary(models.Model):
    receipt_number = models.CharField(max_length=9, null=True, blank=True, verbose_name='Número de comprobante')
    receipt_number_full = models.CharField(max_length=9, null=True, blank=True, verbose_name='Número completo de comprobante')
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha de registro')
    time_joined = models.DateTimeField(default=datetime.now, verbose_name='Fecha y hora de registro')
    subtotal_without_tax = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Subtotal sin impuestos')
    subtotal_with_tax = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Subtotal con impuestos')
    tax = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='IVA')
    total_tax = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Total de IVA')
    total_discount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Valor total del descuento')
    total_amount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Total a pagar')

    @property
    def subtotal(self):
        return float(self.subtotal_with_tax) + float(self.subtotal_without_tax)

    @property
    def tax_rate(self):
        return int(self.tax * 100)

    def formatted_date_joined(self):
        return (datetime.strptime(self.date_joined, '%Y-%m-%d') if isinstance(self.date_joined, str) else self.date_joined).strftime('%Y-%m-%d')

    def formatted_time_joined(self):
        return self.time_joined.strftime('%Y-%m-%d %H:%M:%S')

    def as_dict(self):
        item = model_to_dict(self, exclude=['company'])
        item['date_joined'] = self.formatted_date_joined()
        item['time_joined'] = self.formatted_time_joined()
        item['subtotal_without_tax'] = float(self.subtotal_without_tax)
        item['subtotal_with_tax'] = float(self.subtotal_with_tax)
        item['tax'] = float(self.tax)
        item['total_tax'] = float(self.total_tax)
        item['total_discount'] = float(self.total_discount)
        item['total_amount'] = float(self.total_amount)
        item['subtotal'] = self.subtotal
        return item

    def generate_receipt_number(self):
        self.receipt_number = '000000001'
        last_record = self._meta.model.objects.order_by('-id').first()
        if last_record:
            self.receipt_number = f'{int(last_record.receipt_number) + 1:09d}'
        self.receipt_number_full = f'{self.company.establishment_code}-{self.company.issuing_point_code}-{self.receipt_number}'

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.pk:
            self.generate_receipt_number()
        super(TransactionSummary, self).save()

    class Meta:
        abstract = True


class TransactionDetailBase(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    price_with_tax = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    subtotal = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    tax = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    total_tax = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    total_discount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)

    @property
    def tax_rate(self):
        return self.tax * 100

    @property
    def discount_rate(self):
        return self.discount * 100

    def as_dict(self):
        item = model_to_dict(self)
        item['product'] = self.product.as_dict()
        item['tax'] = float(self.tax)
        item['price'] = float(self.price)
        item['price_with_tax'] = float(self.price_with_tax)
        item['subtotal'] = float(self.subtotal)
        item['tax'] = float(self.tax)
        item['total_tax'] = float(self.total_tax)
        item['discount'] = float(self.discount)
        item['total_discount'] = float(self.total_discount)
        item['total_amount'] = float(self.total_amount)
        return item

    class Meta:
        abstract = True


class Purchase(TransactionSummary):
    number = models.CharField(max_length=8, unique=True, help_text='Ingrese un número de factura', verbose_name='Número de factura')
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT, verbose_name='Proveedor')
    payment_type = models.CharField(max_length=50, choices=PAYMENT_TYPE, default=PAYMENT_TYPE[0][0], verbose_name='Tipo de pago')
    end_credit = models.DateField(default=datetime.now, verbose_name='Fecha de plazo de crédito')

    def __str__(self):
        return self.provider.name

    def calculate_detail(self):
        for detail in self.purchasedetail_set.filter():
            detail.price = float(detail.price)
            detail.tax = float(self.tax)
            detail.price_with_tax = detail.price + (detail.price * detail.tax)
            detail.subtotal = detail.price * detail.quantity
            detail.total_discount = detail.subtotal * float(detail.discount)
            detail.total_tax = (detail.subtotal - detail.total_discount) * detail.tax
            detail.total_amount = detail.subtotal - detail.total_discount
            detail.save()

    def calculate_invoice(self):
        self.subtotal_without_tax = float(self.purchasedetail_set.filter(product__has_tax=False).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result'])
        self.subtotal_with_tax = float(self.purchasedetail_set.filter(product__has_tax=True).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result'])
        self.total_tax = float(self.purchasedetail_set.filter(product__has_tax=True).aggregate(result=Coalesce(Sum('total_tax'), 0.00, output_field=FloatField()))['result'])
        self.total_discount = float(self.purchasedetail_set.filter().aggregate(result=Coalesce(Sum('total_discount'), 0.00, output_field=FloatField()))['result'])
        self.total_amount = round(self.subtotal, 2) + float(self.total_tax)
        self.save()

    def recalculate_invoice(self):
        self.calculate_detail()
        self.calculate_invoice()

    def delete(self, using=None, keep_parents=False):
        try:
            for i in self.purchasedetail_set.all():
                i.product.stock -= i.quantity
                i.product.save()
        except:
            pass
        super(Purchase, self).delete()

    def as_dict(self):
        item = super().as_dict()
        item['provider'] = self.provider.as_dict()
        item['payment_type'] = {'id': self.payment_type, 'name': self.get_payment_type_display()}
        item['end_credit'] = self.end_credit.strftime('%Y-%m-%d')
        return item

    class Meta:
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'
        default_permissions = ()
        permissions = (
            ('view_purchase', 'Can view Compra'),
            ('add_purchase', 'Can add Compra'),
            ('delete_purchase', 'Can delete Compra'),
        )


class PurchaseDetail(TransactionDetailBase):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE)

    def __str__(self):
        return self.product.name

    def as_dict(self):
        item = super().as_dict()
        return item

    class Meta:
        verbose_name = 'Detalle de Compra'
        verbose_name_plural = 'Detalle de Compras'
        default_permissions = ()


class AccountPayable(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.PROTECT)
    date_joined = models.DateField(default=datetime.now)
    end_date = models.DateField(default=datetime.now)
    debt = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    balance = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.get_full_name()

    def formatted_date_joined(self):
        return self.date_joined.strftime('%Y-%m-%d')

    def get_full_name(self):
        return f"{self.purchase.provider.name} ({self.purchase.number}) / {self.formatted_date_joined()} / ${f'{self.debt:.2f}'}"

    def validate_debt(self):
        try:
            balance = self.accountpayablepayment_set.aggregate(result=Coalesce(Sum('amount'), 0.00, output_field=FloatField()))['result']
            self.balance, self.active = float(self.debt) - float(balance), (float(self.debt) - float(balance)) > 0.00
            self.save()
        except:
            pass

    def as_dict(self):
        item = model_to_dict(self)
        item['text'] = self.get_full_name()
        item['purchase'] = self.purchase.as_dict()
        item['date_joined'] = self.formatted_date_joined()
        item['end_date'] = self.end_date.strftime('%Y-%m-%d')
        item['debt'] = float(self.debt)
        item['balance'] = float(self.balance)
        return item

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.pk:
            self.balance = self.debt
        super(AccountPayable, self).save()

    class Meta:
        verbose_name = 'Cuenta por pagar'
        verbose_name_plural = 'Cuentas por pagar'
        default_permissions = ()
        permissions = (
            ('view_account_payable', 'Can view Cuenta por pagar'),
            ('add_account_payable', 'Can add Cuenta por pagar'),
            ('delete_account_payable', 'Can delete Cuenta por pagar'),
        )


class AccountPayablePayment(models.Model):
    account_payable = models.ForeignKey(AccountPayable, on_delete=models.CASCADE, verbose_name='Cuenta por pagar')
    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha de registro')
    description = models.CharField(max_length=500, null=True, blank=True, help_text='Ingrese una descripción', verbose_name='Detalles')
    amount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Monto')

    def __str__(self):
        return self.account_payable.id

    def as_dict(self):
        item = model_to_dict(self, exclude=['debts_pay'])
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['amount'] = float(self.amount)
        return item

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.description:
            self.description = 's/n'
        super(AccountPayablePayment, self).save()
        self.account_payable.validate_debt()

    def delete(self, using=None, keep_parents=False):
        account_payable = self.account_payable
        super(AccountPayablePayment, self).delete()
        account_payable.validate_debt()

    class Meta:
        verbose_name = 'Pago de una Cuenta por pagar'
        verbose_name_plural = 'Pago de unas Cuentas por pagar'
        default_permissions = ()


class Invoice(TransactionSummary):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, verbose_name='Cliente')
    employee = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, verbose_name='Empleado')
    payment_type = models.CharField(choices=PAYMENT_TYPE, max_length=50, default=PAYMENT_TYPE[0][0], verbose_name='Forma de pago')
    end_credit = models.DateField(default=datetime.now, verbose_name='Fecha limite de crédito')
    cash = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Efectivo recibido')
    change = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Cambio')
    is_draft_invoice = models.BooleanField(default=False, verbose_name='Factura borrador')
    status = models.CharField(max_length=50, choices=INVOICE_STATUS, default=INVOICE_STATUS[0][0], verbose_name='Estado')

    def __str__(self):
        return self.get_full_name()

    @property
    def subtotal_without_taxes(self):
        return float(self.invoicedetail_set.filter().aggregate(result=Coalesce(Sum('subtotal'), 0.00, output_field=FloatField()))['result'])

    def get_full_name(self):
        return f'{self.receipt_number_full} / {self.customer.get_full_name()})'

    def calculate_detail(self):
        for detail in self.invoicedetail_set.filter():
            detail.price = float(detail.price)
            detail.tax = float(self.tax)
            detail.price_with_tax = detail.price + (detail.price * detail.tax)
            detail.subtotal = detail.price * detail.quantity
            detail.total_discount = detail.subtotal * float(detail.discount)
            detail.total_tax = (detail.subtotal - detail.total_discount) * detail.tax
            detail.total_amount = detail.subtotal - detail.total_discount
            detail.save()

    def calculate_invoice(self):
        self.subtotal_without_tax = float(self.invoicedetail_set.filter(product__has_tax=False).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result'])
        self.subtotal_with_tax = float(self.invoicedetail_set.filter(product__has_tax=True).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result'])
        self.total_tax = float(self.invoicedetail_set.filter(product__has_tax=True).aggregate(result=Coalesce(Sum('total_tax'), 0.00, output_field=FloatField()))['result'])
        self.total_discount = float(self.invoicedetail_set.filter().aggregate(result=Coalesce(Sum('total_discount'), 0.00, output_field=FloatField()))['result'])
        self.total_amount = round(self.subtotal, 2) + float(self.total_tax)
        self.save()

    def recalculate_invoice(self):
        self.calculate_detail()
        self.calculate_invoice()

    def send_invoice_files_to_customer(self):
        response = {'resp': True}
        try:
            message = MIMEMultipart('alternative')
            message['Subject'] = f'Notificación de Factura {self.receipt_number_full}'
            message['From'] = self.company.email_host_user
            message['To'] = self.customer.user.email
            content = f'Estimado(a)\n\n{self.customer.user.names.upper()}\n\n'
            content += f"{self.company.name} le informa que el documento PDF de su factura ha sido enviado a su correo electrónico.\n\n"
            content += f"FECHA: {self.formatted_date_joined()}\n"
            content += f'MONTO: {str(float(round(self.total_amount, 2)))}\n'
            part = MIMEText(content)
            message.attach(part)
            pdf_file = self.create_invoice_pdf()
            part = MIMEApplication(pdf_file, _subtype='pdf')
            part.add_header('Content-Disposition', 'attachment', filename=f'{self.receipt_number_full}.pdf')
            message.attach(part)
            server = smtplib.SMTP(self.company.email_host, self.company.email_port)
            server.starttls()
            server.login(self.company.email_host_user, self.company.email_host_password)
            server.sendmail(self.company.email_host_user, message['To'], message.as_string())
            server.quit()
        except Exception as e:
            response = {'resp': False, 'error': str(str(e))}
        return response

    def create_invoice_pdf(self):
        template_name = 'invoice/ticket_pdf.html'
        return PDFCreator(template_name=template_name).create(context={'object': self})

    def as_dict(self):
        item = super().as_dict()
        item['text'] = self.get_full_name()
        item['customer'] = self.customer.as_dict()
        item['employee'] = self.employee.as_dict() if self.employee else dict()
        item['payment_type'] = {'id': self.payment_type, 'name': self.get_payment_type_display()}
        item['end_credit'] = self.end_credit.strftime('%Y-%m-%d')
        item['cash'] = float(self.cash)
        item['change'] = float(self.change)
        item['status'] = {'id': self.status, 'name': self.get_status_display()}
        return item

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.is_draft_invoice and self.status != INVOICE_STATUS[3][0]:
            self.status = INVOICE_STATUS[1][0]
        super(Invoice, self).save()

    class Meta:
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        default_permissions = ()
        permissions = (
            ('view_invoice_admin', 'Can view Factura'),
            ('add_invoice_admin', 'Can add Factura'),
            ('change_invoice_admin', 'Can update Factura'),
            ('delete_invoice_admin', 'Can delete Factura'),
            ('view_invoice_customer', 'Can view Factura | Cliente'),
            ('print_invoice', 'Can print Factura'),
        )
        ordering = ['id']


class InvoiceDetail(TransactionDetailBase):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)

    def __str__(self):
        return self.product.name

    def deduct_product_stock(self):
        if not self.invoice.is_draft_invoice:
            if self.product.is_inventoried:
                self.product.stock -= self.quantity
                self.product.save()

    def as_dict(self):
        return super().as_dict()

    class Meta:
        verbose_name = 'Detalle de Factura'
        verbose_name_plural = 'Detalle de Facturas'
        default_permissions = ()
        ordering = ['id']


class AccountReceivable(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT)
    date_joined = models.DateField(default=datetime.now)
    end_date = models.DateField(default=datetime.now)
    debt = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    balance = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.get_full_name()

    def formatted_date_joined(self):
        return self.date_joined.strftime('%Y-%m-%d')

    def get_full_name(self):
        return f"{self.invoice.customer.user.names} ({self.invoice.customer.dni}) / {self.formatted_date_joined()} / ${f'{self.debt:.2f}'}"

    def validate_debt(self):
        try:
            balance = self.accountreceivablepayment_set.aggregate(result=Coalesce(Sum('amount'), 0.00, output_field=FloatField()))['result']
            self.balance, self.active = float(self.debt) - float(balance), (float(self.debt) - float(balance)) > 0.00
            self.save()
        except:
            pass

    def as_dict(self):
        item = model_to_dict(self)
        item['text'] = self.get_full_name()
        item['invoice'] = self.invoice.as_dict()
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['end_date'] = self.end_date.strftime('%Y-%m-%d')
        item['debt'] = float(self.debt)
        item['balance'] = float(self.balance)
        return item

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.pk:
            self.balance = self.debt
        super(AccountReceivable, self).save()

    class Meta:
        verbose_name = 'Cuenta por cobrar'
        verbose_name_plural = 'Cuentas por cobrar'
        default_permissions = ()
        permissions = (
            ('view_account_receivable', 'Can view Cuenta por cobrar'),
            ('add_account_receivable', 'Can add Cuenta por cobrar'),
            ('delete_account_receivable', 'Can delete Cuenta por cobrar'),
        )


class AccountReceivablePayment(models.Model):
    account_receivable = models.ForeignKey(AccountReceivable, on_delete=models.CASCADE, verbose_name='Cuenta por cobrar')
    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha de registro')
    description = models.CharField(max_length=500, null=True, blank=True, help_text='Ingrese una descripción', verbose_name='Detalles')
    amount = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Monto')

    def __str__(self):
        return self.account_receivable.id

    def as_dict(self):
        item = model_to_dict(self, exclude=['ctas_collect'])
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['amount'] = float(self.amount)
        return item

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.description:
            self.description = 's/n'
        super(AccountReceivablePayment, self).save()
        self.account_receivable.validate_debt()

    def delete(self, using=None, keep_parents=False):
        account_receivable = self.account_receivable
        super(AccountReceivablePayment, self).delete()
        account_receivable.validate_debt()

    class Meta:
        verbose_name = 'Detalle de una Cuenta por cobrar'
        verbose_name_plural = 'Detalles de unas Cuentas por cobrar'
        default_permissions = ()


class CreditNote(TransactionSummary):
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, verbose_name='Factura')
    motive = models.CharField(max_length=300, null=True, blank=True, help_text='Ingrese una descripción', verbose_name='Motivo')
    is_draft_invoice = models.BooleanField(default=False, verbose_name='Factura borrador')
    status = models.CharField(max_length=50, choices=INVOICE_STATUS, default=INVOICE_STATUS[0][0], verbose_name='Estado')

    def __str__(self):
        return self.motive

    @property
    def subtotal_without_taxes(self):
        return float(self.creditnotedetail_set.filter().aggregate(result=Coalesce(Sum('subtotal'), 0.00, output_field=FloatField()))['result'])

    def calculate_detail(self):
        for detail in self.creditnotedetail_set.filter():
            detail.price = float(detail.price)
            detail.tax = float(self.tax)
            detail.price_with_tax = detail.price + (detail.price * detail.tax)
            detail.subtotal = detail.price * detail.quantity
            detail.total_discount = detail.subtotal * float(detail.discount)
            detail.total_tax = (detail.subtotal - detail.total_discount) * detail.tax
            detail.total_amount = detail.subtotal - detail.total_discount
            detail.save()

    def calculate_invoice(self):
        self.subtotal_without_tax = float(self.creditnotedetail_set.filter(product__has_tax=False).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result'])
        self.subtotal_with_tax = float(self.creditnotedetail_set.filter(product__has_tax=True).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result'])
        self.total_tax = float(self.creditnotedetail_set.filter(product__has_tax=True).aggregate(result=Coalesce(Sum('total_tax'), 0.00, output_field=FloatField()))['result'])
        self.total_discount = float(self.creditnotedetail_set.filter().aggregate(result=Coalesce(Sum('total_discount'), 0.00, output_field=FloatField()))['result'])
        self.total_amount = round(self.subtotal, 2) + float(self.total_tax)
        self.save()

    def recalculate_invoice(self):
        self.calculate_detail()
        self.calculate_invoice()

    def return_product_stock(self):
        for detail in self.creditnotedetail_set.filter(product__is_inventoried=True):
            detail.product.stock += detail.quantity
            detail.product.save()

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.is_draft_invoice:
            self.status = INVOICE_STATUS[1][0]
        if self.pk and self.status == INVOICE_STATUS[1][0]:
            self.return_product_stock()
            self.invoice.status = INVOICE_STATUS[3][0]
            self.invoice.save()
        super(CreditNote, self).save()

    def as_dict(self):
        item = super().as_dict()
        item['invoice'] = self.invoice.as_dict()
        item['motive'] = self.motive
        item['status'] = {'id': self.status, 'name': self.get_status_display()}
        return item

    class Meta:
        verbose_name = 'Devolución'
        verbose_name_plural = 'Devoluciones'
        default_permissions = ()
        permissions = (
            ('view_credit_note_admin', 'Can view Devolución'),
            ('add_credit_note_admin', 'Can add Devolución'),
            ('delete_credit_note_admin', 'Can delete Devolución'),
            ('view_credit_note_customer', 'Can view Devolución | Cliente'),
            ('print_credit_note', 'Can print Devolución'),
        )
        ordering = ['id']


class CreditNoteDetail(TransactionDetailBase):
    credit_note = models.ForeignKey(CreditNote, on_delete=models.CASCADE)
    invoice_detail = models.ForeignKey(InvoiceDetail, on_delete=models.CASCADE)

    def __str__(self):
        return self.product.name

    def as_dict(self):
        return super().as_dict()

    class Meta:
        verbose_name = 'Detalle Devolución Ventas'
        verbose_name_plural = 'Detalle Devoluciones Ventas'
        default_permissions = ()
        ordering = ['id']


class Quotation(TransactionSummary):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='Cliente')
    employee = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Empleado')
    active = models.BooleanField(default=True, verbose_name='Activo')

    def __str__(self):
        return f'{self.formatted_number} = {self.customer.get_full_name()}'

    @property
    def subtotal_without_taxes(self):
        return float(self.quotationdetail_set.filter().aggregate(result=Coalesce(Sum('subtotal'), 0.00, output_field=FloatField()))['result'])

    @property
    def formatted_number(self):
        return f'{self.id:08d}'

    @property
    def validate_stock(self):
        return not self.quotationdetail_set.filter(product__is_inventoried=True, product__stock__lt=F('quantity')).exists()

    def send_quotation_by_email(self):
        company = Company.objects.first()
        message = MIMEMultipart('alternative')
        message['Subject'] = f'Proforma {self.formatted_number} - {self.customer.get_full_name()}'
        message['From'] = settings.EMAIL_HOST
        message['To'] = self.customer.user.email
        content = f'Estimado(a)\n\n{self.customer.user.names.upper()}\n\n'
        content += f'La cotización solicitada ha sido enviada a su correo electrónico para su revisión.\n\n'
        part = MIMEText(content)
        message.attach(part)
        context = {'quotation': self}
        pdf_creator = PDFCreator(template_name='quotation/invoice_pdf.html')
        pdf_file = pdf_creator.create(context=context)
        part = MIMEApplication(pdf_file, _subtype='pdf')
        part.add_header('Content-Disposition', 'attachment', filename=f'{self.formatted_number}.pdf')
        message.attach(part)
        server = smtplib.SMTP(company.email_host, company.email_port)
        server.starttls()
        server.login(company.email_host_user, company.email_host_password)
        server.sendmail(company.email_host_user, message['To'], message.as_string())
        server.quit()

    def calculate_detail(self):
        for detail in self.quotationdetail_set.filter():
            detail.price = float(detail.price)
            detail.tax = float(self.tax)
            detail.price_with_tax = detail.price + (detail.price * detail.tax)
            detail.subtotal = detail.price * detail.quantity
            detail.total_discount = detail.subtotal * float(detail.discount)
            detail.total_tax = (detail.subtotal - detail.total_discount) * detail.tax
            detail.total_amount = detail.subtotal - detail.total_discount
            detail.save()

    def calculate_invoice(self):
        self.subtotal_without_tax = float(self.quotationdetail_set.filter(product__has_tax=False).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result'])
        self.subtotal_with_tax = float(self.quotationdetail_set.filter(product__has_tax=True).aggregate(result=Coalesce(Sum('total_amount'), 0.00, output_field=FloatField()))['result'])
        self.total_tax = float(self.quotationdetail_set.filter(product__has_tax=True).aggregate(result=Coalesce(Sum('total_tax'), 0.00, output_field=FloatField()))['result'])
        self.total_discount = float(self.quotationdetail_set.filter().aggregate(result=Coalesce(Sum('total_discount'), 0.00, output_field=FloatField()))['result'])
        self.total_amount = round(self.subtotal, 2) + float(self.total_tax)
        self.save()

    def recalculate_invoice(self):
        self.calculate_detail()
        self.calculate_invoice()

    def create_invoice(self, is_draft_invoice=False):
        details = [detail for detail in self.quotationdetail_set.all()]
        invoice = Invoice()
        invoice.date_joined = datetime.now().date()
        invoice.company = self.company
        invoice.employee_id = self.employee_id
        invoice.customer_id = self.customer_id
        invoice.tax = invoice.company.tax_rate
        invoice.cash = float(invoice.total_amount)
        invoice.is_draft_invoice = is_draft_invoice
        invoice.save()
        for quotation_detail in details:
            product = quotation_detail.product
            invoice_detail = InvoiceDetail.objects.create(
                invoice_id=invoice.id,
                product_id=product.id,
                quantity=quotation_detail.quantity,
                price=quotation_detail.price,
                discount=quotation_detail.discount,
            )
            invoice_detail.deduct_product_stock()
        invoice.recalculate_invoice()

    def as_dict(self):
        item = super().as_dict()
        item['number'] = self.formatted_number
        item['customer'] = self.customer.as_dict()
        item['employee'] = self.employee.as_dict()
        return item

    class Meta:
        verbose_name = 'Proforma'
        verbose_name_plural = 'Proformas'
        default_permissions = ()
        permissions = (
            ('view_quotation', 'Can view Proforma'),
            ('add_quotation', 'Can add Proforma'),
            ('change_quotation', 'Can change Proforma'),
            ('delete_quotation', 'Can delete Proforman'),
            ('print_quotation', 'Can print Proforma'),
        )


class QuotationDetail(TransactionDetailBase):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE)

    def __str__(self):
        return self.quotation.__str__()

    def as_dict(self):
        return super().as_dict()

    class Meta:
        verbose_name = 'Proforma Detalle'
        verbose_name_plural = 'Proforma Detalles'
        default_permissions = ()
