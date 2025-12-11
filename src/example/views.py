from orange_sherbert.view import CRUDView
from .models import Book, Author, BookRequest
from django.views import View
from django.shortcuts import redirect

class OrderOnlineView(View):
    def post(self, request, pk):
        book = Book.objects.get(pk=pk)
        return redirect(f'https://www.barnesandnoble.com/s/{book.title}')

class CheckOutView(View):
    def post(self, request, pk):
        book = Book.objects.get(pk=pk)
        book.checked_out = True
        book.save()
        return redirect(request.META.get('HTTP_REFERER', 'book-list'))

class CheckInView(View):
    def post(self, request, pk):
        book = Book.objects.get(pk=pk)
        book.checked_out = False
        book.save()
        return redirect(request.META.get('HTTP_REFERER', 'book-list'))

class BookCRUDView(CRUDView):
    model = Book
    fields = '__all__'
    filter_fields = ['author', 'checked_out']
    search_fields = ['title', 'isbn']
    restricted_fields = {'ordered_from': 'can_view_ordered_from'}
    
    inline_formsets = [
        {
            'model': BookRequest,
            'fields': ['requester_name', 'requester_email', 'priority'],
            'can_delete': True,
        }
    ]

    extra_actions = [
        {
            'name': 'order-online',
            'view': OrderOnlineView,
            'label': 'Order Online',
            'method': 'POST',
            # 'permission': 'can_order_online',
        },
        {
            'name': 'check-in',
            'label': 'Check In',
            'view': CheckInView,
            'method': 'POST',
            #'permission': 'can_check_in'
        },
        {
            'name': 'check-out',
            'label': 'Check Out',
            'view': CheckOutView,
            'method': 'POST',
            #'permission': 'can_check_out'
        }
    ]

class AuthorCRUDView(CRUDView):
    model = Author
    fields = '__all__'
    search_fields = ['name']