import base64
import cv2
import json
import fitz
import os

import numpy as np

from pypdf import PdfReader as PyPDFReader
from pdfrw import PdfReader, PdfWriter, PdfDict, PdfName
from pdf2image import convert_from_path
import os
from .general_utils import save_json

def validate_fieldname_images(image_paths, logger=None):
    """
    Validate that fieldname images contain visible text by checking file sizes and basic image properties.
    This is a simple check to ensure the images aren't blank.
    """
    if not image_paths:
        if logger:
            logger.error("CRITICAL: No fieldname images were generated!")
        return False
        
    validation_passed = True
    for img_path in image_paths:
        try:
            # Check if file exists and has reasonable size
            if not os.path.exists(img_path):
                if logger:
                    logger.error(f"Image file does not exist: {img_path}")
                validation_passed = False
                continue
                
            file_size = os.path.getsize(img_path)
            if file_size < 10000:  # Less than 10KB is probably too small for a form with field names
                if logger:
                    logger.warning(f"Image file suspiciously small ({file_size} bytes): {img_path}")
                    logger.warning("This may indicate field names are not visible in the image")
                validation_passed = False
                
        except Exception as e:
            if logger:
                logger.error(f"Error validating image {img_path}: {e}")
            validation_passed = False
            
    return validation_passed
def fill_pdf_fields_with_names_and_render_images(
    input_pdf,
    output_folder,
    pdf_name,
    logger,
    font_size=6,
):
    """
    Fills all AcroForm fields in the PDF with their field names using a bold and italic font,
    saves a new PDF, and renders each page as a PNG image.
    
    Args:
        input_pdf: Path to input PDF
        output_folder: Output directory for filled PDF and images
        pdf_name: Name of the PDF
        logger: Logger instance
        font_size: Font size for the field name text.
    """
    # Prepare output paths
    base_pdf_name = os.path.splitext(os.path.basename(input_pdf))[0]
    filled_pdf_path = os.path.join(
        output_folder, f"{base_pdf_name}_filled_with_field_names.pdf"
    )
    image_dir = os.path.join(output_folder, f"{base_pdf_name}_fieldname_images")
    os.makedirs(image_dir, exist_ok=True)

    # Diagnostic counters
    total_fields = 0
    processed_fields = 0
    failed_fields = 0

    # Fill PDF fields with their names using a Default Appearance string
    pdf = PdfReader(input_pdf)
    for page in pdf.pages:
        if "/Annots" in page:
            for annotation in page["/Annots"]:
                if annotation["/Subtype"] == "/Widget" and annotation.get("/T"):
                    total_fields += 1
                    try:
                        field_name = annotation["/T"].to_unicode()

                        # Use a reliable visual marker that will render in the final PNG.
                        display_value = f"{{{field_name}}}"
                        
                        # Set a default appearance string for font size and color.
                        # This helps with consistency but the visual marker is the primary identifier.
                        da_string = f"/Helv {font_size} Tf 0 g"

                        annotation.update(
                            PdfDict(
                                V=display_value,
                                Ff=1,  # Make field read-only
                                DA=da_string,
                                AP=None,  # Clear existing appearance to force regeneration
                            )
                        )
                        processed_fields += 1

                        if logger:
                            logger.debug(
                                f"Processed field: {field_name} -> {display_value}"
                            )

                    except Exception as e:
                        failed_fields += 1
                        if logger:
                            logger.warning(f"Failed to process field: {e}")
                        
    # Log field processing summary
    if logger:
        logger.info(f"Field processing summary: {processed_fields}/{total_fields} successful, {failed_fields} failed")
        if failed_fields > 0:
            logger.warning(f"{failed_fields} fields could not be processed - this may affect AI mapping quality")
    
    PdfWriter(filled_pdf_path, trailer=pdf).write()
    if logger:
        logger.info(f"PDF with field names written to: {filled_pdf_path}")

    # Render each page as PNG
    try:
        images = convert_from_path(filled_pdf_path, dpi=200)
        image_paths = []
        for i, img in enumerate(images):
            img_path = os.path.join(image_dir, f"page_{i+1}.png")
            img.save(img_path, 'PNG')
            image_paths.append(img_path)
            if logger:
                logger.info(f"Image saved to: {img_path}")
                
        # Validation check: Verify images contain visible field names
        validation_passed = validate_fieldname_images(image_paths, logger)
        if logger:
            if validation_passed:
                logger.info("SUCCESS: Fieldname image validation PASSED")
                logger.info("AI model should be able to map field names correctly")
            else:
                logger.error("FAILED: Fieldname image validation FAILED")
                logger.error("CRITICAL: Field names may not be visible in images!")
                logger.error("AI model will NOT be able to map field names correctly!")
                logger.error("This means the AI cannot see field locations on the form")
                
            logger.info(f"Check fieldname images in: {image_dir}")
            logger.info("Manually verify that field names are visible as blue/black text overlays")
            
        return image_paths
        
    except Exception as e:
        if logger:
            logger.error(f"Failed to convert PDF to images: {e}")
            logger.error("This will prevent proper field name mapping by the AI model")
        raise


