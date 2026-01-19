import os
import cloudinary.uploader
import cloudinary_config

BASE_DIR = "sku"

for sku in os.listdir(BASE_DIR):
    img_dir = os.path.join(BASE_DIR, sku, "images")

    if not os.path.isdir(img_dir):
        continue

    for img in os.listdir(img_dir):
        img_path = os.path.join(img_dir, img)

        try:
            upload = cloudinary.uploader.upload(
                img_path,
                folder=f"rightgifting/fashion/her/{sku}",
                public_id=os.path.splitext(img)[0]
            )

            print("Uploaded:", upload["secure_url"])

        except Exception as e:
            print("Failed:", img_path, e)
