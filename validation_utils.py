import json
import os
from typing import Dict, List, Tuple, Any

from utils.image_utils import encode_images_to_base64
from utils.pdf_utils import pdf_to_images
from utils.general_utils import save_json


def validate_filled_pdf_mapping(
    filled_pdf_path: str,
    original_pdf_path: str,  # Add original PDF path parameter
    fieldname_images: List[str],
    field_mappings: Dict[str, Any],
    human_readable_labels: Dict[str, str],
    synthetic_data: Dict[str, Any],
    current_persona: Dict[str, Any],
    client,
    output_directory: str,
    document_type: str,
    data_generation_prompt: str,
    logger,
    max_retries: int = 2
) -> Tuple[bool, Dict[str, str], Dict[str, Any], Dict[str, Any]]:
    """
    Validates if the filled PDF makes logical sense and regenerates data if needed.
    
    Args:
        filled_pdf_path: Path to the filled PDF
        original_pdf_path: Path to the original unfilled PDF template
        fieldname_images: List of paths to field name overlay images
        field_mappings: Original field mappings JSON
        human_readable_labels: Current human readable labels mapping
        synthetic_data: The data used to fill the PDF
        current_persona: Current persona context to maintain consistency
        client: OpenAI client
        output_directory: Directory to save corrected files
        document_type: Type of document being processed
        data_generation_prompt: Original prompt used for data generation
        logger: Logger instance
        max_retries: Maximum number of correction attempts
        
    Returns:
        Tuple of (is_valid, corrected_human_readable_labels, regenerated_synthetic_data, validation_result)
    """
    
    validation_result = None
    
    for attempt in range(max_retries + 1):
        logger.info(f"Validation attempt {attempt + 1}/{max_retries + 1} for {document_type}")
        
        # Generate images of the filled PDF
        filled_pdf_image_dir = os.path.join(output_directory, "filled_pdf_validation_images")
        os.makedirs(filled_pdf_image_dir, exist_ok=True)
        
        pdf_to_images(
            pdf_path=filled_pdf_path,
            image_directory=filled_pdf_image_dir,
            data_flag=f"Validation attempt {attempt + 1}",
            logger=logger
        )
        
        # Get the generated image paths
        filled_pdf_images = []
        if os.path.exists(filled_pdf_image_dir):
            for file_name in sorted(os.listdir(filled_pdf_image_dir)):
                if file_name.endswith('.jpg'):
                    filled_pdf_images.append(os.path.join(filled_pdf_image_dir, file_name))
        
        # Encode both sets of images
        fieldname_image_data = encode_images_to_base64(fieldname_images)
        
        if filled_pdf_images:
            filled_pdf_image_data = encode_images_to_base64(filled_pdf_images)
        else:
            logger.error("Failed to generate filled PDF images")
            filled_pdf_image_data = {}
        
        # Combine all image data
        all_image_data = {**fieldname_image_data, **filled_pdf_image_data}
        
        # Perform validation with AI
        validation_result = _perform_ai_validation(
            all_image_data=all_image_data,
            field_mappings=field_mappings,
            human_readable_labels=human_readable_labels,
            synthetic_data=synthetic_data,
            client=client,
            document_type=document_type,
            logger=logger
        )
        
        if validation_result["is_valid"]:
            logger.info(f"Validation successful after {attempt + 1} attempts")
            return True, human_readable_labels, synthetic_data, validation_result
        
        if attempt < max_retries:
            logger.warning(f"Validation failed, attempting correction. Issues: {validation_result['issues']}")
            
            # Generate corrected mappings and regenerate data
            corrected_labels, regenerated_data = _generate_corrected_labels_and_regenerate_data(
                validation_result=validation_result,
                all_image_data=all_image_data,
                field_mappings=field_mappings,
                human_readable_labels=human_readable_labels,
                current_persona=current_persona,
                data_generation_prompt=data_generation_prompt,
                client=client,
                document_type=document_type,
                logger=logger
            )
            
            # Save corrected files
            corrected_labels_path = os.path.join(
                output_directory, f"{document_type}_human_readable_labels_corrected_v{attempt + 2}.json"
            )
            save_json(
                data=corrected_labels,
                json_path=corrected_labels_path,
                data_flag=f"Corrected human readable labels v{attempt + 2}",
                logger=logger
            )
            
            # Update for next iteration
            human_readable_labels = corrected_labels
            synthetic_data = regenerated_data
            
            # Re-fill PDF with regenerated data ONLY if regenerated data is valid
            # Robust validation: ensure regenerated_data is a non-empty dict with field mappings
            is_valid_regenerated_data = (
                regenerated_data and 
                isinstance(regenerated_data, dict) and 
                len(regenerated_data) > 0 and
                # Ensure it has some actual field data (not just empty structure)
                any(isinstance(v, dict) and 'field_value' in v for v in regenerated_data.values())
            )
            
            if is_valid_regenerated_data:
                try:
                    from utils.pdf_utils import fill_pdf_fields
                    fill_pdf_fields(
                        input_pdf=original_pdf_path,  # Use the original PDF path
                        output_pdf_path=filled_pdf_path,
                        data=regenerated_data,
                        data_flag=f"Corrected attempt {attempt + 2}",
                        logger=logger
                    )
                    logger.info(f"Successfully re-filled PDF with regenerated data (attempt {attempt + 2})")
                except Exception as e:
                    logger.error(f"Failed to re-fill PDF with regenerated data (attempt {attempt + 2}): {str(e)}")
                    # Continue to next attempt or fail
            else:
                logger.warning(f"Regenerated data is invalid for attempt {attempt + 2}, skipping PDF refill")
                logger.warning(f"Regenerated data type: {type(regenerated_data)}, length: {len(regenerated_data) if isinstance(regenerated_data, dict) else 'N/A'}")
                # Don't overwrite the PDF with bad data
        
    logger.error(f"Failed to validate mapping after {max_retries + 1} attempts")
    return False, human_readable_labels, synthetic_data, validation_result or {}


