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
        
        formsets = []
        for formset_config in self.inline_formsets:
            FormSet = inlineformset_factory(
                self.model,
                formset_config['model'],
                fields=formset_config['fields'],
                extra=1,
                can_delete=formset_config.get('can_delete', True),
            )
            
            formset_name = formset_config['model'].__name__.lower() + '_formset'
            
            if self.request.POST:
                formset = FormSet(self.request.POST, instance=instance)
            else:
                formset = FormSet(instance=instance)
            
            formsets.append({
                'name': formset_name,
                'formset': formset,
                'verbose_name': formset_config['model']._meta.verbose_name,
                'verbose_name_plural': formset_config['model']._meta.verbose_name_plural,
            })
        
        return formsets
    
    def _save_formsets(self, formsets):
        all_valid = True
        for formset_data in formsets:
            formset = formset_data['formset']
            if formset.is_valid():
                formset.instance = self.object
                formset.save()
            else:
                all_valid = False
        return all_valid
    
    
    def form_valid(self, form):
        view_type = self.view_type
        if view_type in ('create', 'update') and self.inline_formsets:
            formsets = self._get_formsets(instance=self.object)
            
            self.object = form.save()
            
            if self._save_formsets(formsets):
                return super().form_valid(form)
            else:
                return self.form_invalid(form)
        
        return super().form_valid(form)

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
