from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import CreateView
from django.views.generic import UpdateView
from django.views.generic import DeleteView
from django.views import View
from django.urls import path, reverse
from django.db.models import Q
from django.http import HttpResponseForbidden, HttpResponse
from django.template.loader import render_to_string
from django.forms.models import BaseInlineFormSet
from django.forms.models import inlineformset_factory

class NestedInlineFormSet(BaseInlineFormSet):
    parent_formset_name = None
    children = []
    def __init__(self, *args, parent_form=None, **kwargs):
        self.parent_form = parent_form
        super().__init__(*args, **kwargs)

def nestedinlineformset_factory(parent_model, model, parent_formset_name, **kwargs):
    FormSet = inlineformset_factory(
        parent_model,
        model,
        formset=NestedInlineFormSet,
        **kwargs
    )
    FormSet.parent_formset_name = parent_formset_name
    return FormSet

class _CRUDMixin:
    fields = None
    form_fields = None
    filter_fields = {}
    search_fields = []
    extra_actions = []
    property_field_map = {}
    view_type = None
    url_namespace = None
    inline_formsets = []
    parent_view = None

    def get_formsets(self):
        formsets = {}

        if self.inline_formsets:
            for config in self.inline_formsets:
                name = config['model']._meta.model_name
                parent_model = config.get('nested_under') or self.model
                parent_name = config['nested_under']._meta.model_name if config.get('nested_under') else None
                
                formset = nestedinlineformset_factory(
                    parent_model,
                    config['model'],
                    parent_formset_name=parent_name,
                    fields=config.get('fields', '__all__'),
                    extra=config.get('extra', 1),
                    can_delete=config.get('can_delete', True),
                )
                formsets[name] = formset

        return formsets
    
    def init_formsets(self):
        self.formset_instances = {}
        self.all_formsets_by_prefix = {}
        formsets = self.get_formsets()
        
        for name, FormSetClass in formsets.items():
            if FormSetClass.parent_formset_name is None:
                formset_instance = FormSetClass(
                    instance=getattr(self, 'object', None),
                    prefix=name,
                )
                formset_instance.model_name = name
                for form in formset_instance.forms:
                    form.children = []
                self.formset_instances[name] = formset_instance
                self.all_formsets_by_prefix[name] = formset_instance
        
        for name, FormSetClass in formsets.items():
            parent_name = FormSetClass.parent_formset_name
            if parent_name and parent_name in self.formset_instances:
                parent_formset = self.formset_instances[parent_name]
                for i, parent_form in enumerate(parent_formset.forms):
                    prefix = f'{parent_name}-{i}-{name}'
                    child_formset = FormSetClass(
                        instance=parent_form.instance,
                        prefix=prefix,
                        parent_form=parent_form,
                    )
                    child_formset.model_name = name
                    for form in child_formset.forms:
                        form.children = []
                    parent_form.children.append(child_formset)
                    self.all_formsets_by_prefix[prefix] = child_formset

    def bind_formsets(self, request):
        self.formset_instances = {}
        formsets = self.get_formsets()
        
        for name, FormSetClass in formsets.items():
            if FormSetClass.parent_formset_name is None:
                formset_instance = FormSetClass(
                    request.POST,
                    request.FILES,
                    instance=getattr(self, 'object', None),
                    prefix=name,
                )
                for form in formset_instance.forms:
                    form.children = []
                self.formset_instances[name] = formset_instance
        
        for name, FormSetClass in formsets.items():
            parent_name = FormSetClass.parent_formset_name
            if parent_name and parent_name in self.formset_instances:
                parent_formset = self.formset_instances[parent_name]
                for i, parent_form in enumerate(parent_formset.forms):
                    child_formset = FormSetClass(
                        request.POST,
                        request.FILES,
                        instance=parent_form.instance,
                        prefix=f'{parent_name}-{i}-{name}',
                        parent_form=parent_form,
                    )
                    for form in child_formset.forms:
                        form.children = []
                    parent_form.children.append(child_formset)

    def add_formset(self, formset_class_name, prefix, form_index):
        formsets = self.get_formsets()
        FormSetClass = formsets.get(formset_class_name)

        formset_instance = FormSetClass(prefix=prefix)
        empty_form = formset_instance.empty_form
        
        empty_form.prefix = f'{prefix}-{form_index}'
        empty_form.children = []
        
        for name, ChildFormSetClass in formsets.items():
            if ChildFormSetClass.parent_formset_name == formset_class_name:
                child_prefix = f'{prefix}-{form_index}-{name}'
                child_formset = ChildFormSetClass(
                    instance=empty_form.instance,
                    prefix=child_prefix,
                    queryset=ChildFormSetClass.model.objects.none(),
                )
                child_formset.model_name = name
                for form in child_formset.forms:
                    form.children = []
                empty_form.children.append(child_formset)
        
        return empty_form

    def are_formsets_valid(self):
        valid = True
        stack = list(self.formset_instances.values())
        while stack:
            formset = stack.pop()
            valid = formset.is_valid() and valid
            for form in formset.forms:
                if hasattr(form, 'children'):
                    stack.extend(form.children)
        return valid
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Call parent_view's get_form_kwargs if it exists
        if self.parent_view and hasattr(self.parent_view, 'get_form_kwargs'):
            # Set request on parent_view so it can access self.request
            self.parent_view.request = self.request
            parent_kwargs = self.parent_view.get_form_kwargs()
            kwargs.update(parent_kwargs)
        return kwargs
    
    def get_form(self, form_class=None):
        from django import forms as django_forms
        
        form = super().get_form(form_class)
        
        # Apply default DaisyUI styling to form widgets
        for field_name, field in form.fields.items():
            widget = field.widget
            attrs = widget.attrs if hasattr(widget, 'attrs') else {}
            
            # Add default classes based on widget type
            if isinstance(widget, (django_forms.TextInput, django_forms.EmailInput, 
                                  django_forms.URLInput, django_forms.NumberInput,
                                  django_forms.PasswordInput)):
                if 'class' not in attrs:
                    attrs['class'] = 'input input-bordered w-full'
            elif isinstance(widget, django_forms.Textarea):
                if 'class' not in attrs:
                    attrs['class'] = 'textarea textarea-bordered w-full'
            elif isinstance(widget, django_forms.Select):
                if 'class' not in attrs:
                    attrs['class'] = 'select select-bordered w-full'
            elif isinstance(widget, django_forms.CheckboxInput):
                if 'class' not in attrs:
                    attrs['class'] = 'checkbox'
            elif isinstance(widget, django_forms.FileInput):
                if 'class' not in attrs:
                    attrs['class'] = 'file-input file-input-bordered w-full'
            elif isinstance(widget, django_forms.DateInput):
                if 'class' not in attrs:
                    attrs['class'] = 'input input-bordered w-full'
                if 'type' not in attrs:
                    attrs['type'] = 'date'
            elif isinstance(widget, django_forms.TimeInput):
                if 'class' not in attrs:
                    attrs['class'] = 'input input-bordered w-full'
                if 'type' not in attrs:
                    attrs['type'] = 'time'
            elif isinstance(widget, django_forms.DateTimeInput):
                if 'class' not in attrs:
                    attrs['class'] = 'input input-bordered w-full'
                if 'type' not in attrs:
                    attrs['type'] = 'datetime-local'
            
            widget.attrs = attrs
        
        # Call parent_view's get_form if it exists
        if self.parent_view and hasattr(self.parent_view, 'get_form'):
            form = self.parent_view.get_form(form, self.request)
        
        return form

    def save_formsets(self):
        for formset in self.formset_instances.values():
            formset.instance = self.object
        
        stack = list(self.formset_instances.values())
        while stack:
            formset = stack.pop(0)
            formset.save()
            for form in formset.forms:
                if hasattr(form, 'children'):
                    for child in form.children:
                        child.instance = form.instance
                        stack.append(child)
    
    def get_queryset(self, **kwargs):
        queryset = super().get_queryset()
        
        # Call parent_view's get_queryset if it exists
        if self.parent_view and hasattr(self.parent_view, 'get_queryset'):
            queryset = self.parent_view.get_queryset(queryset, self.request)
        
        filter_fields = self.filter_fields
        if filter_fields:
            for field in filter_fields:
                field_name = field if isinstance(filter_fields, list) else field
                field_value = self.request.GET.get(field_name)
                if field_value:
                    queryset = queryset.filter(**{field_name: field_value})
        
        search_query = self.request.GET.get('search', '').strip()
        search_fields = self.search_fields
        if search_query and search_fields:
            q_objects = Q()
            for field in search_fields:
                q_objects |= Q(**{f'{field}__icontains': search_query})
            queryset = queryset.filter(q_objects)
        
        sort_by = self.request.GET.get('sort_by')
        sort_dir = self.request.GET.get('sort_dir', 'asc')
        if sort_by:
            property_field_map = getattr(self, 'property_field_map', {})
            db_field = property_field_map.get(sort_by, sort_by)
            order_field = f'-{db_field}' if sort_dir == 'desc' else db_field
            queryset = queryset.order_by(order_field)
        
        return queryset
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        meta = self.model._meta
        object_data = []

        if 'object_list' in context:
            for obj in context['object_list']:
                field_tuples = []
                for field_name, verbose_name in self.fields.items():
                    value = getattr(obj, field_name, '')
                    field_tuples.append((field_name, verbose_name, value))
                
                object_data.append({
                    'object': obj,
                    'fields': field_tuples,
                })
        
        url_namespace = f'{self.url_namespace}:' if self.url_namespace else ''
        context.update({
            'model_name': meta.model_name,
            'verbose_name': meta.verbose_name,
            'verbose_name_plural': meta.verbose_name_plural,
            'fields': self.fields,
            'object_data': object_data,
            'filter_fields': self.filter_fields,
            'search_fields': self.search_fields,
            'search_query': self.request.GET.get('search', ''),
            'extra_actions': self.extra_actions,
            'url_namespace': url_namespace,
        })
        
        if self.view_type == 'detail' and 'object' in context:
            obj = context['object']
            detail_fields = []
            for field_name, verbose_name in self.fields.items():
                value = getattr(obj, field_name, '')
                detail_fields.append((field_name, verbose_name, value))
            context['detail_fields'] = detail_fields
        
        if self.view_type in ('create', 'update') and self.inline_formsets:
            if not hasattr(self, 'formset_instances'):
                self.init_formsets()
            context['formsets'] = self.formset_instances
        
        if self.parent_view and hasattr(self.parent_view, 'get_context_data'):
            context = self.parent_view.get_context_data(context, self.request)
        
        return context
    
    def get_success_url(self):
        model_name = self.model._meta.model_name
        url_name = f'{self.url_namespace}:{model_name}-list' if self.url_namespace else f'{model_name}-list'
        return reverse(url_name)

    def get(self, request, *args, **kwargs):
        if self.view_type == 'create':
            self.object = None
        elif self.view_type == 'update':
            self.object = self.get_object()
        if self.inline_formsets:
            self.init_formsets()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if self.view_type == 'create':
            self.object = None
        elif self.view_type in ('update', 'delete'):
            self.object = self.get_object()
        
        # For delete views, skip form handling and let DeleteView handle it
        if self.view_type == 'delete':
            return super().post(request, *args, **kwargs)
        
        if self.inline_formsets:
            self.init_formsets()
        
        if request.htmx:
            formset_class = request.POST.get('formset_class')
            prefix = request.POST.get('prefix')
            form_index = int(request.POST.get('form_index', 0))
            form = self.add_formset(formset_class, prefix, form_index)
            if form:
                html = render_to_string(
                    'orange_sherbert/includes/form.html',
                    {'form': form},
                    request=request,
                )
                html = html.replace('__prefix__', str(form_index))
                return HttpResponse(html)
            return HttpResponse(f"Formset class '{formset_class}' not found", status=400)

        form = self.get_form()
        if self.inline_formsets:
            self.bind_formsets(request)
            if form.is_valid() and self.are_formsets_valid():
                return self.form_valid(form)
        else:
            if form.is_valid():
                return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        # Call parent_view's form_valid before save if it exists
        if self.parent_view and hasattr(self.parent_view, 'form_valid'):
            self.parent_view.form_valid(form)
        
        # Only save form if it has a save method (delete forms don't)
        if hasattr(form, 'save'):
            self.object = form.save()
            if self.inline_formsets:
                self.save_formsets()
            
            # Call parent_view's post_save if it exists (for M2M relations, etc.)
            if self.parent_view and hasattr(self.parent_view, 'post_save'):
                self.parent_view.post_save(self.object, self.request)
        
        return super().form_valid(form)

