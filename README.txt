Example run

1. python main.py --input_pdf="data/1040-ScheduleC/1040-ScheduleC.pdf" --number_of_variants=5 --prompt_filepath="data/prompts.json" --output_directory="output"
2. Then you map the Human Readable form key values to the ones in field mapping using https://edit-pdf.pdffiller.com and then you click on Add fields right next to edit and look at the acroform name for the field and map it to the human readable format.
3. Run 1 again.

Batch running script: python main.py --batch_directory "data/Schedule Batch" --number_of_variants 30 --output_directory "output\Schedule Batch" --prompt_filepath "data/prompts.json"

Running AVM part:
python avm_template_generator.py --num_reports 30


# AVM Report Generator - Implementation Guide

## Overview

This implements **Option 1: Template-Based Approach** for generating synthetic AVM (Automated Valuation Model) reports. It extends your existing form filling system to create comprehensive property valuation reports in multiple formats.

## System Architecture

```
AVM Report Generation Flow:
1. Load prompts from JSON configuration
2. Generate synthetic property data using AI
3. Create professional HTML templates  
4. Convert to PDF (optional)
5. Generate images (optional)
6. Output: JSON + HTML + PDF + Images
```

## Files Created

### Core System Files
- **`data/avm_prompts.json`** - AI prompts for generating realistic AVM data
- **`avm_template_generator.py`** - Main AVM generator (extends existing system)
- **`demo_avm_simple.py`** - Basic functionality test (no extra dependencies)

### Key Features
✅ **Realistic Data Generation** - AI creates consistent property/market data  
✅ **Professional Templates** - Clean, responsive HTML reports  
✅ **Multiple Output Formats** - JSON, HTML, PDF, Images  
✅ **Batch Processing** - Generate multiple reports efficiently  
✅ **Error Handling** - Graceful fallbacks when PDF libraries unavailable  
✅ **Existing System Integration** - Uses your current utilities and patterns  

## Quick Start

### 1. Test Basic Functionality
```bash
python demo_avm_simple.py
```
This tests core functionality without requiring PDF libraries.

### 2. Generate AVM Reports  
```bash
# Generate 3 reports (default)
python avm_template_generator.py

# Generate 10 reports
python avm_template_generator.py --num_reports 10

# Custom output directory  
python avm_template_generator.py --num_reports 5 --output_directory "output/my_avm_reports"
```

## Installation Requirements

### Essential (Already in your system)
- Python 3.8+
- openai package  
- python-dotenv
- Your existing utilities (logger_utils, general_utils, etc.)

### Optional (for full PDF/image functionality)
```bash
# For best PDF quality
pip install weasyprint

# Alternative PDF option (requires wkhtmltopdf installed separately)
pip install pdfkit

# For HTML to image conversion
pip install selenium
```

## Output Structure

Each generated report creates:
```
output/avm_reports/
├── AVM_08_12_25_14_30_45_abc123ef/
│   ├── AVM_08_12_25_14_30_45_abc123ef.json    # Raw data
│   ├── AVM_08_12_25_14_30_45_abc123ef.html    # HTML report  
│   ├── AVM_08_12_25_14_30_45_abc123ef.pdf     # PDF report (if libraries available)
│   └── images/
│       └── Page1.png                          # Report images
```

## Comparison to Your Current System

| Aspect | Current Forms | AVM Reports |
|--------|---------------|-------------|
| **Input** | Fillable PDF templates | AI-generated data schema |
| **Data Source** | AcroForm field extraction | Custom property/market data |  
| **AI Usage** | Field value generation | Comprehensive report data |
| **Output** | Filled PDF + images | HTML + PDF + images |
| **Complexity** | Simple form fields | Complex reports with tables/charts |
| **Use Case** | Tax forms, applications | Property valuation reports |

## Configuration

### Environment Variables (Same as your current system)
```env
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_GPT4O_MINI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-02-01
```

### AVM Prompts (`data/avm_prompts.json`)
Contains detailed prompts that instruct the AI to generate:
- Property information (address, size, features)  
- Valuation data (estimated value, confidence, methodology)
- Comparable sales (3 similar properties with adjustments)
- Market analysis (trends, conditions, metrics)
- Neighborhood information (schools, amenities, demographics)
- Risk factors and disclaimers

## Code Organization

### Main Generator Class (`AVMReportGenerator`)
```python
# Core methods that mirror your existing system patterns:
- generate_avm_data()                    # Like generate_synthetic_data()  
- create_professional_html_template()    # Like form filling but for reports
- convert_html_to_pdf()                  # Like pdf_utils functions
- generate_single_report()               # Complete report generation
- generate_batch_reports()               # Batch processing like main.py
```

### Integration Points  
- Uses your existing `CustomLogger` for logging
- Uses your existing `make_directory()` and `save_json()` utilities  
- Follows same error handling patterns
- Uses same Azure OpenAI client setup
- Similar command-line argument structure

## Data Quality Features

### Geographic Consistency
- Real US cities, states, ZIP codes
- Comparable properties in same area  
- Distance calculations make sense

### Mathematical Accuracy  
- Price per sqft calculations correct
- Adjustment calculations sum properly
- Value ranges logically derived

### Market Realism
- Sale dates within last 6 months
- Price trends match market conditions
- Comparable properties similar to subject

## Extensibility  

### Easy Customizations
1. **Templates** - Modify HTML in `_get_html_template()`
2. **Data Schema** - Update prompts in `avm_prompts.json`  
3. **Output Formats** - Add new conversion methods
4. **Styling** - Update CSS in templates
5. **Data Sources** - Integrate real MLS/tax data

### Integration with Current System
- Could add AVM generation as option in main.py
- Could create unified reporting system  
- Could share persona data between forms and AVMs
- Could extend existing PDF utilities

## Troubleshooting

### Common Issues  

**"Missing environment variables"**
- Add Azure OpenAI credentials to .env file

**"Import dotenv/openai could not be resolved"** 
- Install: `pip install openai python-dotenv`

**"PDF not generated"**
- Install: `pip install weasyprint` (recommended)
- Or: `pip install pdfkit` + install wkhtmltopdf separately
- System gracefully falls back to HTML if PDF libraries unavailable

**"No images generated"**
- PDF images require PDF libraries installed
- HTML images require selenium + Chrome driver
- System continues without images if libraries unavailable

### Test Commands
```bash
# Test basic functionality
python demo_avm_simple.py

# Test full system with 1 report
python avm_template_generator.py --num_reports 1

# Check your existing system for comparison
python main.py --input_pdf="data/1040-ScheduleC/1040-ScheduleC.pdf" --number_of_variants=1
```

## Success Metrics

After running the demo, you should see:
- ✅ Realistic property data generated  
- ✅ Professional HTML reports created
- ✅ Data mathematically consistent
- ✅ Multiple output formats available
- ✅ Integration with existing system utilities
