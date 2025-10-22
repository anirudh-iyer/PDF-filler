import json
import os
import re
import uuid

from .general_utils import save_json


def clean_response(response):
    """Enhanced response cleaning to handle malformed JSON"""
    # Remove code block markers
    response = re.sub(r"^```(?:json)?\s*", "", response.strip())
    response = re.sub(r"\s*```$", "", response)
    
    # Remove control characters except newlines (we'll handle those separately)
    response = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", response)
    
    # First normalize spacing - replace all whitespace sequences with single spaces
    # but preserve the JSON structure
    response = re.sub(r'\s+', ' ', response)
    
    # Fix common JSON issues
    # Fix unescaped backslashes (but preserve valid escape sequences)
    response = re.sub(r"(?<!\\)\\(?![\\/\"bfnrtu])", r"\\\\", response)
    
    # Fix trailing commas before closing brackets/braces
    response = re.sub(r',\s*([}\]])', r'\1', response)
    
    # Fix multiple consecutive commas
    response = re.sub(r',\s*,+', ',', response)
    
    # Remove any trailing text after the JSON object
    # Find the last } that closes the main JSON object
    brace_count = 0
    json_end = -1
    for i, char in enumerate(response):
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                json_end = i + 1
                break
    
    if json_end > 0:
        response = response[:json_end]
    
    return response


def generate_human_readable_labels(
    client, image_data, document_type, human_readable_prompt, output_path, logger, field_mappings_json=None
):
    try:
        system_prompt = """
        You are a document understanding expert. 
        Your task is to analyze {document_type} PDFs and 
        map each AcroForm field name to its corresponding 
        human-readable label based on the form's 
        layout and printed instructions.

        Use visual cues from the form such as field placement, 
        surrounding text, section titles and line numbers
        to determine the most accurate and concise label for each field. 
        Maintain accuracy with field numbers and context, 
        even if the layout spans multiple pages.

        Be accurate, consistent, and align labels with the official 
        {document_type} terminology as it appears on the form.
        """
        system_prompt = system_prompt.format(document_type=document_type)

        image_blocks = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_data[image_name]}"
                },
            }
            for image_name in image_data.keys()
        ]

        # Add field mappings as structured data
        field_mappings_text = ""
        if field_mappings_json:
            field_mappings_text = f"\n\n### AcroForm Field Mappings JSON:\n```json\n{field_mappings_json}\n```"

        message_data = [
            {"type": "text", "text": human_readable_prompt + field_mappings_text}
        ] + image_blocks

        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_GPT4O_MODEL_DEPLOYMENT", "gpt-4o"),
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=12000,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": message_data,
                },
            ],
        )
        response = clean_response(response=response.choices[0].message.content)
        response = json.loads(response)

        # --- Post-process: map short field names to full field mapping keys ---
        # Load field mappings from the prompt (should be passed in or loaded here)
        # For now, try to load from output_path's sibling field_mappings.json
        field_mappings_path = output_path.replace('_human_readable_labels.json', '_field_mappings.json')
        if os.path.exists(field_mappings_path):
            with open(field_mappings_path, 'r', encoding='utf-8') as f:
                field_mappings = json.load(f)
        else:
            field_mappings = {}

        # Simple validation: only keep fields that exist in field mappings
        remapped = {}
        for k, v in response.items():
            if k in field_mappings:
                remapped[k] = v
            else:
                logger.warning(f"Field {k} not found in field mappings, skipping")
        
        # If we have good matches, we're done. Otherwise try fuzzy matching.
        if len(remapped) < len(response) * 0.7:  # Less than 70% matched
            logger.info(f"Only {len(remapped)}/{len(response)} exact matches found, attempting fuzzy matching...")
            # Simple suffix matching as fallback
            suffix_to_full = {}
            for full_key in field_mappings.keys():
                parts = full_key.split('.')
                if parts and parts[-1].startswith(('f', 'c')):
                    field_suffix = parts[-1]
                    suffix_to_full[field_suffix] = full_key
            
            for k, v in response.items():
                if k not in remapped:  # Not already matched exactly
                    response_parts = k.split('.')
                    if response_parts and response_parts[-1].startswith(('f', 'c')):
                        response_suffix = response_parts[-1]
                        if response_suffix in suffix_to_full:
                            remapped[suffix_to_full[response_suffix]] = v
                            logger.info(f"Fuzzy matched {k} -> {suffix_to_full[response_suffix]}")
        
        logger.info(f"Final mapping: {len(remapped)} fields mapped successfully")

        print("Human readable labels have been generated successfully!")
        logger.info("Human readable labels have been generated successfully!")
        save_json(
            data=remapped,
            json_path=output_path,
            data_flag="Human readable labels",
            logger=logger,
        )
        human_readable_labels_json = json.dumps(remapped, indent=4)
        return human_readable_labels_json
    except Exception as error:
        print("Error while generating human readable labels!")
        print("{}".format(error))
        logger.error("Error while generating human readable labels!")
        logger.error("{}".format(error))
        raise


