import json
import os
import random
import string
from os.path import basename

import django
from django.contrib.auth.models import Group
from django.core.files import File
from django.core.management import BaseCommand

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.pos.models import *


class Command(BaseCommand):
    help = 'It allows me to insert test data into the software'

    def load_json_from_file(self, file):
        with open(f'{settings.BASE_DIR}/deploy/json/{file}', encoding='utf-8', mode='r') as wr:
            return json.loads(wr.read())

    def handle(self, *args, **options):
        company = Company.objects.create(
            ruc='0921637781001',
            name='VELEZ AGUIRRE SIMON EDUARDO',
            address='5 DE OCTUBRE Y 10 DE AGOSTO NARANJITO,GUAYAS',
            mobile='0996555528',
            phone='2977557',
            email='puntohelpsa@gmail.com',
            website='https://puntohelp.com',
            description='VENTA AL POR MAYOR DE COMPUTADORAS Y EQUIPO PERIFÉRICO.',
            establishment_code='000',
            issuing_point_code='000',
            tax=15.00,
            email_host_user='netdev@in-planet.net',
            email_host_password='llylnrfzcsvykyyl'
        )
        image_path = f'{settings.BASE_DIR}{settings.STATIC_URL}img/default/logo.png'
        company.image.save(basename(image_path), content=File(open(image_path, 'rb')), save=False)
        company.save()

        numbers = list(string.digits)

        for product_json in self.load_json_from_file(file='product.json'):
            product_json['category'] = Category.objects.get_or_create(name=product_json.pop('category'))[0]
            product = Product.objects.create(**product_json)
            print(f'Product record created successfully: {product.id}')

        for expense_type in self.load_json_from_file(file='expense_type.json'):
            expense_type = ExpenseType.objects.create(**expense_type)
            print(f'Expense type record created successfully: {expense_type.id}')

        for provider_json in self.load_json_from_file(file='provider.json'):
            provider = Provider.objects.create(**provider_json)
            print(f'Provider record created successfully: {provider.id}')

        for customer_json in self.load_json_from_file(file='customer.json')[0:20]:
            user = User.objects.create(username=customer_json['dni'], names=customer_json.pop('names'), email=customer_json.pop('email'))
            user.set_password(user.username)
            user.save()
            user.groups.add(Group.objects.get(id=settings.GROUPS['customer']))
            customer_json['user'] = user
            customer = Customer.objects.create(**customer_json)
            print(f'Customer record created successfully: {customer.id}')

        provider_id = list(Provider.objects.all().values_list('id', flat=True))
        product_id = list(Product.objects.filter(is_inventoried=True).values_list('id', flat=True))

        for i in range(1, random.randint(4, 10)):
            purchase = Purchase.objects.create(number=''.join(random.choices(numbers, k=8)), provider_id=random.choice(provider_id), company_id=company.id)
            for d in range(1, random.randint(3, 10)):
                product_choice = random.choice(product_id)
                while purchase.purchasedetail_set.filter(product_id=product_choice).exists():
                    product_choice = random.choice(product_id)
                product = Product.objects.get(pk=product_choice)
                detail = PurchaseDetail.objects.create(purchase_id=purchase.id, product_id=product.id, quantity=random.randint(1, 50), price=product.price)
                product.stock += detail.quantity
                product.save()
            purchase.recalculate_invoice()
            print(f'Purchase record created successfully: {purchase.id}')
