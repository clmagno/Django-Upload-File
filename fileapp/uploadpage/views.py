from django.shortcuts import render, redirect
from .forms import ImageUploadForm
from .models import UploadedImage
from django.shortcuts import render
from django.http import JsonResponse
from tensorflow.keras.models import load_model, Model
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.vgg16 import preprocess_input
import numpy as np
from . import apps
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.applications.vgg16 import VGG16, preprocess_input
from keras.preprocessing.image import ImageDataGenerator
from keras.callbacks import ModelCheckpoint, EarlyStopping
from keras.layers import Dense, Dropout, Flatten
from pathlib import Path
from django.shortcuts import get_object_or_404
import io
import numpy as np
from django.http import HttpResponse

def create_model(input_shape, n_classes, optimizer='rmsprop', fine_tune=0):
    """
    Compiles a model integrated with VGG16 pretrained layers

    input_shape: tuple - the shape of input images (width, height, channels)
    n_classes: int - number of classes for the output layer
    optimizer: string - instantiated optimizer to use for training. Defaults to 'RMSProp'
    fine_tune: int - The number of pre-trained layers to unfreeze.
                If set to 0, all pretrained layers will freeze during training
    """

    # Pretrained convolutional layers are loaded using the Imagenet weights.
    # Include_top is set to False, in order to exclude the model's fully-connected layers.
    conv_base = VGG16(include_top=False,
                      weights='imagenet',
                      input_shape=input_shape)

    # Defines how many layers to freeze during training.
    # Layers in the convolutional base are switched from trainable to non-trainable
    # depending on the size of the fine-tuning parameter.
    if fine_tune > 0:
        for layer in conv_base.layers[:-fine_tune]:
            layer.trainable = False
    else:
        for layer in conv_base.layers:
            layer.trainable = False

    # Create a new 'top' of the model (i.e. fully-connected layers).
    # This is 'bootstrapping' a new top_model onto the pretrained layers.
    top_model = conv_base.output
    top_model = Flatten(name="flatten")(top_model)
    top_model = Dense(4096, activation='relu')(top_model)
    top_model = Dense(1072, activation='relu')(top_model)
    top_model = Dropout(0.2)(top_model)
    output_layer = Dense(n_classes, activation='softmax')(top_model)

    # Group the convolutional base and new fully-connected layers into a Model object.
    model = Model(inputs=conv_base.input, outputs=output_layer)

    # Compiles the model for training.
    model.compile(optimizer=optimizer,
                  loss='categorical_crossentropy',
                  metrics=['accuracy'])
    return model

def classify_image(request,id):
    if request.method == 'POST':
        # Set batch size
        BATCH_SIZE = 32
        # Define image data generators for training, validation, and testing
        train_generator = ImageDataGenerator(
            rotation_range=30,
            width_shift_range=0.2,
            height_shift_range=0.2,
            shear_range=0.2,
            zoom_range=0.2,
            horizontal_flip=True,
            fill_mode='nearest',
            preprocessing_function=preprocess_input
        )

        valid_generator = ImageDataGenerator(
            rescale=1. / 255,
            preprocessing_function=preprocess_input
        )

        test_generator = ImageDataGenerator(
            rescale=1. / 255,
            preprocessing_function=preprocess_input
        )

        # Set directory paths for training, validation, and testing
        train_data_dir = 'static/datasets/train'
        valid_data_dir = 'static/datasets/valid'
        test_data_dir = 'static/datasets/test'

        # Create image data generators for training, validation, and testing
        train_gen = train_generator.flow_from_directory(
            train_data_dir,
            target_size=(224, 224),
            class_mode='categorical',
            classes=['Healthy', 'LeafSpot', 'OtherDisease'],
            batch_size=BATCH_SIZE,
            shuffle=True,
            seed=42
        )

        valid_gen = valid_generator.flow_from_directory(
            valid_data_dir,
            target_size=(224, 224),
            class_mode='categorical',
            classes=['Healthy', 'LeafSpot', 'OtherDisease'],
            batch_size=BATCH_SIZE,
            shuffle=True,
            seed=42
        )

        test_gen = test_generator.flow_from_directory(
            test_data_dir,
            target_size=(224, 224),
            class_mode=None,
            classes=['Healthy', 'LeafSpot', 'OtherDisease'],
            batch_size=BATCH_SIZE,
            shuffle=False,
            seed=42
        )

        # Define input shape, optimizer, and number of classes
        input_shape = (224, 224, 3)
        optimizer = Adam(learning_rate=0.002)
        n_classes = 3

        # Create VGG16 model without fine-tuning
        model = create_model(input_shape, n_classes, optimizer, fine_tune=0)

        # Load image file from POST request

        if id == '-1':
            return HttpResponse("Invalid image ID")
        try:
            mod = UploadedImage.objects.get(id=id+1)
        except UploadedImage.DoesNotExist:
            return HttpResponse("Image not found")

        # mod = UploadedImage.objects.get(id=id)
        img_data = mod.image.read()
        img_file = io.BytesIO(img_data)
        img = image.load_img(img_file, target_size=(224, 224))

        # Convert image to array and preprocess
        x = image.img_to_array(img)
        x = np.expand_dims(x, axis=0)
        x = preprocess_input(x)

        # Make prediction and get class index
        predictions = model.predict(x)
        class_index = np.argmax(predictions)

        # Get predicted class name and create context for response
        class_names = ['Healthy', 'LeafSpot', 'OtherDisease']
        class_name = class_names[class_index]
        context = {'classification_result': class_name,
                   'image_path': mod.image.url}

        # Render HTML template with classification result
        return render(request, 'upload_image.html', context)

    else:
        # Render HTML template for uploading image
        return render(request, 'upload_image.html')

def upload_image(request):
    classification_result = None
    images = UploadedImage.objects.last()
    print(f"last object from model {images}")
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            print("form is valid. Trying to save image")
            # create a new UploadedImage object and save it
            image_model = UploadedImage(image=request.FILES['image'])
            image_model.save()
            print("image saved")
    else:
        form = ImageUploadForm()

    context = {
        'form': form,
        'images': images,
        'classification_result': classification_result,
    }

    return render(request, 'upload_image.html', context)