def _perform_ai_validation(
    all_image_data: Dict[str, str],
    field_mappings: Dict[str, Any],
    human_readable_labels: Dict[str, str],
    synthetic_data: Dict[str, Any],
    client,
    document_type: str,
    logger
) -> Dict[str, Any]:
    """
    Uses AI to validate if the filled PDF makes logical sense.
    """
    
    system_prompt = f"""
    You are a document validation expert specializing in {document_type} forms.
    
    Your task is to analyze whether the filled PDF makes logical sense by comparing:
    1. Field name overlay images (showing where each field is located)
    2. Filled PDF images (showing the actual filled values)
    3. The current field mappings and human-readable labels
    4. The synthetic data that was used to fill the form
    
    Identify any issues where:
    - Values appear in wrong locations on the form
    - Field names don't match their actual purpose based on form layout
    - Human-readable labels are incorrect for their field positions
    - Data values don't make sense for their intended fields
    - Required fields are empty or filled incorrectly
    
    Be thorough and specific in identifying mapping issues.
    """
    
    validation_prompt = f"""
    Please validate this filled {document_type} form for logical consistency and correct field mapping.
    
    ## IMPORTANT: VISUAL FIELD IDENTIFICATION FORMATS
    You will see TWO types of field identification:
    
    **1. Field Name Overlay Images (Reference):**
    - Show field names wrapped in double curly brackets: "{{{{fieldname}}}}" (e.g., "{{{{f1_01}}}}").
    - These are for reference to see where each field is located.
    
    **2. Filled PDF Images (Validation Target):**
    - These images show the final PDF with the actual synthetic data values filled in.
    - Use these images to verify that the correct data appears in the correct field locations, by cross-referencing with the Field Name Overlay images.
    
    ## CURRENT FIELD MAPPINGS
    ```json
    {{json.dumps(field_mappings, indent=2)}}
    ```
    
    ## SYNTHETIC DATA USED (contains field names, labels, and values)
    ```json
    {{json.dumps(synthetic_data, indent=2)}}
    ```
    
    ## CURRENT HUMAN READABLE LABELS (for reference and comparison)
    ```json  
    {{json.dumps(human_readable_labels, indent=2)}}
    ```
    
    Note: The human-readable labels are also the keys in the synthetic data JSON. 
    Use this separate mapping to identify if there are inconsistencies between 
    intended labels and actual usage.
    
    ## VALIDATION INSTRUCTIONS: ACT AS A STRICT AUDITOR
    Your task is to meticulously audit this form for correctness.

    1.  **Verify Field Locations:** Use the `{{{{fieldname}}}}` overlay images as a map. For each field name, find its location on the filled PDF image and check the value there.

    2.  **Enforce Data Type Integrity:** This is critical. For each field, verify that the data type of the value matches the field's label.
        *   A field labeled "Percentage" MUST contain a percentage (e.g., "25.00%").
        *   A field labeled "Date" MUST contain a valid date (e.g., "MM/DD/YYYY").
        *   A field labeled "Number of shares" MUST contain a number, not a percentage or text.
        *   A field labeled "Name" or "Address" should not contain numbers or percentages.

    3.  **Check for Logical Consistency:**
        *   **Dates:** Ensure end dates are after start dates. The calendar year should be logical.
        *   **Totals:** If there are subtotal and total fields, ensure they add up correctly if possible.
        *   **Context:** Does the data make sense? A "TIN" should not be identical to a "Social Security Number" on the same form if they are for different entities.

    4.  **Identify Misplaced Values:** If you find a value in the wrong field (e.g., the text "Individual" in a percentage field), check if a nearby field that *should* contain that value is empty. This is a strong indicator of a `wrong_label` or `wrong_location` issue.

    5.  **Report All Issues:** Be thorough. Document every single discrepancy you find in the `issues` array.
    
    ## OUTPUT FORMAT
    Respond with a JSON object containing:
    ```json
    {{
        "is_valid": true/false,
        "confidence_score": 0.0-1.0,
        "issues": [
            {{
                "field_name": "exact_field_name",
                "issue_type": "wrong_location|wrong_label|wrong_value|missing_value",
                "description": "Detailed description of the issue",
                "suggested_correct_label": "What the label should be based on form position",
                "page_number": 1
            }}
        ],
        "summary": "Overall assessment summary"
    }}
    ```
    
    Set is_valid to false if there are significant mapping issues that affect form readability or logic.
    """
    
    try:
        # Prepare image blocks
        image_blocks = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_data}"
                },
            }
            for image_data in all_image_data.values()
        ]
        
        message_data = [{"type": "text", "text": validation_prompt}] + image_blocks
        
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_GPT4O_MODEL_DEPLOYMENT", "gpt-4o"),
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=8000,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message_data}
            ],
        )
        
        result = json.loads(response.choices[0].message.content)
        logger.info(f"Validation result: {result['summary']}")
        return result
        
    except Exception as e:
        logger.error(f"Error during AI validation: {str(e)}")
        return {
            "is_valid": False,
            "confidence_score": 0.0,
            "issues": [{"field_name": "unknown", "issue_type": "validation_error", "description": str(e)}],
            "summary": f"Validation failed due to error: {str(e)}"
        }