def flatten_nested_response(data, parent_key='', separator='.'):
    """
    Flatten nested JSON response into flat structure with full field paths as keys.
    Handles both flat and nested AI response formats.
    """
    items = []
    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{parent_key}{separator}{key}" if parent_key else key
            if isinstance(value, dict) and value:  # Only recurse if dict is not empty
                # Recursively flatten nested dictionaries
                items.extend(flatten_nested_response(value, new_key, separator).items())
            elif not isinstance(value, dict):  # Only add non-dict values
                # Keep the value as-is (could be string, number, etc.)
                items.append((new_key, value))
    return dict(items)

def generate_output_json(response, field_mappings_json, human_readable_labels, logger):
    try:
        field_mappings_json = json.loads(field_mappings_json)
        human_readable_labels = json.loads(human_readable_labels)
        
        # Flatten nested response if needed
        flattened_response = flatten_nested_response(response)
        logger.info(f"Flattened response has {len(flattened_response)} fields")
        
        json_data = {}
        matched_fields = 0
        
        for key, field_value in flattened_response.items():
            field_name = key
            label = human_readable_labels.get(field_name, "N/A")
            if label == "N/A":
                # Try to find partial matches for nested responses
                # Sometimes AI returns keys like "f1_01[0]" but we need "topmostSubform[0].Page1[0].f1_01[0]"
                for full_key in human_readable_labels.keys():
                    if full_key.endswith(key) or key in full_key:
                        field_name = full_key
                        label = human_readable_labels.get(field_name, "N/A")
                        logger.info(f"Matched partial key '{key}' to full key '{field_name}'")
                        break
                
                if label == "N/A":
                    logger.warning(f"No label found for field: {key}")
                    continue
            
            field_type = field_mappings_json.get(field_name, {}).get(
                "field_type", "N/A"
            )
            output_data = {
                "field_name": field_name,
                "field_type": field_type,
                "field_value": field_value,
            }
            json_data[label] = output_data
            matched_fields += 1
        
        logger.info(f"Successfully mapped {matched_fields} fields out of {len(flattened_response)} total fields")
        return json_data
    except Exception as error:
        print("Error while generating output JSON!")
        print("{}".format(error))
        logger.error("Error while generating output JSON!")
        logger.error("{}".format(error))
        raise


def generate_synthetic_data(
    client,
    document_type,
    data_generation_prompt,
    field_mappings_json,
    human_readable_labels,
    data_flag,
    logger,
):
    try:
        # Parse field mappings to determine if we need chunked processing
        field_mappings = json.loads(field_mappings_json)
        total_fields = len([k for k, v in field_mappings.items() if v.get('field_type')])
        
        # If the form has many fields (>200), use chunked processing
        if total_fields > 200:
            logger.info(f"Large form detected ({total_fields} fields). Using chunked processing.")
            return generate_synthetic_data_chunked(
                client, document_type, data_generation_prompt, 
                field_mappings_json, human_readable_labels, data_flag, logger
            )
        else:
            logger.info(f"Standard processing for {total_fields} fields.")
            return generate_synthetic_data_single(
                client, document_type, data_generation_prompt, 
                field_mappings_json, human_readable_labels, data_flag, logger
            )
    except Exception as error:
        print("Error while generating data for sample {}!".format(data_flag))
        print("{}".format(error))
        logger.error("Error while generating data for sample {}!".format(data_flag))
        logger.error("{}".format(error))
        raise

