from django.db import models

class Book(models.Model):
    title = models.CharField(max_length=100,verbose_name='Title')
    author = models.ForeignKey('Author', on_delete=models.CASCADE,verbose_name='Author')
    isbn = models.CharField(max_length=13,verbose_name='ISBN')
    price = models.DecimalField(max_digits=10, decimal_places=2,verbose_name='Price')
    pub_date = models.DateField(verbose_name='Publication Date')
    checked_out = models.BooleanField(default=False,verbose_name='Checked Out')
    ordered_from = models.CharField(max_length=100, blank=True, null=True, verbose_name='Ordered From')
    class Meta:
        verbose_name = 'Book'
        verbose_name_plural = 'Books'
        permissions = [
            ('can_view_ordered_from', 'Can view ordered from field'),
        ]
    
    def __str__(self):
        return self.title

class Author(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

