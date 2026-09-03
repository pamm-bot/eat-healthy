from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Entry


class SignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ("grams", "meal", "eaten_on")
        widgets = {
            "grams": forms.NumberInput(attrs={"min": 1, "step": 1, "class": "form-control"}),
            "meal": forms.Select(attrs={"class": "form-select"}),
            "eaten_on": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["eaten_on"].initial = timezone.localdate()
