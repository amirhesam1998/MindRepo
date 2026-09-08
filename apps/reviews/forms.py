from django import forms

from .models import ReviewLog


class RatingForm(forms.Form):
    rating = forms.ChoiceField(choices=ReviewLog.Rating.choices)
    version = forms.IntegerField(min_value=0)
