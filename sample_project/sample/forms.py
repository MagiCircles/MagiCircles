from django import forms
from sample import models

class FormWithRequest(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(FormWithRequest, self).__init__(*args, **kwargs)

class AccountForm(FormWithRequest):
    class Meta:
        model = models.Account
        fields = ('level',)