def generate_synthetic_data_chunked(
    client,
    document_type,
    data_generation_prompt,
    field_mappings_json,
    human_readable_labels,
    data_flag,
    logger,
):
    """Process large forms by breaking them into chunks and combining results"""
    try:
        field_mappings = json.loads(field_mappings_json)
        human_readable = json.loads(human_readable_labels)
        
        # Get all fields that need data
        relevant_fields = {k: v for k, v in field_mappings.items() if v.get('field_type')}
        
        # Split fields into chunks of 150 fields each
        chunk_size = 150
        field_keys = list(relevant_fields.keys())
        chunks = [field_keys[i:i + chunk_size] for i in range(0, len(field_keys), chunk_size)]
        
        logger.info(f"Processing {len(field_keys)} fields in {len(chunks)} chunks of {chunk_size} fields each")
        
        combined_response = {}
        
        for chunk_idx, chunk_fields in enumerate(chunks, 1):
            logger.info(f"Processing chunk {chunk_idx}/{len(chunks)} with {len(chunk_fields)} fields")
            
            # Create a subset of field mappings and human readable labels for this chunk
            chunk_field_mappings = {k: field_mappings[k] for k in chunk_fields}
            chunk_human_readable = {k: v for k, v in human_readable.items() if k in chunk_fields}
            
            # Create a focused prompt for this chunk
            chunk_prompt = f"""
Generate synthetic data for {document_type} fields (chunk {chunk_idx}/{len(chunks)}).

Field mappings for this chunk:
{json.dumps(chunk_field_mappings, indent=2)}

Human readable labels for this chunk:
{json.dumps(chunk_human_readable, indent=2)}

Generate realistic, consistent data for these {len(chunk_fields)} fields only.
Ensure data is appropriate for the document type and field labels.
Return as a JSON object with field names as keys and values as strings.
            """
            
            # Process this chunk
            chunk_response = generate_synthetic_data_single(
                client=client,
                document_type=f"{document_type} (chunk {chunk_idx})",
                data_generation_prompt=chunk_prompt,
                field_mappings_json=json.dumps(chunk_field_mappings),
                human_readable_labels=json.dumps(chunk_human_readable),
                data_flag=f"{data_flag} - Chunk {chunk_idx}",
                logger=logger
            )
            
            # Merge the chunk response into the combined response
            for label, data in chunk_response.items():
                combined_response[label] = data
            
            logger.info(f"Chunk {chunk_idx} completed: {len(chunk_response)} fields processed")
        
        logger.info(f"Chunked processing completed: {len(combined_response)} total fields processed")
        return combined_response
        
    except Exception as error:
        logger.error(f"Error in chunked processing: {error}")
        raise

