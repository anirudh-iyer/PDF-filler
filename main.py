import argparse
import datetime
import json
import os
import pytz
import shutil
import uuid

from dotenv import load_dotenv, find_dotenv
from openai import AzureOpenAI

from utils.genai_utils import generate_human_readable_labels, generate_synthetic_data
from utils.image_utils import encode_images_to_base64
from utils.validation_utils import validate_filled_pdf_mapping
from utils.validation_reporter import ValidationReporter
from utils.general_utils import (
    make_directory,
    save_json,
    upload_to_azure_blob_storage,
)
from utils.logger_utils import CustomLogger
from utils.pdf_utils import (
    extract_pdf_fields,
    fill_pdf_fields,
    pdf_to_images,
    pdf_to_base64,
    fill_pdf_fields_with_names_and_render_images,
)

def extract_persona_fields_from_json(output_json):
    # Heuristic: treat any field with values that look like name, ssn, address, etc. as persona fields
    persona = {}
    for label, info in output_json.items():
        # label: human-readable label; info: {field_name, field_type, field_value}
        l = label.lower()
        v = info["field_value"]
        if any(k in l for k in ["name", "ssn", "social security", "address", "city", "state", "zip", "employer", "dob", "date of birth", "policy", "property", "wages", "salary", "income", "ein", "phone"]):
            persona[label] = v
    return persona

def merge_persona(persona, new_persona):
    # New fields from new_persona are added to persona
    for k, v in new_persona.items():
        persona[k] = v
    return persona

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input_pdf",
        type=str,
        default="data/1040-ScheduleC/1040-ScheduleC.pdf",
        help="Single PDF file to process"
    )
    parser.add_argument(
        "--batch_directory",
        type=str,
        default=None,
        help="Directory containing multiple PDFs to process in batch"
    )
    parser.add_argument(
        "--number_of_variants",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--prompt_filepath",
        type=str,
        default="data/prompts.json",
    )
    parser.add_argument(
        "--output_directory",
        type=str,
        default="output",
    )
    parser.add_argument(
        "--disable_validation",
        action="store_true",
        default=False,
        help="Disable PDF validation and correction logic (validation enabled by default)"
    )
    parser.add_argument(
        "--field_font_size",
        type=int,
        default=8,
        help="Font size for field names in fieldname images (default: 8)"
    )
    args = parser.parse_args()
    return args


