from django.db import models
import os
from django.conf import settings
from django.db import models

class UploadedImage(models.Model):
    id = models.AutoField(primary_key=True)
    image = models.ImageField(upload_to=os.path.join("static/"+settings.MEDIA_ROOT+'images/'))

    def __str__(self):
        return str(self.id)