def generate_synthetic_data_single(
    client,
    document_type,
    data_generation_prompt,
    field_mappings_json,
    human_readable_labels,
    data_flag,
    logger,
):
    try:
        random_seed = uuid.uuid4().int % 1_000_000
        prompt = (
            data_generation_prompt
            + f"\n\n### VARIABILITY NOTE\nRandomization seed: {random_seed}"
        )

        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_GPT4O_MINI_DEPLOYMENT", "gpt-4o-mini"),
            response_format={"type": "json_object"},
            temperature=1.0,
            max_tokens=16000,  # Increased from 12000 to handle large forms like URLA
            messages=[
                {
                    "role": "system",
                    "content": "You are generating realistic synthetic data for the following document type: {}. Ensure no two outputs are alike (i.e) No distinguishable fields are the same across outputs. Use the given seed for variability: {}.".format(
                        document_type, random_seed
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        
        # Log token usage to help diagnose truncation issues
        if hasattr(response, 'usage') and response.usage:
            logger.info(f"Token usage - Input: {response.usage.prompt_tokens}, Output: {response.usage.completion_tokens}, Total: {response.usage.total_tokens}")
            if response.usage.completion_tokens >= 15900:  # Close to 16k limit
                logger.warning(f"Response may be truncated - used {response.usage.completion_tokens} out of 16000 max tokens")
        
        response = response.choices[0].message.content
        logger.info("Response before cleaning: {}".format(response))
        response = clean_response(response=response)
        
        # Enhanced JSON parsing with multiple fallback attempts
        parsed_response = None
        parsing_attempts = [
            ("Standard json.loads", lambda r: json.loads(r)),
            ("JSONDecoder.raw_decode", lambda r: json.JSONDecoder().raw_decode(r)[0]),
            ("Lenient parsing", lambda r: json.loads(r, strict=False)),
        ]
        
        for attempt_name, parse_func in parsing_attempts:
            try:
                parsed_response = parse_func(response)
                logger.info(f"Successfully parsed JSON using {attempt_name}")
                break
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parsing failed with {attempt_name}: {e}")
                if attempt_name == "JSONDecoder.raw_decode":
                    # Try to fix common issues and retry
                    try:
                        # Try to extract just the JSON part if there's extra text
                        start_idx = response.find('{')
                        if start_idx >= 0:
                            response_clean = response[start_idx:]
                            
                            # Try to fix truncated JSON by removing incomplete last field
                            last_comma = response_clean.rfind(',')
                            last_brace = response_clean.rfind('}')
                            
                            if last_comma > last_brace:
                                # The JSON ends with a comma and incomplete field
                                # Remove everything after the last complete field
                                response_clean = response_clean[:last_comma] + '}'
                                logger.info("Attempting to fix truncated JSON by removing incomplete field")
                            
                            parsed_response = json.loads(response_clean)
                            logger.info(f"Successfully parsed JSON after fixing truncation")
                            break
                    except:
                        continue
                continue
            except Exception as e:
                logger.warning(f"Unexpected error with {attempt_name}: {e}")
                continue
        
        if parsed_response is None:
            # Final attempt: try to salvage what we can from truncated JSON
            try:
                start_idx = response.find('{')
                if start_idx >= 0:
                    response_part = response[start_idx:]
                    # Find the last complete field before any truncation
                    last_complete_field = -1
                    brace_count = 0
                    in_string = False
                    escape_next = False
                    
                    for i, char in enumerate(response_part):
                        if escape_next:
                            escape_next = False
                            continue
                        
                        if char == '\\':
                            escape_next = True
                            continue
                        
                        if char == '"' and not escape_next:
                            in_string = not in_string
                        elif not in_string:
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                            elif char == ',' and brace_count == 1:
                                # This is a field separator at the top level
                                last_complete_field = i
                    
                    if last_complete_field > 0:
                        truncated_json = response_part[:last_complete_field] + '}'
                        parsed_response = json.loads(truncated_json)
                        logger.warning(f"Successfully parsed truncated JSON, recovered {len(parsed_response)} fields")
                    
            except Exception as e:
                logger.error(f"Final JSON salvage attempt failed: {e}")
        
        if parsed_response is None:
            raise json.JSONDecodeError(
                f"Failed to parse JSON response with all methods. Response length: {len(response)}", 
                response, 0
            )
        
        # Check if we got a nested response that needs flattening
        if parsed_response and any(isinstance(v, dict) for v in parsed_response.values()):
            logger.info("Detected nested JSON response, flattening...")
            parsed_response = flatten_nested_response(parsed_response)
            logger.info(f"Flattened response has {len(parsed_response)} fields")
        
        response = parsed_response
        logger.info("Response after cleaning: {}".format(response))
        output_json = generate_output_json(
            response=response,
            field_mappings_json=field_mappings_json,
            human_readable_labels=human_readable_labels,
            logger=logger,
        )
        print("Data for {} has been generated successfully!".format(data_flag))
        logger.info("Data for {} has been generated successfully!".format(data_flag))
        return output_json
    except Exception as error:
        print("Error while generating data for sample {}!".format(data_flag))
        print("{}".format(error))
        logger.error("Error while generating data for sample {}!".format(data_flag))
        logger.error("{}".format(error))
        raise
