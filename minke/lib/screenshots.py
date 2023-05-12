from PIL import Image
from PIL import ImageChops

def images_are_same(path_1, path_2):
    image_one = Image.open(path_1)
    image_two = Image.open(path_2)

    diff = ImageChops.difference(image_one, image_two)

    if diff.getbbox():
        return False
    else:
        return True
