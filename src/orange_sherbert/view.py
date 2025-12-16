from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import CreateView
from django.views.generic import UpdateView
from django.views.generic import DeleteView
from django.views import View
from django.urls import path, reverse
from django.db.models import Q
from django.http import HttpResponseForbidden


class _CRUDMixin:
    fields = None
    form_fields = None
    filter_fields = {}
    search_fields = []
    extra_actions = []
    property_field_map = {}
    view_type = None
    url_namespace = None

    def get_queryset(self, **kwargs):
        queryset = super().get_queryset()
        
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
        
        return context
    
    def get_success_url(self):
        model_name = self.model._meta.model_name
        url_name = f'{self.url_namespace}:{model_name}-list' if self.url_namespace else f'{model_name}-list'
        return reverse(url_name)

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
    form_fields = []
    extra_actions = []
    restricted_fields = []
    filter_fields = {}
    search_fields = []
    property_field_map = {}
    view_type = None
    url_namespace = None
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
        
        view_kwargs = {
            'model': self.model,
            'fields': form_fields if view_type in ('create', 'update', 'detail') else self.fields,
            'filter_fields': self.filter_fields,
            'search_fields': self.search_fields,
            'extra_actions': self.extra_actions,
            'property_field_map': self.property_field_map,
            'view_type': view_type,
            'form_fields': self.form_fields,
            'url_namespace': self.url_namespace,
        }

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

        urls = [
            path(f'{model_name}/', cls.as_view(view_type='list'), name=f'{model_name}-list'),
            path(f'{model_name}/create/', cls.as_view(view_type='create'), name=f'{model_name}-create'),
            path(f'{model_name}/<int:pk>/', cls.as_view(view_type='detail'), name=f'{model_name}-detail'),
            path(f'{model_name}/<int:pk>/update/', cls.as_view(view_type='update'), name=f'{model_name}-update'),
            path(f'{model_name}/<int:pk>/delete/', cls.as_view(view_type='delete'), name=f'{model_name}-delete'),
        ]
        
        if cls.extra_actions:
            for action in cls.extra_actions:
                action_name = action['name']
                view_class = action['view']
                
                url_name = f"{model_name}-{action_name}"
                url_path = f'{model_name}/<int:pk>/{action_name}/'
                urls.append(path(url_path, view_class.as_view(), name=url_name))
        
        return urls