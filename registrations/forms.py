import re

from django import forms
from django.core.exceptions import ValidationError

from registrations.services.images import validate_id_card

_REG_NUMBER = re.compile(r"[A-Z0-9]{10}")


class RegistrationForm(forms.Form):
    name = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={
            "class": "field-input", "autocomplete": "name",
            "placeholder": "As printed on your ID", "required": True,
        }),
    )
    reg_number = forms.CharField(
        max_length=32,
        label="Registration number",
        widget=forms.TextInput(attrs={
            "class": "field-input", "autocomplete": "off",
            "autocapitalize": "characters", "spellcheck": "false",
            "placeholder": "10 characters, e.g. 251FW02027", "required": True,
            "hx-get": "/register/check/",
            "hx-trigger": "keyup changed delay:400ms, blur",
            "hx-target": "#reg-hint", "hx-swap": "innerHTML",
        }),
    )
    phone = forms.CharField(
        max_length=16,
        label="Phone",
        widget=forms.TextInput(attrs={
            "class": "field-input", "autocomplete": "tel", "inputmode": "tel",
            "placeholder": "10-digit mobile number", "required": True,
        }),
    )
    id_card = forms.FileField(
        label="Student ID card",
        widget=forms.FileInput(attrs={
            "class": "mt-2 block w-full text-sm text-slate-700 file:mr-3 file:rounded-lg file:border-0 file:bg-ink file:px-3 file:py-2 file:text-sm file:font-semibold file:text-white",
            "accept": "image/jpeg,image/png,image/webp", "capture": "environment",
            "required": True,
        }),
    )

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        if len(name) < 2:
            raise ValidationError("Enter your full name.")
        return name

    def clean_reg_number(self):
        reg_number = self.cleaned_data["reg_number"].strip().upper()
        if len(reg_number) != 10:
            raise ValidationError("Registration number must be exactly 10 characters.")
        if not _REG_NUMBER.fullmatch(reg_number):
            raise ValidationError("Use only letters and numbers in your registration number.")
        return reg_number

    def clean_phone(self):
        raw = re.sub(r"[\s()-]", "", self.cleaned_data["phone"])
        if raw.startswith("+91"):
            raw = raw[3:]
        elif raw.startswith("91") and len(raw) == 12:
            raw = raw[2:]
        elif raw.startswith("0") and len(raw) == 11:
            raw = raw[1:]
        if not re.fullmatch(r"[6-9]\d{9}", raw):
            raise ValidationError("Enter a valid Indian mobile number.")
        return "+91" + raw

    def clean_id_card(self):
        return validate_id_card(self.cleaned_data["id_card"])