def extract_pdf_fields(pdf_path, output_path, logger):
    try:
        reader = PyPDFReader(pdf_path)
        fields = reader.get_fields()
        # print(fields)
        field_mappings = {}
        for field_name, field in fields.items():
            field_type = field.get("/FT")
            result = {}
            result["field_type"] = field_type
            if field_type == "/Btn":
                widgets = field.get("/Kids", [field])
                valid_states = set()
                for widget in widgets:
                    widget_obj = widget.get_object()
                    states = widget_obj.get("/_States_")
                    if states:
                        for s in states:
                            valid_states.add(str(s))
                if valid_states:
                    result["possible_values"] = list(valid_states)
            field_mappings[field_name] = result
        print("PDF AcroForm fields were extracted successfully!")
        logger.info("PDF AcroForm fields were extracted successfully!")
        save_json(
            data=field_mappings,
            json_path=output_path,
            data_flag="PDF AcroForm fields",
            logger=logger,
        )
        field_mappings_json = json.dumps(field_mappings, indent=4)
        return field_mappings_json
    except Exception as error:
        print("Error while extracting PDF AcroForm fields!")
        print("{}".format(error))
        logger.error("Error while extracting PDF AcroForm fields!")
        logger.error("{}".format(error))
        raise


def fill_pdf_fields(input_pdf, output_pdf_path, data, data_flag, logger):
    try:
        field_map = {
            info["field_name"].split(".")[-1]: {
                "type": info["field_type"],
                "value": info["field_value"],
            }
            for info in data.values()
        }

        template = PdfReader(input_pdf)
        for page in template.pages:
            annotations = page.Annots
            if annotations:
                for annotation in annotations:
                    if annotation.Subtype == PdfName.Widget and annotation.T:
                        try:
                            field_name = annotation.T.to_unicode().strip("()")
                        except Exception:
                            field_name = (
                                str(annotation.T)
                                .encode("latin1")
                                .decode("utf-16")
                                .strip("()")
                            )

                        if field_name in field_map:
                            entry = field_map[field_name]
                            value = entry["value"]
                            field_type = entry["type"]
                            if field_type == "/Tx":
                                annotation.update(PdfDict(V=str(value), AP=None))
                            elif field_type == "/Btn":
                                data_value = value.lstrip("/")
                                annotation.update(
                                    PdfDict(
                                        V=PdfName(data_value), AS=PdfName(data_value)
                                    )
                                )
        PdfWriter().write(output_pdf_path, template)
        print("PDF was filled successfully for {}!".format(data_flag))
        logger.info("PDF was filled successfully for {}!".format(data_flag))
    except Exception as error:
        print("Error while filling PDF for {}!".format(data_flag))
        print("{}".format(error))
        logger.error("Error while filling PDF for {}!".format(data_flag))
        logger.error("{}".format(error))
        raise


def pdf_to_images(pdf_path, image_directory, data_flag, logger):
    try:
        doc = fitz.open(pdf_path)
        for idx, page in enumerate(doc):
            image_filepath = os.path.join(
                image_directory, "Page{}.jpg".format(str(idx + 1))
            )
            pix = page.get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72))
            image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            cv2.imwrite(image_filepath, image)
        doc.close()
        print("PDF was converted to images successfully for {}!".format(data_flag))
        logger.info(
            "PDF was converted to images successfully for {}!".format(data_flag)
        )
    except Exception as error:
        print("Error while converting PDF to images for {}!".format(data_flag))
        print("{}".format(error))
        logger.error("Error while converting PDF to images for {}!".format(data_flag))
        logger.error("{}".format(error))
        raise


def pdf_to_base64(data_directory, logger):
    try:
        image_data = {}
        for file_name in os.listdir(data_directory):
            if file_name.endswith(".jpg"):
                with open(os.path.join(data_directory, file_name), "rb") as f:
                    base64_image = base64.b64encode(f.read()).decode("utf-8")
                image_data[file_name] = base64_image
        print("PDF was converted to Base64 images successfully!")
        logger.info("PDF was converted to Base64 images successfully!")
        return image_data
    except Exception as error:
        print("Error while converting PDF to Base64 images!")
        print("{}".format(error))
        logger.error("Error while converting PDF to Base64 images!")
        logger.error("{}".format(error))
        raise
