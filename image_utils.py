import base64
import os

def encode_images_to_base64(image_paths):
    """
    Given a list of image file paths, return a dict {filename: base64_string}
    """
    image_data = {}
    for img_path in image_paths:
        with open(img_path, "rb") as img_file:
            b64 = base64.b64encode(img_file.read()).decode("utf-8")
            image_data[os.path.basename(img_path)] = b64
    return image_data
