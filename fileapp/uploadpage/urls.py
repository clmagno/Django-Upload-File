from django.urls import path

from . views import upload_image, classify_image

urlpatterns = [
    path('', upload_image, name='upload_image'),
    path('<int:id>', classify_image, name='classify_image'),
]