def _generate_corrected_labels(
    validation_result: Dict[str, Any],
    all_image_data: Dict[str, str],
    field_mappings: Dict[str, Any],
    human_readable_labels: Dict[str, str],
    client,
    document_type: str,
    logger
) -> Dict[str, str]:
    """
    Generates corrected human-readable labels based on validation issues.
    """
    
    system_prompt = f"""
    You are a document correction expert specializing in {document_type} forms.
    
    Based on the validation issues identified, you need to correct human-readable labels 
    for misidentified fields. Focus ONLY on correcting the labels - data regeneration 
    will be handled separately.
    """
    
    correction_prompt = f"""
    Please correct the human-readable labels based on the validation issues found.
    
    ## VALIDATION ISSUES
    ```json
    {json.dumps(validation_result['issues'], indent=2)}
    ```
    
    ## CURRENT FIELD MAPPINGS
    ```json
    {json.dumps(field_mappings, indent=2)}
    ```
    
    ## CURRENT HUMAN READABLE LABELS
    ```json
    {json.dumps(human_readable_labels, indent=2)}
    ```
    
    ## CORRECTION INSTRUCTIONS
    1. For each issue identified, correct the human-readable label based on the actual form field location
    2. Maintain consistency with existing correct mappings
    3. Use exact language from the form for corrected labels
    4. Only correct labels that have identified issues
    5. Keep all other labels unchanged
    
    ## OUTPUT FORMAT
    Respond with a JSON object containing the COMPLETE corrected human-readable labels mapping:
    ```json
    {{
        "field_name_1": "corrected or unchanged human readable label",
        "field_name_2": "corrected or unchanged human readable label",
        ...
    }}
    ```
    
    Include ALL field names from the original mapping, not just the corrected ones.
    """
    
    try:
        # Prepare image blocks
        image_blocks = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_data}"
                },
            }
            for image_data in all_image_data.values()
        ]
        
        message_data = [{"type": "text", "text": correction_prompt}] + image_blocks
        
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_GPT4O_MODEL_DEPLOYMENT", "gpt-4o"),
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=12000,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message_data}
            ],
        )
        
        corrected_labels = json.loads(response.choices[0].message.content)
        
        # Log corrections made
        corrections_count = 0
        for field_name, new_label in corrected_labels.items():
            if field_name in human_readable_labels and human_readable_labels[field_name] != new_label:
                logger.info(f"Label correction: {field_name} - '{human_readable_labels[field_name]}' -> '{new_label}'")
                corrections_count += 1
        
        logger.info(f"Generated {corrections_count} label corrections")
        return corrected_labels
        
    except Exception as e:
        logger.error(f"Error during label correction generation: {str(e)}")
        return human_readable_labels


