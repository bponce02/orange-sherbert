from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import CreateView
from django.views.generic import UpdateView
from django.views.generic import DeleteView
from django.views import View
from django.urls import path, reverse
from django.db.models import Q

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
        
        return queryset
        
    def get_context_data(self, **kwargs):
        super().get_context_data(**kwargs)
        context = super().get_context_data(**kwargs)
        meta = self.model._meta
        context.update({
            'model_name': meta.model_name,
            'verbose_name': meta.verbose_name,
            'verbose_name_plural': meta.verbose_name_plural,
            'filter_fields': self.filter_fields,
            })
        return context
    
    def get_success_url(self):
        model_name = self.model._meta.model_name
        return reverse(f'{model_name}-list')


class CRUDView(View):
    model = None
    fields = []
    filter_fields = []
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
                {'fields': None, 'filter_fields': None}
            )
            for view_type, base_class in cls._base_view_classes.items()
        }
    
    def dispatch(self, request, *args, **kwargs):
        view_type = getattr(self, 'view_type', 'list')
        
        view_classes = self._get_view_classes()
        view_class = view_classes[view_type]
        
        view_kwargs = {
            'model': self.model,
            'template_name': self.templates[view_type],
            'fields': self.fields,
            'filter_fields': self.filter_fields
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
        
        return [
            path(f'{model_name}/', cls.as_view(view_type='list'), name=f'{model_name}-list'),
            path(f'{model_name}/create/', cls.as_view(view_type='create'), name=f'{model_name}-create'),
            path(f'{model_name}/<int:pk>/', cls.as_view(view_type='detail'), name=f'{model_name}-detail'),
            path(f'{model_name}/<int:pk>/update/', cls.as_view(view_type='update'), name=f'{model_name}-update'),
            path(f'{model_name}/<int:pk>/delete/', cls.as_view(view_type='delete'), name=f'{model_name}-delete'),
        ]