def process_single_pdf(pdf_path, args, logger, client, prompts):
    """Process a single PDF file and generate synthetic data"""
    
    document_type = os.path.basename(pdf_path)
    document_type = document_type.split("/")[-1].split(".")[0]

    output_directory = os.path.join(os.path.abspath(args.output_directory))

    # Generate field-name-overlaid images for the input PDF
    fieldname_images = fill_pdf_fields_with_names_and_render_images(
        pdf_path,
        output_directory,
        os.path.basename(pdf_path),
        logger=logger,
        font_size=args.field_font_size,
    )
    
    # Critical validation: Check if field names are visible in images
    if not fieldname_images:
        logger.error("CRITICAL: No fieldname images were generated!")
        logger.error("Cannot proceed - AI model needs fieldname images for mapping")
        raise Exception("Failed to generate fieldname images - this will break AI field mapping")
        
    # Additional validation for image quality
    from utils.pdf_utils import validate_fieldname_images
    if not validate_fieldname_images(fieldname_images, logger):
        logger.warning("WARNING: Fieldname images may not contain visible field names")
        logger.warning("This could result in poor AI model performance for field mapping")
        logger.warning("The AI needs to see field names overlaid on the form to work properly")
    
    # Encode PNGs as base64 for model input
    fieldname_image_data = encode_images_to_base64(fieldname_images)

    make_directory(directory=output_directory)
    output_directory = os.path.join(output_directory, document_type)
    make_directory(directory=output_directory)

    print(f"\n-------------------------------------")
    print(f"Processing: {document_type}")
    print(f"PDF Path: {pdf_path}")
    print(f"Output Directory: {output_directory}")
    print("-------------------------------------")

    logger.info("-------------------------------------")
    logger.info(f"Processing: {document_type}")
    logger.info(f"PDF Path: {pdf_path}")
    logger.info(f"Output Directory: {output_directory}")
    logger.info("-------------------------------------")

    image_directory = os.path.join(output_directory, "image_data")
    pdf_directory = os.path.join(output_directory, "pdf_data")
    json_directory = os.path.join(output_directory, "json_data")

    make_directory(directory=image_directory)
    make_directory(directory=pdf_directory)
    make_directory(directory=json_directory)

    pdf_path_abs = os.path.abspath(pdf_path)
    data_directory = os.path.dirname(pdf_path_abs)

    field_mappings_path = os.path.join(
        data_directory, f"{document_type}_field_mappings.json"
    )
    human_readable_labels_path = os.path.join(
        data_directory, f"{document_type}_human_readable_labels.json"
    )

    # Extract or load field mappings
    if os.path.exists(field_mappings_path):
        print("Field mappings already exist!")
        logger.info("Field mappings already exist!")
        with open(field_mappings_path, "r", encoding='utf-8') as json_file:
            field_mappings_json = json_file.read()
        print("Field mappings were read from JSON file successfully!")
        logger.info("Field mappings were read from JSON file successfully!")
    else:
        field_mappings_json = extract_pdf_fields(
            pdf_path=pdf_path_abs, output_path=field_mappings_path, logger=logger
        )

    # Generate or load human readable labels
    if os.path.exists(human_readable_labels_path):
        print("Human readable labels already exist!")
        logger.info("Human readable labels already exist!")
        with open(human_readable_labels_path, "r", encoding='utf-8') as json_file:
            human_readable_labels = json_file.read()
        print("Human readable labels were read from JSON file successfully!")
        logger.info("Human readable labels were read from JSON file successfully!")
    else:
        human_readable_prompt = prompts.get("default", {}).get(
            "humanReadableLabels", ""
        )

        human_readable_prompt = human_readable_prompt.format(
            document_type=document_type
        )

        human_readable_labels = generate_human_readable_labels(
            client=client,
            image_data=fieldname_image_data,
            document_type=document_type,
            human_readable_prompt=human_readable_prompt,
            output_path=human_readable_labels_path,
            logger=logger,
            field_mappings_json=field_mappings_json,
        )

    total_samples = args.number_of_variants

    # Initialize validation reporter if validation is enabled
    validation_reporter = None
    if not args.disable_validation:
        validation_reporter = ValidationReporter(
            output_directory=output_directory,
            document_type=document_type
        )
        logger.info("Validation enabled - initialized validation reporter")
    else:
        logger.info("Validation disabled via --disable_validation flag")

    # Generate synthetic data variants
    for idx in range(1, total_samples + 1):
        
        persona_dir = os.path.join(args.output_directory, "persona_variants")
        os.makedirs(persona_dir, exist_ok=True)
        persona_json_path = os.path.join(persona_dir, f"persona_variant_{idx}.json")

        if os.path.exists(persona_json_path):
            with open(persona_json_path, 'r', encoding='utf-8') as f:
                persona = json.load(f)
        else:
            persona = {}

        data_generation_prompt = prompts.get("default", {}).get("dataGeneration", "")

        if persona:
            persona_json_escaped = json.dumps(persona, indent=2).replace("{", "{{").replace("}", "}}")
            data_generation_prompt += (
                "\n\n## BORROWER PERSONA\n"
                "Below is the current borrower persona JSON. "
                "You MUST use these details for all similar fields in the output, for example, Social security number (SSN) and Employee's social security number would be the same values for a specific borrower persona."
                "and update the persona if new personal identifiers are created or changed. "
                "Do not invent new identities for this variant unless a new field is required.\n"
                f"{persona_json_escaped}"
            )

        data_generation_prompt = data_generation_prompt.format(
            document_type=document_type,
            field_mappings_json=field_mappings_json,
            human_readable_labels=human_readable_labels,
        )

        sample_flag = f"{document_type} - Sample [ {idx} / {total_samples} ]"
        print(f"Generating {sample_flag}!")
        logger.info(f"Generating {sample_flag}!")

        time_stamp = datetime.datetime.now(pytz.UTC).strftime("%m_%d_%y_%H_%M_%S")
        unique_id = str(uuid.uuid4())
        sample_id = f"Sample{idx}_{time_stamp}_{unique_id}"

        output_json_directory = os.path.join(json_directory, sample_id)
        output_pdf_directory = os.path.join(pdf_directory, sample_id)
        output_image_directory = os.path.join(image_directory, sample_id)

        make_directory(directory=output_json_directory)
        make_directory(directory=output_pdf_directory)
        make_directory(directory=output_image_directory)

        output_json_path = os.path.join(
            output_json_directory, f"{document_type}.json"
        )
        output_pdf_path = os.path.join(
            output_pdf_directory, f"{document_type}.pdf"
        )

        output_json = generate_synthetic_data(
            client=client,
            document_type=document_type,
            data_generation_prompt=data_generation_prompt,
            field_mappings_json=field_mappings_json,
            human_readable_labels=human_readable_labels,
            data_flag=sample_flag,
            logger=logger,
        )

        new_persona = extract_persona_fields_from_json(output_json)
        persona = merge_persona(persona, new_persona)
        with open(persona_json_path, 'w', encoding='utf-8') as f:
            json.dump(persona, f, indent=2)

        save_json(
            data=output_json,
            json_path=output_json_path,
            data_flag=sample_flag,
            logger=logger,
        )
        fill_pdf_fields(
            input_pdf=pdf_path_abs,
            output_pdf_path=output_pdf_path,
            data=output_json,
            data_flag=sample_flag,
            logger=logger,
        )
        
        # ========== NEW: VALIDATION AND CORRECTION LOGIC ==========
        # Only run validation if not disabled
        if not args.disable_validation:
            logger.info(f"Starting validation recheck for {sample_flag}")
            
            # Load current mappings for validation
            with open(field_mappings_path, "r", encoding='utf-8') as f:
                current_field_mappings = json.load(f)
            with open(human_readable_labels_path, "r", encoding='utf-8') as f:
                current_human_readable_labels = json.load(f)
            
            # Extract current persona for consistency
            current_persona = extract_persona_fields_from_json(output_json)
            
            validation_successful, corrected_labels, regenerated_data, validation_result = validate_filled_pdf_mapping(
                filled_pdf_path=output_pdf_path,
                original_pdf_path=pdf_path_abs,  # Pass the original PDF path
                fieldname_images=fieldname_images,
                field_mappings=current_field_mappings,
                human_readable_labels=current_human_readable_labels,
                synthetic_data=output_json,
                current_persona=current_persona,
                client=client,
                output_directory=output_json_directory,
                document_type=document_type,
                data_generation_prompt=data_generation_prompt,
                logger=logger,
                max_retries=2
            )
            
            # Add to validation reporter if it exists
            corrections_made = []
            data_was_regenerated = False
            
            # Check if regeneration was successful and data is valid
            # Robust validation: ensure regenerated_data is a non-empty dict with field mappings
            is_valid_regenerated_data = (
                regenerated_data and 
                isinstance(regenerated_data, dict) and 
                len(regenerated_data) > 0 and
                regenerated_data != output_json and
                # Ensure it has some actual field data (not just empty structure)
                any(isinstance(v, dict) and 'field_value' in v for v in regenerated_data.values())
            )
            
            if is_valid_regenerated_data:
                logger.info(f"Using regenerated synthetic data for {sample_flag} ({len(regenerated_data)} fields)")
                output_json = regenerated_data
                data_was_regenerated = True
                corrections_made.append({
                    "type": "data_regeneration",
                    "description": "Regenerated synthetic data with corrected labels and persona context"
                })
                
                # CRITICAL FIX: Refill PDF with regenerated data
                logger.info(f"Refilling PDF with regenerated data for {sample_flag}")
                fill_pdf_fields(
                    input_pdf=pdf_path_abs,
                    output_pdf_path=output_pdf_path,
                    data=regenerated_data,
                    data_flag=f"{sample_flag} (regenerated)",
                    logger=logger,
                )
            elif regenerated_data == output_json:
                logger.info(f"Regenerated data identical to original - no changes needed for {sample_flag}")
            else:
                logger.warning(f"Data regeneration failed or returned invalid data for {sample_flag}. Keeping original data.")
                logger.warning(f"Regenerated data type: {type(regenerated_data)}, length: {len(regenerated_data) if isinstance(regenerated_data, dict) else 'N/A'}")
                # Continue with original data - PDF already filled correctly
            
            # Update human readable labels if corrected (for future samples)
            if corrected_labels != current_human_readable_labels:
                logger.info(f"Updating human readable labels based on validation feedback")
                human_readable_labels = json.dumps(corrected_labels, indent=4)
                
                # Save updated labels for future use
                corrected_labels_path = human_readable_labels_path.replace('.json', '_validated.json')
                save_json(
                    data=corrected_labels,
                    json_path=corrected_labels_path,
                    data_flag="Validated human readable labels",
                    logger=logger,
                )
                
                # Also update the main file so subsequent samples use corrected labels
                logger.info(f"Updating main human readable labels file for future samples")
                save_json(
                    data=corrected_labels,
                    json_path=human_readable_labels_path,
                    data_flag="Updated human readable labels",
                    logger=logger,
                )
                
                corrections_made.append({
                    "type": "label_correction", 
                    "description": "Corrected human-readable field labels"
                })
            
            # Save regenerated data if different from original
            if data_was_regenerated:
                corrected_json_path = os.path.join(
                    output_json_directory, f"{document_type}_regenerated.json"
                )
                save_json(
                    data=output_json,
                    json_path=corrected_json_path,
                    data_flag=f"{sample_flag} - Regenerated",
                    logger=logger,
                )
            
            # Update persona with any new fields from regenerated data
            if data_was_regenerated:
                new_persona_fields = extract_persona_fields_from_json(output_json)
                persona = merge_persona(persona, new_persona_fields)
                with open(persona_json_path, 'w', encoding='utf-8') as f:
                    json.dump(persona, f, indent=2)
            
            # Add to validation reporter
            if validation_reporter is not None:
                validation_reporter.add_sample_report(
                    sample_id=sample_id,
                    validation_result=validation_result,
                    corrections_made=corrections_made
                )
            
            # Update files if corrections were made
            if not validation_successful:
                logger.warning(f"Validation had issues for {sample_flag}, but used best corrected version")
            
            logger.info(f"Validation recheck completed for {sample_flag}")
        else:
            logger.info(f"Validation disabled - skipping recheck for {sample_flag}")
        
        # Move image generation to the end of the loop to ensure it captures the final, validated PDF state.
        pdf_to_images(
            pdf_path=output_pdf_path,
            image_directory=output_image_directory,
            data_flag=sample_flag,
            logger=logger,
        )
        
        # Copy filled PDF to consolidated folder
        consolidated_dir = os.path.join(os.path.abspath(args.output_directory), "consolidated_pdfs")
        make_directory(directory=consolidated_dir)
        
        # Create a more descriptive filename for the consolidated folder
        consolidated_filename = f"{document_type}_Sample{idx}.pdf"
        consolidated_pdf_path = os.path.join(consolidated_dir, consolidated_filename)
        
        try:
            shutil.copy2(output_pdf_path, consolidated_pdf_path)
            logger.info(f"Copied filled PDF to consolidated folder: {consolidated_filename}")
        except Exception as e:
            logger.warning(f"Failed to copy PDF to consolidated folder: {str(e)}")
        
        print(f"{sample_flag} has been generated successfully!")
        logger.info(f"{sample_flag} has been generated successfully!")

    # Generate and save validation report
    if validation_reporter is not None:
        try:
            validation_reporter.print_summary()
            report_path = validation_reporter.save_report(logger=logger)
            print(f"Validation report saved to: {report_path}")
            logger.info(f"Validation report saved to: {report_path}")
        except Exception as e:
            logger.error(f"Failed to generate validation report: {str(e)}")

    print(f"Completed processing {document_type}!")
    logger.info(f"Completed processing {document_type}!")


