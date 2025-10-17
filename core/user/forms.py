from crum import get_current_request
from django import forms
from django.contrib.auth import update_session_auth_hash

from core.security.form_handlers.base import BaseModelForm
from core.security.form_handlers.helpers import update_form_fields_attributes
from .models import User


class UserForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self, exclude_fields=['groups', 'password'])
        self.fields['groups'].required = True
        self.fields['names'].widget.attrs['autofocus'] = True

    class Meta:
        model = User
        fields = 'names', 'username', 'password', 'email', 'groups', 'image', 'is_active'
        widgets = {
            'password': forms.PasswordInput(render_value=True, attrs={'placeholder': 'Ingrese un password'}),
            'groups': forms.SelectMultiple(attrs={'class': 'select2', 'multiple': 'multiple', 'style': 'width:100%'}),
        }
        exclude = ['is_password_change', 'is_staff', 'user_permissions', 'date_joined', 'last_login', 'is_superuser', 'password_reset_token']

    def update_session(self, user):
        request = get_current_request()
        if user == request.user:
            update_session_auth_hash(request, user)

    def save(self, commit=True):
        data = {}
        try:
            if self.is_valid():
                obj = super().save(commit=False)
                raw_password = self.cleaned_data['password']
                if not obj.pk:
                    obj.set_password(raw_password)
                else:
                    user = User.objects.get(pk=obj.pk)
                    if user.password != raw_password:
                        obj.set_password(raw_password)

                if commit:
                    obj.save()
                    self.save_m2m()

                self.update_session(obj)
            else:
                data['error'] = self.errors
        except Exception as e:
            data['error'] = str(e)
        return data


class ProfileForm(BaseModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        update_form_fields_attributes(self)

    class Meta:
        model = User
        fields = 'names', 'username', 'email', 'image'
        exclude = ['is_password_change', 'is_active', 'is_staff', 'user_permissions', 'password', 'date_joined', 'last_login', 'is_superuser', 'groups', 'password_reset_token']
