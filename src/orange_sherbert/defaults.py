"""
Default widget configuration for Orange Sherbert forms.

This configuration maps Django field types to their widget class, CSS classes, and extra attributes.
Projects can override these defaults in their settings.py with ORANGE_SHERBERT_FIELD_WIDGETS.
"""

DEFAULT_FIELD_WIDGETS = {
    # Field Type: (Widget Class Name, CSS Classes, Extra Attributes)
    'DateField': ('DateInput', 'input input-bordered w-full', {'type': 'date'}),
    'TimeField': ('TimeInput', 'input input-bordered w-full', {'type': 'time'}),
    'DateTimeField': ('DateTimeInput', 'input input-bordered w-full', {'type': 'datetime-local'}),
    'CharField': ('TextInput', 'input input-bordered w-full', {}),
    'EmailField': ('EmailInput', 'input input-bordered w-full', {}),
    'URLField': ('URLInput', 'input input-bordered w-full', {}),
    'IntegerField': ('NumberInput', 'input input-bordered w-full', {}),
    'DecimalField': ('NumberInput', 'input input-bordered w-full', {'step': '0.01'}),
    'FloatField': ('NumberInput', 'input input-bordered w-full', {'step': 'any'}),
    'TextField': ('Textarea', 'textarea textarea-bordered w-full', {'rows': '4'}),
    'BooleanField': ('CheckboxInput', 'checkbox', {}),
    'ChoiceField': ('Select', 'select select-bordered w-full', {}),
    'FileField': ('FileInput', 'file-input file-input-bordered w-full', {}),
    'ImageField': ('FileInput', 'file-input file-input-bordered w-full', {'accept': 'image/*'}),
}
