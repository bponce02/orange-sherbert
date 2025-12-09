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

    def get_queryset(self, **kwargs):
        super().get_queryset()
        queryset = self.model.objects.all()
        
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
                field_tuples = [(field_name, verbose_name, getattr(obj, field_name, '')) 
                               for field_name, verbose_name in self.fields.items()]
                object_data.append({'object': obj, 'fields': field_tuples})
        
        context.update({
            'model_name': meta.model_name,
            'verbose_name': meta.verbose_name,
            'verbose_name_plural': meta.verbose_name_plural,
            'fields': self.fields,
            'object_data': object_data,
            'filter_fields': self.filter_fields,
            'search_fields': self.search_fields,
            'search_query': self.request.GET.get('search', ''),
        })
        return context
    
    def get_success_url(self):
        model_name = self.model._meta.model_name
        return reverse(f'{model_name}-list')


class CRUDView(View):
    model = None
    enforce_model_permissions = False
    fields = []
    objects_data = None
    restricted_fields = []
    filter_fields = []
    search_fields = []
    view_type = None
    
    templates = {
        'list': 'orange_sherbert/list.html',
        'detail': 'orange_sherbert/detail.html',
        'create': 'orange_sherbert/create.html',
        'update': 'orange_sherbert/update.html',
        'delete': 'orange_sherbert/delete.html',
    }
    
    _base_view_classes = {
        'list': ListView,
        'detail': DetailView,
        'create': CreateView,
        'update': UpdateView,
        'delete': DeleteView,
    }
    
    @classmethod
    def _get_view_classes(cls):
        return {
            view_type: type(
                f'_CRUD{base_class.__name__}',
                (_CRUDMixin, base_class),
                {'fields': None, 'filter_fields': None, 'search_fields': None}
            )
            for view_type, base_class in cls._base_view_classes.items()
        }
    
    def dispatch(self, request, *args, **kwargs):
        view_type = getattr(self, 'view_type', 'list')
        
        permission_map = {
            'list': 'view',
            'detail': 'view',
            'create': 'add',
            'update': 'change',
            'delete': 'delete',
        }
        
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
        
        view_classes = self._get_view_classes()
        view_class = view_classes[view_type]
        
        view_kwargs = {
            'model': self.model,
            'template_name': self.templates[view_type],
            'fields': self.fields,
            'filter_fields': self.filter_fields,
            'search_fields': self.search_fields,
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

        return [
            path(f'{app_name}/{model_name}/', cls.as_view(view_type='list'), name=f'{model_name}-list'),
            path(f'{app_name}/{model_name}/create/', cls.as_view(view_type='create'), name=f'{model_name}-create'),
            path(f'{app_name}/{model_name}/<int:pk>/', cls.as_view(view_type='detail'), name=f'{model_name}-detail'),
            path(f'{app_name}/{model_name}/<int:pk>/update/', cls.as_view(view_type='update'), name=f'{model_name}-update'),
            path(f'{app_name}/{model_name}/<int:pk>/delete/', cls.as_view(view_type='delete'), name=f'{model_name}-delete'),
        ]