if __name__ == "__main__":
    load_dotenv(find_dotenv())

    logger = CustomLogger(logger_name="SyntheticData", log_prefix="SyntheticData")
    args = get_args()

    # Initialize OpenAI client
    client = AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", ""),
    )

    # Load prompts
    prompt_filepath = os.path.abspath(args.prompt_filepath)
    with open(prompt_filepath, "r", encoding="utf-8") as json_file:
        prompts = json.load(json_file)

    if args.batch_directory:
        # Batch processing mode
        batch_dir = os.path.abspath(args.batch_directory)
        if not os.path.exists(batch_dir):
            print(f"Batch directory does not exist: {batch_dir}")
            logger.error(f"Batch directory does not exist: {batch_dir}")
            exit(1)

        # Find all PDF files in the batch directory
        pdf_files = [f for f in os.listdir(batch_dir) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            print(f"No PDF files found in batch directory: {batch_dir}")
            logger.warning(f"No PDF files found in batch directory: {batch_dir}")
            exit(0)

        print(f"\n====================================")
        print(f"BATCH PROCESSING MODE")
        print(f"Found {len(pdf_files)} PDF files to process")
        print(f"Batch directory: {batch_dir}")
        print(f"Output directory: {args.output_directory}")
        print(f"====================================\n")

        logger.info(f"====================================")
        logger.info(f"BATCH PROCESSING MODE")
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        logger.info(f"Batch directory: {batch_dir}")
        logger.info(f"Output directory: {args.output_directory}")
        logger.info(f"====================================")

        successful_count = 0
        failed_count = 0

        for pdf_file in pdf_files:
            pdf_path = os.path.join(batch_dir, pdf_file)
            print(f"\n[{successful_count + failed_count + 1}/{len(pdf_files)}] Processing: {pdf_file}")
            try:
                process_single_pdf(pdf_path, args, logger, client, prompts)
                successful_count += 1
            except Exception as e:
                failed_count += 1
                print(f"✗ Failed to process {pdf_file}: {e}")
                logger.error(f"Failed to process {pdf_file}: {e}", exc_info=True)

        print(f"\n====================================")
        print(f"BATCH PROCESSING COMPLETE")
        print(f"Successfully processed: {successful_count}")
        print(f"Failed: {failed_count}")
        print(f"Total: {len(pdf_files)}")
        print(f"====================================")

        logger.info(f"====================================")
        logger.info(f"BATCH PROCESSING COMPLETE")
        logger.info(f"Successfully processed: {successful_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info(f"Total: {len(pdf_files)}")
        logger.info(f"====================================")

    else:
        # Single file processing mode (original behavior)
        if not args.input_pdf:
            print("Error: --input_pdf is required when not using batch mode")
            logger.error("Error: --input_pdf is required when not using batch mode")
            exit(1)
            
        process_single_pdf(
            pdf_path=args.input_pdf,
            args=args,
            logger=logger,
            client=client,
            prompts=prompts
        )
