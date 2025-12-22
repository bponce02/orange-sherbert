"""
Custom widgets for Orange Sherbert that properly set HTML5 input types.
"""

from django import forms


class DateInput(forms.DateInput):
    """DateInput widget with input_type='date' for HTML5 date picker."""
    input_type = 'date'


class TimeInput(forms.TimeInput):
    """TimeInput widget with input_type='time' for HTML5 time picker."""
    input_type = 'time'


class DateTimeInput(forms.DateTimeInput):
    """DateTimeInput widget with input_type='datetime-local' for HTML5 datetime picker."""
    input_type = 'datetime-local'
