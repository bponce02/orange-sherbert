from orange_sherbert.view import CRUDView
from .models import Book, Author

class BookCRUDView(CRUDView):
    model = Book
    fields = '__all__'

class AuthorCRUDView(CRUDView):
    model = Author
    fields = '__all__'
    