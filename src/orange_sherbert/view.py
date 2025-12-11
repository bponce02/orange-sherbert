from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import CreateView
from django.views.generic import UpdateView
from django.views.generic import DeleteView
from django.views import View
from django.urls import path, reverse
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.forms import inlineformset_factory


class _CRUDMixin:
    fields = None
    filter_fields = []
    search_fields = []
    extra_actions = []
    inline_formsets = []
    view_type = None

    def _get_formsets(self, instance=None):
        if not self.inline_formsets:
            return []
        
        top_level_configs = [c for c in self.inline_formsets if not c.get('nested_under')]
        nested_configs = {}
        for c in self.inline_formsets:
            if c.get('nested_under'):
                parent_model = c['nested_under']
                if parent_model not in nested_configs:
                    nested_configs[parent_model] = []
                nested_configs[parent_model].append(c)
        
        formsets = []
        
        for config in top_level_configs:
            FormSetClass = inlineformset_factory(
                self.model,
                config['model'],
                fields=config['fields'],
                extra=config.get('extra', 1),
                can_delete=config.get('can_delete', True),
            )
            
            prefix = config.get('name', config['model'].__name__.lower() + '_formset')
            
            if self.request.POST:
                formset = FormSetClass(self.request.POST, instance=instance, prefix=prefix)
            else:
                formset = FormSetClass(instance=instance, prefix=prefix)
            
            if config['model'] in nested_configs:
                for i, form in enumerate(formset):
                    form.nested_formsets = []
                    for nested_config in nested_configs[config['model']]:
                        NestedFormSetClass = inlineformset_factory(
                            config['model'],
                            nested_config['model'],
                            fields=nested_config['fields'],
                            extra=nested_config.get('extra', 1),
                            can_delete=nested_config.get('can_delete', True),
                        )
                        
                        nested_prefix = f"{form.prefix}-{nested_config['model'].__name__.lower()}_formset"
                        
                        nested_instance = form.instance
                        
                        if self.request.POST:
                            nested_formset = NestedFormSetClass(
                                self.request.POST, 
                                instance=nested_instance, 
                                prefix=nested_prefix
                            )
                        else:
                            nested_formset = NestedFormSetClass(
                                instance=nested_instance, 
                                prefix=nested_prefix
                            )
                        
                        nested_formset.verbose_name = nested_config['model']._meta.verbose_name
                        nested_formset.verbose_name_plural = nested_config['model']._meta.verbose_name_plural
                        
                        form.nested_formsets.append(nested_formset)
            
            formsets.append({
                'name': prefix,
                'formset': formset,
                'verbose_name': config['model']._meta.verbose_name,
                'verbose_name_plural': config['model']._meta.verbose_name_plural,
                'model': config['model'],
                'config': config,
            })
        
        return formsets
    
    def _save_formsets(self, formsets):
        def _save_formset(formset):
            if not formset.is_valid():
                return False
            
            formset.save()
            
            for form in formset:
                if form.instance.pk and not form.cleaned_data.get('DELETE'):
                    if hasattr(form, 'nested_formsets'):
                        for nested_formset in form.nested_formsets:
                            nested_formset.instance = form.instance
                            if not _save_formset(nested_formset):
                                return False
            
            return True
        
        all_valid = True
        
        for formset_data in formsets:
            formset = formset_data['formset']
            if not formset.is_valid():
                all_valid = False
            
            for form in formset:
                if hasattr(form, 'nested_formsets'):
                    for nested_formset in form.nested_formsets:
                        if not nested_formset.is_valid():
                            all_valid = False
        
        if not all_valid:
            return False

        for formset_data in formsets:
            formset = formset_data['formset']
            formset.instance = self.object
            if not _save_formset(formset):
                return False
        
        return True
    
    def form_valid(self, form):
        view_type = self.view_type
        if view_type in ('create', 'update') and self.inline_formsets:
            formsets = self._get_formsets(instance=self.object)
            
            self.object = form.save()
            
            if self._save_formsets(formsets):
                return super().form_valid(form)
            else:
                return self.form_invalid(form, formsets=formsets)
        
        return super().form_valid(form)

    def form_invalid(self, form, formsets=None):
        return self.render_to_response(self.get_context_data(form=form, formsets=formsets))

    def get_queryset(self, **kwargs):
        queryset = super().get_queryset()
        
        filter_fields = self.filter_fields
        if filter_fields:
            for field in filter_fields:
                field_value = self.request.GET.get(field)
                if field_value:
                    queryset = queryset.filter(**{field: field_value})
        
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
            order_field = f'-{sort_by}' if sort_dir == 'desc' else sort_by
            queryset = queryset.order_by(order_field)
        
        return queryset
        
    def get_context_data(self, **kwargs):
        # Allow formsets to be passed in to avoid double-creation and preserve errors
        formsets = kwargs.pop('formsets', None)
        
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
        })
        
        view_type = self.view_type  
        if view_type in ('create', 'update'):
            if formsets is None:
                formsets = self._get_formsets(instance=getattr(self, 'object', None))
            context['formsets'] = formsets
        
        return context
    
    def get_success_url(self):
        model_name = self.model._meta.model_name
        return reverse(f'{model_name}-list')

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

class CRUDView(View):
    model = None
    enforce_model_permissions = False
    fields = []
    extra_actions = []
    restricted_fields = []
    filter_fields = []
    search_fields = []
    inline_formsets = []
    view_type = None
    
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
        
        view_kwargs = {
            'model': self.model,
            'fields': self.fields,
            'filter_fields': self.filter_fields,
            'search_fields': self.search_fields,
            'extra_actions': self.extra_actions,
            'inline_formsets': self.inline_formsets,
            'view_type': view_type,
        }
        
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
        app_name = cls.model._meta.app_label

        urls = [
            path(f'{app_name}/{model_name}/', cls.as_view(view_type='list'), name=f'{model_name}-list'),
            path(f'{app_name}/{model_name}/create/', cls.as_view(view_type='create'), name=f'{model_name}-create'),
            path(f'{app_name}/{model_name}/<int:pk>/', cls.as_view(view_type='detail'), name=f'{model_name}-detail'),
            path(f'{app_name}/{model_name}/<int:pk>/update/', cls.as_view(view_type='update'), name=f'{model_name}-update'),
            path(f'{app_name}/{model_name}/<int:pk>/delete/', cls.as_view(view_type='delete'), name=f'{model_name}-delete'),
        ]
        
        if cls.extra_actions:
            for action in cls.extra_actions:
                action_name = action['name']
                view_class = action['view']
                
                url_name = f"{model_name}-{action_name}"
                url_path = f'{app_name}/{model_name}/<int:pk>/{action_name}/'
                urls.append(path(url_path, view_class.as_view(), name=url_name))
        
        return urls