def _regenerate_synthetic_data_with_persona(
    corrected_labels: Dict[str, str],
    field_mappings: Dict[str, Any],
    current_persona: Dict[str, Any],
    data_generation_prompt: str,
    client,
    document_type: str,
    logger
) -> Dict[str, Any]:
    """
    Regenerates synthetic data using the existing pipeline with corrected labels and persona context.
    """
    
    from utils.genai_utils import generate_synthetic_data
    
    try:
        # Validate inputs
        if not field_mappings:
            logger.error("Empty field_mappings provided for data regeneration")
            return {}
        
        if not corrected_labels:
            logger.error("Empty corrected_labels provided for data regeneration") 
            return {}
        
        # Prepare prompt with persona context
        enhanced_prompt = data_generation_prompt
        
        if current_persona:
            persona_json_escaped = json.dumps(current_persona, indent=2).replace("{", "{{").replace("}", "}}")
            enhanced_prompt += (
                "\n\n## CURRENT PERSONA CONTEXT\n"
                "Below is the current persona that MUST be maintained for consistency. "
                "Use these exact values for any matching fields (name, SSN, address, etc.):\n"
                f"{persona_json_escaped}"
            )
        
        # Format prompt with corrected labels and explicit field mapping instructions
        field_mappings_json = json.dumps(field_mappings, indent=4)
        corrected_labels_json = json.dumps(corrected_labels, indent=4)
        
        # Add explicit field mapping instruction to ensure consistency
        field_mapping_instruction = (
            "\n\n## CRITICAL FIELD MAPPING REQUIREMENT\n"
            "IMPORTANT: In your JSON output, the 'field_name' value for each entry MUST exactly match "
            "the keys from the FIELD MAPPINGS JSON above. Do not modify or truncate the field names. "
            "Use the complete field path exactly as shown in the field mappings.\n"
            "The human-readable label (key) should match the corrected labels, and the field_name "
            "should be the exact technical field name from the mappings."
        )
        
        formatted_prompt = enhanced_prompt.format(
            document_type=document_type,
            field_mappings_json=field_mappings_json,
            human_readable_labels=corrected_labels_json,
        ) + field_mapping_instruction
        
        # Generate new synthetic data using existing pipeline
        regenerated_data = generate_synthetic_data(
            client=client,
            document_type=document_type,
            data_generation_prompt=formatted_prompt,
            field_mappings_json=field_mappings_json,
            human_readable_labels=corrected_labels_json,
            data_flag="Validation Correction",
            logger=logger,
        )
        
        logger.info(f"Successfully regenerated synthetic data with persona consistency")
        return regenerated_data
        
    except Exception as e:
        logger.error(f"Error during data regeneration: {str(e)}")
        # Return empty dict as fallback
        return {}


def _generate_corrected_labels_and_regenerate_data(
    validation_result: Dict[str, Any],
    all_image_data: Dict[str, str],
    field_mappings: Dict[str, Any],
    human_readable_labels: Dict[str, str],
    current_persona: Dict[str, Any],
    data_generation_prompt: str,
    client,
    document_type: str,
    logger
) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """
    Generates corrected human-readable labels and regenerates synthetic data using existing pipeline.
    """
    
    # Step 1: Generate corrected human-readable labels
    corrected_labels = _generate_corrected_labels(
        validation_result=validation_result,
        all_image_data=all_image_data,
        field_mappings=field_mappings,
        human_readable_labels=human_readable_labels,
        client=client,
        document_type=document_type,
        logger=logger
    )
    
    # Step 2: Regenerate synthetic data using existing pipeline with corrected labels
    regenerated_data = _regenerate_synthetic_data_with_persona(
        corrected_labels=corrected_labels,
        field_mappings=field_mappings,
        current_persona=current_persona,
        data_generation_prompt=data_generation_prompt,
        client=client,
        document_type=document_type,
        logger=logger
    )
    
    return corrected_labels, regenerated_data
