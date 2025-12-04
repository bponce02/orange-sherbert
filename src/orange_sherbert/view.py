from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import CreateView
from django.views.generic import UpdateView
from django.views.generic import DeleteView
from django.views import View
from django.urls import path

class CRUDView(View):
    model = None
    template_name = None
    
    detail_view = DetailView
    list_view = ListView
    create_view = CreateView
    update_view = UpdateView
    delete_view = DeleteView
    
    detail_template = 'orange_sherbert/detail.html'
    list_template = 'orange_sherbert/list.html'
    create_template = 'orange_sherbert/create.html'
    update_template = 'orange_sherbert/update.html'
    delete_template = 'orange_sherbert/delete.html'
    
    @classmethod
    def get_model_name(cls):
        if cls.model is None:
            raise ValueError("model attribute must be set")
        return cls.model._meta.model_name
    
    @classmethod
    def get_urls(cls):
        model_name = cls.get_model_name()
        
        return [
            path(f'{model_name}/', cls.list_view.as_view(model=cls.model, template_name=cls.list_template), name=f'{model_name}-list'),
            path(f'{model_name}/create/', cls.create_view.as_view(model=cls.model, template_name=cls.create_template), name=f'{model_name}-create'),
            path(f'{model_name}/<int:pk>/', cls.detail_view.as_view(model=cls.model, template_name=cls.detail_template), name=f'{model_name}-detail'),
            path(f'{model_name}/<int:pk>/update/', cls.update_view.as_view(model=cls.model, template_name=cls.update_template), name=f'{model_name}-update'),
            path(f'{model_name}/<int:pk>/delete/', cls.delete_view.as_view(model=cls.model, template_name=cls.delete_template), name=f'{model_name}-delete'),
        ]