class _CRUDListView(_CRUDMixin, ListView):
    template_name = 'orange_sherbert/list.html'

class _CRUDDetailView(_CRUDMixin, DetailView):
    template_name = 'orange_sherbert/detail.html'

class _CRUDCreateView(_CRUDMixin, CreateView):
    template_name = 'orange_sherbert/create.html'

class _CRUDUpdateView(_CRUDMixin, UpdateView):
    template_name = 'orange_sherbert/update.html'

class _CRUDDeleteView(_CRUDMixin, DeleteView):
    template_name = 'orange_sherbert/delete.html'
    
    def get_context_data(self, **kwargs):
        # Ensure self.object is set before calling parent's get_context_data
        if not hasattr(self, 'object') or not self.object:
            self.object = self.get_object()
        return super().get_context_data(**kwargs)
    
    def form_valid(self, form):
        # Set self.object before calling parent's form_valid
        # DeleteView needs this to delete the object
        if not hasattr(self, 'object') or not self.object:
            self.object = self.get_object()
        # Call the actual delete logic from DeleteView
        return DeleteView.form_valid(self, form)


class CRUDView(View):
    model = None
    enforce_model_permissions = False
    fields = []
    form_fields = []
    extra_actions = []
    restricted_fields = []
    filter_fields = {}
    search_fields = []
    property_field_map = {}
    inline_formsets = []
    view_type = None
    url_namespace = None
    path_converter = 'int'  # 'int', 'uuid', 'slug', etc.
    list_template_name = 'orange_sherbert/list.html'
    detail_template_name = 'orange_sherbert/detail.html'
    create_template_name = 'orange_sherbert/create.html'
    update_template_name = 'orange_sherbert/update.html'
    delete_template_name = 'orange_sherbert/delete.html'
    
    def dispatch(self, request, *args, **kwargs):
        view_type = getattr(self, 'view_type', 'list')
        
        permission_map = {
            'list': 'view',
            'detail': 'view',
            'create': 'add',
            'update': 'change',
            'delete': 'delete',
        }
        view_classes = {
            'list': _CRUDListView,
            'detail': _CRUDDetailView,
            'create': _CRUDCreateView,
            'update': _CRUDUpdateView,
            'delete': _CRUDDeleteView,
        }
        view_class = view_classes[view_type]

        action = permission_map.get(view_type, 'view')
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        permission = f'{app_label}.{action}_{model_name}'
        
        if self.fields == '__all__':
            self.fields = {f.name: f.verbose_name for f in self.model._meta.fields if not f.primary_key}
        
        if self.restricted_fields:
            for field in self.restricted_fields:
                if field in self.fields:
                    del self.fields[field]
 
        if self.enforce_model_permissions and not request.user.has_perm(permission):
            return HttpResponseForbidden("You do not have permission to perform this action.")
        
        # For create/update views, replace properties with their underlying model fields
        form_fields = self.form_fields if self.form_fields else self.fields
        if view_type in ('create', 'update') and self.property_field_map:
            resolved_form_fields = {}
            for k, v in form_fields.items():
                if k in self.property_field_map:
                    db_field = self.property_field_map[k]
                    resolved_form_fields[db_field] = v
                else:
                    resolved_form_fields[k] = v
            form_fields = resolved_form_fields
        
        # Check if custom form_class is defined
        has_custom_form = hasattr(self, 'form_class') and self.form_class is not None
        
        view_kwargs = {
            'model': self.model,
            'filter_fields': self.filter_fields,
            'search_fields': self.search_fields,
            'extra_actions': self.extra_actions,
            'property_field_map': self.property_field_map,
            'view_type': view_type,
            'form_fields': self.form_fields,
            'url_namespace': self.url_namespace,
            'inline_formsets': self.inline_formsets,
            'parent_view': self,
        }
        
        # Only pass fields if no custom form_class (Django doesn't allow both)
        # form_class only applies to create/update views
        if has_custom_form and view_type in ('create', 'update'):
            view_kwargs['form_class'] = self.form_class
        else:
            view_kwargs['fields'] = form_fields if view_type in ('create', 'update', 'detail') else self.fields

        if view_type == 'list':
            view_kwargs['template_name'] = self.list_template_name
        elif view_type == 'detail':
            view_kwargs['template_name'] = self.detail_template_name
        elif view_type == 'create':
            view_kwargs['template_name'] = self.create_template_name
        elif view_type == 'update':
            view_kwargs['template_name'] = self.update_template_name
        elif view_type == 'delete':
            view_kwargs['template_name'] = self.delete_template_name
        
        view = view_class.as_view(**view_kwargs)
        return view(request, *args, **kwargs)
    
    @classmethod
    def get_model_name(cls):
        if cls.model is None:
            raise ValueError("model attribute must be set")
        return cls.model._meta.model_name
    
    @classmethod
    def get_urls(cls):
        model_name = cls.get_model_name()

        pk_type = cls.path_converter
        
        urls = [
            path(f'{model_name}/', cls.as_view(view_type='list'), name=f'{model_name}-list'),
            path(f'{model_name}/create/', cls.as_view(view_type='create'), name=f'{model_name}-create'),
            path(f'{model_name}/<{pk_type}:pk>/', cls.as_view(view_type='detail'), name=f'{model_name}-detail'),
            path(f'{model_name}/<{pk_type}:pk>/update/', cls.as_view(view_type='update'), name=f'{model_name}-update'),
            path(f'{model_name}/<{pk_type}:pk>/delete/', cls.as_view(view_type='delete'), name=f'{model_name}-delete'),
        ]
        
        if cls.extra_actions:
            for action in cls.extra_actions:
                action_name = action['name']
                view_class = action['view']
                
                url_name = f"{model_name}-{action_name}"
                url_path = f'{model_name}/<{pk_type}:pk>/{action_name}/'
                urls.append(path(url_path, view_class.as_view(), name=url_name))
        
        return urls