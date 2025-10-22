#!/usr/bin/env python3
"""
AVM Template Generator - Option 1 Implementation

This module extends the existing form filling system to generate AVM (Automated Valuation Model) 
reports using a template-based approach. It follows the same pattern as the current system:

1. Load prompts from JSON configuration
2. Use AI to generate synthetic property data
3. Create professional HTML templates
4. Convert to PDF and images
5. Output in multiple formats (JSON, HTML, PDF, Images)

Author: GitHub Copilot
Date: August 2025
"""

import argparse
import datetime
import json
import os
import pytz
import uuid
from typing import Dict, List, Any, Optional

# Import existing utilities from t# Import existing utilities from the current system
from utils.general_utils import make_directory, save_json
from utils.logger_utils import CustomLogger

# External dependencies (same as current system)
from dotenv import load_dotenv, find_dotenv
from openai import AzureOpenAI


class AVMReportGenerator:
    """
    AVM Report Generator using Template-Based Approach
    
    This class generates synthetic AVM reports by:
    1. Using AI to create realistic property and market data
    2. Applying professional HTML templates 
    3. Converting to multiple output formats (JSON, HTML, PDF, Images)
    4. Following the same patterns as the existing form filling system
    """
    
    def __init__(self, logger: Optional[CustomLogger] = None):
        """
        Initialize the AVM report generator.
        
        Args:
            logger: Optional logger instance. If None, creates a new logger.
        """
        self.logger = logger or CustomLogger("AVMReportGenerator", "AVM")
        
        # Initialize Azure OpenAI client (same as existing system)
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        self.logger.info("AVM Report Generator initialized")
    
    def generate_avm_data(self, prompts_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate synthetic AVM data using AI (similar to generate_synthetic_data in existing system).
        
        Args:
            prompts_config: Prompts configuration loaded from JSON
            
        Returns:
            Dictionary containing complete AVM report data
        """
        try:
            # Get the data generation prompt
            data_prompt = prompts_config["avm"]["dataGeneration"]
            
            # Add randomization for variety (same approach as existing system)
            random_seed = uuid.uuid4().int % 1_000_000
            prompt_with_seed = data_prompt + f"\n\n### VARIABILITY\nRandomization seed: {random_seed}"
            
            self.logger.info(f"Generating AVM data with seed: {random_seed}")
            
            # Call Azure OpenAI (same pattern as existing system)
            response = self.client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_GPT4O_MINI_DEPLOYMENT", "gpt-4o-mini"),
                response_format={"type": "json_object"},
                temperature=0.9,  # Higher temperature for more variety
                max_tokens=4000,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional real estate appraiser generating comprehensive AVM reports with realistic, mathematically consistent data."
                    },
                    {"role": "user", "content": prompt_with_seed}
                ]
            )
            
            # Parse the response
            avm_data = json.loads(response.choices[0].message.content)
            
            self.logger.info("AVM data generated successfully")
            return avm_data
            
        except Exception as e:
            self.logger.error(f"Error generating AVM data: {e}")
            raise
    
    def create_professional_html_template(self, avm_data: Dict[str, Any]) -> str:
        """
        Create a professional HTML template for the AVM report.
        This follows the template approach similar to form filling but creates
        a comprehensive report layout instead of filling form fields.
        
        Args:
            avm_data: Complete AVM report data
            
        Returns:
            Formatted HTML string
        """
        try:
            # Generate comparable sales table rows
            comparables_html = self._generate_comparables_table(avm_data.get('comparables', []))
            
            # Generate risk factors list
            risk_factors_html = self._generate_list_items(avm_data.get('risk_factors', []))
            
            # Generate disclaimers list  
            disclaimers_html = self._generate_list_items(avm_data.get('disclaimers', []))
            
            # Generate amenities list
            amenities_html = self._generate_list_items(
                avm_data.get('neighborhood_info', {}).get('nearby_amenities', [])
            )
            
            # Main HTML template with professional styling
            html_template = self._get_html_template()
            
            # Format the template with actual data
            formatted_html = html_template.format(
                # Report Info
                report_id=avm_data['report_info']['report_id'],
                report_date=avm_data['report_info']['report_date'],
                effective_date=avm_data['report_info']['effective_date'],
                prepared_by=avm_data['report_info']['prepared_by'],
                client_name=avm_data['report_info']['client_name'],
                appraiser_license=avm_data['report_info'].get('appraiser_license', 'N/A'),
                
                # Property Info
                address=avm_data['property']['address'],
                city=avm_data['property']['city'],
                state=avm_data['property']['state'],
                zip_code=avm_data['property']['zip_code'],
                apn=avm_data['property']['apn'],
                property_type=avm_data['property']['property_type'],
                year_built=avm_data['property']['year_built'],
                square_feet=avm_data['property']['square_feet'],
                lot_size=avm_data['property']['lot_size'],
                bedrooms=avm_data['property']['bedrooms'],
                bathrooms=avm_data['property']['bathrooms'],
                garage=avm_data['property']['garage'],
                pool=avm_data['property']['pool'],
                condition=avm_data['property']['condition'],
                occupancy=avm_data['property']['occupancy'],
                
                # Valuation Info
                estimated_value=avm_data['valuation']['estimated_value'],
                value_range_low=avm_data['valuation']['value_range_low'],
                value_range_high=avm_data['valuation']['value_range_high'],
                confidence_score=avm_data['valuation']['confidence_score'],
                price_per_sqft=avm_data['valuation']['price_per_sqft'],
                methodology=avm_data['valuation']['methodology'],
                data_sources=avm_data['valuation']['data_sources'],
                
                # Market Analysis
                median_price_per_sqft=avm_data['market_analysis']['median_price_per_sqft'],
                days_on_market_avg=avm_data['market_analysis']['days_on_market_avg'],
                price_trend_6m=avm_data['market_analysis']['price_trend_6m'],
                inventory_level=avm_data['market_analysis']['inventory_level'],
                market_conditions=avm_data['market_analysis']['market_conditions'],
                absorption_rate=avm_data['market_analysis']['absorption_rate'],
                
                # Neighborhood Info
                school_district=avm_data['neighborhood_info']['school_district'],
                school_rating=avm_data['neighborhood_info']['school_rating'],
                crime_rate=avm_data['neighborhood_info']['crime_rate'],
                walkability_score=avm_data['neighborhood_info']['walkability_score'],
                
                # Dynamic content
                comparables_html=comparables_html,
                risk_factors_html=risk_factors_html,
                disclaimers_html=disclaimers_html,
                amenities_html=amenities_html,
                
                # Trend styling
                trend_class=self._get_trend_class(avm_data['market_analysis']['price_trend_6m'])
            )
            
            self.logger.info("Professional HTML template created successfully")
            return formatted_html
            
        except Exception as e:
            self.logger.error(f"Error creating HTML template: {e}")
            raise
    
    def _generate_comparables_table(self, comparables: List[Dict[str, Any]]) -> str:
        """Generate HTML table rows for comparable properties."""
        rows_html = ""
        for comp in comparables:
            rows_html += f"""
            <tr>
                <td>Comp {comp['comp_number']}</td>
                <td>{comp['address']}</td>
                <td>{comp['sale_date']}</td>
                <td>${comp['sale_price']:,}</td>
                <td>{comp['square_feet']:,}</td>
                <td>{comp['bedrooms']}/{comp['bathrooms']}</td>
                <td>{comp['distance']}</td>
                <td>${comp['adjusted_price']:,}</td>
            </tr>"""
        return rows_html
    
    def _generate_list_items(self, items: List[str]) -> str:
        """Generate HTML list items from a list of strings."""
        return "".join([f"<li>{item}</li>" for item in items])
    
    def _get_trend_class(self, trend_value: str) -> str:
        """Determine CSS class for price trend display."""
        return "trend-positive" if "+" in trend_value else "trend-negative"
    
    def convert_html_to_pdf(self, html_content: str, output_path: str) -> str:
        """
        Convert HTML to PDF using available libraries.
        Attempts multiple methods similar to existing system's approach.
        
        Args:
            html_content: HTML content to convert
            output_path: Desired PDF output path
            
        Returns:
            Actual output path (may be HTML if PDF conversion fails)
        """
        try:
            # Method 1: Try WeasyPrint (best quality)
            try:
                import weasyprint
                weasyprint.HTML(string=html_content).write_pdf(output_path)
                self.logger.info(f"PDF generated using WeasyPrint: {output_path}")
                return output_path
            except ImportError:
                self.logger.warning("WeasyPrint not available, trying alternative methods")
            
            # Method 2: Try pdfkit (requires wkhtmltopdf)
            try:
                import pdfkit
                options = {
                    'page-size': 'Letter',
                    'margin-top': '0.75in',
                    'margin-right': '0.75in', 
                    'margin-bottom': '0.75in',
                    'margin-left': '0.75in',
                    'encoding': "UTF-8",
                    'no-outline': None,
                    'enable-local-file-access': None
                }
                pdfkit.from_string(html_content, output_path, options=options)
                self.logger.info(f"PDF generated using pdfkit: {output_path}")
                return output_path
            except (ImportError, OSError) as e:
                self.logger.warning(f"pdfkit not available or wkhtmltopdf missing: {e}")
            
            # Fallback: Save as HTML
            html_path = output_path.replace('.pdf', '.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            self.logger.info(f"PDF conversion failed, saved as HTML: {html_path}")
            return html_path
            
        except Exception as e:
            self.logger.error(f"Error in HTML to PDF conversion: {e}")
            # Final fallback
            html_path = output_path.replace('.pdf', '.html') 
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            return html_path
    
    def convert_to_images(self, file_path: str, output_dir: str) -> List[str]:
        """
        Convert PDF/HTML to images using existing system utilities when possible.
        
        Args:
            file_path: Path to PDF or HTML file
            output_dir: Directory to save images
            
        Returns:
            List of generated image file paths
        """
        try:
            make_directory(output_dir)
            
            # If we have a PDF, use existing pdf_to_images function
            if file_path.endswith('.pdf') and os.path.exists(file_path):
                try:
                    from utils.pdf_utils import pdf_to_images
                    pdf_to_images(file_path, output_dir, "AVM Report", self.logger)
                    
                    # Return list of generated image paths
                    image_files = [f for f in os.listdir(output_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                    image_paths = [os.path.join(output_dir, f) for f in sorted(image_files)]
                    
                    self.logger.info(f"Generated {len(image_paths)} images from PDF")
                    return image_paths
                except Exception as e:
                    self.logger.warning(f"PDF to images conversion failed: {e}")
            
            # For HTML files or PDF conversion failure, try screenshot approach
            if file_path.endswith('.html'):
                try:
                    # Try using selenium for HTML screenshots
                    from selenium import webdriver
                    from selenium.webdriver.chrome.options import Options
                    
                    chrome_options = Options()
                    chrome_options.add_argument("--headless")
                    chrome_options.add_argument("--no-sandbox")
                    chrome_options.add_argument("--disable-dev-shm-usage")
                    chrome_options.add_argument("--window-size=1200,1600")
                    
                    driver = webdriver.Chrome(options=chrome_options)
                    driver.get(f"file://{os.path.abspath(file_path)}")
                    
                    screenshot_path = os.path.join(output_dir, "Page1.png")
                    driver.save_screenshot(screenshot_path)
                    driver.quit()
                    
                    self.logger.info(f"HTML screenshot saved: {screenshot_path}")
                    return [screenshot_path]
                    
                except ImportError:
                    self.logger.warning("Selenium not available for HTML screenshot")
                except Exception as e:
                    self.logger.warning(f"HTML screenshot failed: {e}")
            
            self.logger.warning("No image conversion method available")
            return []
            
        except Exception as e:
            self.logger.error(f"Error converting to images: {e}")
            return []
    
    def generate_single_report(self, prompts_config: Dict[str, Any], output_dir: str, 
                             report_id: Optional[str] = None) -> Dict[str, str]:
        """
        Generate a single complete AVM report in all formats.
        
        Args:
            prompts_config: Prompts configuration
            output_dir: Output directory
            report_id: Optional specific report ID
            
        Returns:
            Dictionary with paths to generated files
        """
        try:
            # Generate unique report ID if not provided
            if not report_id:
                timestamp = datetime.datetime.now(pytz.UTC).strftime("%m_%d_%y_%H_%M_%S")
                unique_id = str(uuid.uuid4())[:8]
                report_id = f"AVM_{timestamp}_{unique_id}"
            
            # Create report directory
            report_dir = os.path.join(output_dir, report_id)
            make_directory(report_dir)
            
            self.logger.info(f"Generating AVM report: {report_id}")
            
            # Step 1: Generate synthetic data
            avm_data = self.generate_avm_data(prompts_config)
            
            # Step 2: Save JSON data
            json_path = os.path.join(report_dir, f"{report_id}.json")
            save_json(avm_data, json_path, f"AVM Report {report_id}", self.logger)
            
            # Step 3: Generate HTML report
            html_content = self.create_professional_html_template(avm_data)
            html_path = os.path.join(report_dir, f"{report_id}.html")
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Step 4: Convert to PDF
            pdf_path = os.path.join(report_dir, f"{report_id}.pdf")
            actual_pdf_path = self.convert_html_to_pdf(html_content, pdf_path)
            
            # Step 5: Generate images
            images_dir = os.path.join(report_dir, "images")
            image_paths = self.convert_to_images(actual_pdf_path, images_dir)
            
            result = {
                'report_id': report_id,
                'report_dir': report_dir,
                'json_path': json_path,
                'html_path': html_path,
                'pdf_path': actual_pdf_path,
                'images_dir': images_dir,
                'image_paths': image_paths
            }
            
            self.logger.info(f"AVM report generated successfully: {report_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating single report: {e}")
            raise
    
    def generate_batch_reports(self, num_reports: int, output_dir: str, 
                             prompts_file: str = "data/avm_prompts.json") -> List[Dict[str, str]]:
        """
        Generate multiple AVM reports (similar to existing system's batch generation).
        
        Args:
            num_reports: Number of reports to generate
            output_dir: Output directory
            prompts_file: Path to prompts configuration file
            
        Returns:
            List of dictionaries with report information
        """
        try:
            # Load prompts configuration
            if not os.path.exists(prompts_file):
                raise FileNotFoundError(f"Prompts file not found: {prompts_file}")
            
            with open(prompts_file, 'r', encoding='utf-8') as f:
                prompts_config = json.load(f)
            
            # Create output directory
            make_directory(output_dir)
            
            self.logger.info(f"Starting batch generation of {num_reports} AVM reports")
            
            generated_reports = []
            
            for i in range(1, num_reports + 1):
                try:
                    self.logger.info(f"Generating report {i}/{num_reports}")
                    
                    report_result = self.generate_single_report(prompts_config, output_dir)
                    generated_reports.append(report_result)
                    
                    # Progress feedback
                    print(f"Generated report {i}/{num_reports}: {report_result['report_id']}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to generate report {i}/{num_reports}: {e}")
                    print(f"Failed to generate report {i}/{num_reports}: {e}")
                    continue
            
            self.logger.info(f"Batch generation completed. Generated {len(generated_reports)}/{num_reports} reports")
            return generated_reports
            
        except Exception as e:
            self.logger.error(f"Error in batch report generation: {e}")
            raise
    
    def _get_html_template(self) -> str:
        """
        Returns the professional HTML template.
        This is a large template string that defines the complete report layout.
        """
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AVM Report - {address}</title>
    <style>
        /* Professional AVM Report Styling */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            line-height: 1.6; 
            color: #333; 
            background-color: #f8f9fa;
        }}
        
        .container {{ 
            max-width: 1000px; 
            margin: 0 auto; 
            padding: 20px; 
            background: white;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        
        /* Header Section */
        .header {{ 
            background: linear-gradient(135deg, #1e3c72, #2a5298); 
            color: white; 
            padding: 30px; 
            text-align: center; 
            margin-bottom: 30px;
            border-radius: 8px;
        }}
        
        .header h1 {{ 
            font-size: 2.5em; 
            margin-bottom: 10px; 
            font-weight: 300;
        }}
        
        .header p {{ 
            font-size: 1.1em; 
            opacity: 0.9; 
            margin: 5px 0;
        }}
        
        /* Section Styling */
        .section {{ 
            background: white; 
            margin: 20px 0; 
            padding: 25px; 
            border-radius: 8px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.08); 
            border-left: 5px solid #2a5298;
        }}
        
        .section h2 {{ 
            color: #1e3c72; 
            margin-bottom: 20px; 
            font-size: 1.8em; 
            border-bottom: 2px solid #ecf0f1; 
            padding-bottom: 10px; 
            font-weight: 400;
        }}
        
        /* Specialized section backgrounds */
        .property-info {{ background: linear-gradient(135deg, #f8f9fa, #e9ecef); }}
        .valuation {{ background: linear-gradient(135deg, #d4edda, #c3e6cb); }}
        .comparables {{ background: linear-gradient(135deg, #fff3cd, #ffeaa7); }}
        .market {{ background: linear-gradient(135deg, #cce5ff, #b3d9ff); }}
        .neighborhood {{ background: linear-gradient(135deg, #f0e6ff, #e6ccff); }}
        
        /* Grid Layout */
        .info-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); 
            gap: 20px; 
            margin: 20px 0; 
        }}
        
        .info-item {{ 
            background: rgba(255,255,255,0.8); 
            padding: 15px; 
            border-radius: 6px; 
            border-left: 4px solid #2a5298; 
            transition: transform 0.2s ease;
        }}
        
        .info-item:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        
        .info-item strong {{ 
            color: #1e3c72; 
            display: block;
            margin-bottom: 8px;
            font-size: 1.1em;
        }}
        
        /* Value Highlight */
        .value-highlight {{ 
            font-size: 2.5em; 
            font-weight: bold; 
            color: #27ae60; 
            text-align: center; 
            margin: 25px 0; 
            padding: 25px; 
            background: rgba(255,255,255,0.95); 
            border-radius: 12px; 
            border: 3px solid #27ae60;
        }}
        
        .confidence-score {{ 
            display: inline-block; 
            background: #27ae60; 
            color: white; 
            padding: 8px 16px; 
            border-radius: 25px; 
            font-weight: bold; 
            font-size: 1.1em;
        }}
        
        /* Table Styling */
        table {{ 
            width: 100%; 
            border-collapse: collapse; 
            margin: 20px 0; 
            background: rgba(255,255,255,0.95); 
            border-radius: 8px; 
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        th {{ 
            background: #34495e; 
            color: white; 
            padding: 15px 12px; 
            text-align: left; 
            font-weight: 600;
            font-size: 0.95em;
        }}
        
        td {{ 
            padding: 12px; 
            border-bottom: 1px solid #ecf0f1; 
        }}
        
        tr:nth-child(even) {{ 
            background: rgba(52, 73, 94, 0.05); 
        }}
        
        tr:hover {{ 
            background: rgba(42, 82, 152, 0.1); 
        }}
        
        /* Lists */
        ul {{ 
            margin: 15px 0; 
            padding-left: 25px; 
        }}
        
        li {{ 
            margin: 8px 0; 
            line-height: 1.5;
        }}
        
        /* Trend Indicators */
        .trend-positive {{ 
            color: #27ae60; 
            font-weight: bold; 
        }}
        
        .trend-negative {{ 
            color: #e74c3c; 
            font-weight: bold; 
        }}
        
        /* Footer */
        .footer {{ 
            background: #34495e; 
            color: white; 
            padding: 25px; 
            text-align: center; 
            margin-top: 30px; 
            border-radius: 8px; 
        }}
        
        .footer h3 {{
            margin-bottom: 15px;
            font-size: 1.3em;
        }}
        
        .footer p {{ 
            margin: 8px 0; 
            opacity: 0.9;
        }}
        
        .footer ul {{
            list-style: none; 
            text-align: left; 
            max-width: 800px; 
            margin: 0 auto;
            padding: 0;
        }}
        
        .footer li {{
            margin: 10px 0;
            padding-left: 20px;
            position: relative;
        }}
        
        .footer li:before {{
            content: "*";
            position: absolute;
            left: 0;
            color: #3498db;
        }}
        
        /* Responsive Design */
        @media (max-width: 768px) {{
            .container {{ padding: 15px; }}
            .header h1 {{ font-size: 2em; }}
            .info-grid {{ grid-template-columns: 1fr; }}
            .value-highlight {{ font-size: 2em; }}
            th, td {{ padding: 8px; font-size: 0.9em; }}
        }}
        
        @media print {{
            body {{ background: white; }}
            .container {{ box-shadow: none; }}
            .section {{ break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Report Header -->
        <div class="header">
            <h1>Automated Valuation Model Report</h1>
            <p><strong>Report ID:</strong> {report_id} | <strong>Date:</strong> {report_date}</p>
            <p><strong>Prepared by:</strong> {prepared_by}</p>
            <p><strong>License #:</strong> {appraiser_license} | <strong>Client:</strong> {client_name}</p>
        </div>
        
        <!-- Property Information Section -->
        <div class="section property-info">
            <h2>Property Information</h2>
            <div class="info-grid">
                <div class="info-item">
                    <strong>Property Address</strong>
                    {address}<br>
                    {city}, {state} {zip_code}
                </div>
                <div class="info-item">
                    <strong>Property Details</strong>
                    Type: {property_type}<br>
                    Year Built: {year_built}<br>
                    APN: {apn}
                </div>
                <div class="info-item">
                    <strong>Size & Layout</strong>
                    Square Feet: {square_feet:,} sq ft<br>
                    Lot Size: {lot_size:,} sq ft<br>
                    Layout: {bedrooms} bed / {bathrooms} bath
                </div>
                <div class="info-item">
                    <strong>Property Features</strong>
                    Condition: {condition}<br>
                    Garage: {garage}<br>
                    Pool: {pool}<br>
                    Occupancy: {occupancy}
                </div>
            </div>
        </div>
        
        <!-- Valuation Summary Section -->
        <div class="section valuation">
            <h2>Valuation Summary</h2>
            <div class="value-highlight">
                Estimated Market Value: ${estimated_value:,}
            </div>
            <div class="info-grid">
                <div class="info-item">
                    <strong>Value Range</strong>
                    Low: ${value_range_low:,}<br>
                    High: ${value_range_high:,}
                </div>
                <div class="info-item">
                    <strong>Confidence Assessment</strong>
                    <span class="confidence-score">{confidence_score}% Confidence</span>
                </div>
                <div class="info-item">
                    <strong>Price Metrics</strong>
                    Price per Sq Ft: ${price_per_sqft}<br>
                    Effective Date: {effective_date}
                </div>
                <div class="info-item">
                    <strong>Valuation Method</strong>
                    Methodology: {methodology}<br>
                    Data Sources: {data_sources}
                </div>
            </div>
        </div>
        
        <!-- Comparable Sales Section -->
        <div class="section comparables">
            <h2>Comparable Sales Analysis</h2>
            <p>The following recently sold properties were used to establish market value:</p>
            <table>
                <thead>
                    <tr>
                        <th>Property</th>
                        <th>Address</th>
                        <th>Sale Date</th>
                        <th>Sale Price</th>
                        <th>Square Feet</th>
                        <th>Bed/Bath</th>
                        <th>Distance</th>
                        <th>Adjusted Price</th>
                    </tr>
                </thead>
                <tbody>
                    {comparables_html}
                </tbody>
            </table>
        </div>
        
        <!-- Market Analysis Section -->
        <div class="section market">
            <h2>Market Analysis</h2>
            <div class="info-grid">
                <div class="info-item">
                    <strong>Market Conditions</strong>
                    Current Status: {market_conditions}<br>
                    Inventory Level: {inventory_level}
                </div>
                <div class="info-item">
                    <strong>Price Trends</strong>
                    6-Month Trend: <span class="{trend_class}">{price_trend_6m}</span><br>
                    Median Price/Sq Ft: ${median_price_per_sqft}
                </div>
                <div class="info-item">
                    <strong>Market Activity</strong>
                    Avg Days on Market: {days_on_market_avg} days<br>
                    Absorption Rate: {absorption_rate}
                </div>
                <div class="info-item">
                    <strong>Market Outlook</strong>
                    Current market shows {market_conditions} with {inventory_level} inventory levels.
                </div>
            </div>
        </div>
        
        <!-- Neighborhood Information Section -->
        <div class="section neighborhood">
            <h2>Neighborhood Profile</h2>
            <div class="info-grid">
                <div class="info-item">
                    <strong>Education</strong>
                    School District: {school_district}<br>
                    School Rating: {school_rating}/10
                </div>
                <div class="info-item">
                    <strong>Community Metrics</strong>
                    Crime Rate: {crime_rate}<br>
                    Walkability Score: {walkability_score}/100
                </div>
                <div class="info-item" style="grid-column: 1/-1;">
                    <strong>Nearby Amenities</strong>
                    <ul>
                        {amenities_html}
                    </ul>
                </div>
            </div>
        </div>
        
        <!-- Risk Factors Section -->
        <div class="section">
            <h2>Risk Factors & Considerations</h2>
            <ul>
                {risk_factors_html}
            </ul>
        </div>
        
        <!-- Footer with Disclaimers -->
        <div class="footer">
            <h3>Important Disclaimers</h3>
            <ul>
                {disclaimers_html}
            </ul>
            <hr style="margin: 20px 0; opacity: 0.3;">
            <p><strong>Report Prepared:</strong> {report_date} | <strong>Effective Date:</strong> {effective_date}</p>
            <p><strong>Prepared by:</strong> {prepared_by} | <strong>License:</strong> {appraiser_license}</p>
            <p><strong>Client:</strong> {client_name}</p>
            <p style="margin-top: 15px; font-size: 0.9em; opacity: 0.8;">
                This report was generated using advanced automated valuation modeling technology.
            </p>
        </div>
    </div>
</body>
</html>'''


def main():
    """
    Main function for command-line usage.
    Follows the same pattern as the existing main.py file.
    """
    parser = argparse.ArgumentParser(description="Generate synthetic AVM reports using template approach")
    parser.add_argument("--num_reports", type=int, default=3, help="Number of reports to generate")
    parser.add_argument("--output_directory", type=str, default="output/avm_reports", help="Output directory")
    parser.add_argument("--prompts_file", type=str, default="data/avm_prompts.json", help="Prompts JSON file")
    
    args = parser.parse_args()
    
    # Load environment variables (same as existing system)
    load_dotenv(find_dotenv())
    
    # Initialize logger (same pattern as existing system)
    logger = CustomLogger("AVMReportGenerator", "AVM")
    
    print("AVM Template-Based Report Generator")
    print("=" * 60)
    print(f"Generating {args.num_reports} AVM reports")
    print(f"Output directory: {args.output_directory}")
    print(f"Prompts file: {args.prompts_file}")
    print()
    
    try:
        # Initialize generator
        generator = AVMReportGenerator(logger)
        
        # Generate reports
        reports = generator.generate_batch_reports(
            num_reports=args.num_reports,
            output_dir=args.output_directory,
            prompts_file=args.prompts_file
        )
        
        # Display results
        print(f"\nSuccessfully generated {len(reports)} AVM reports!")
        print(f"Reports saved in: {os.path.abspath(args.output_directory)}")
        print("\nGenerated Reports:")
        
        for i, report in enumerate(reports, 1):
            print(f"\n  Report {i}: {report['report_id']}")
            print(f"    JSON: {os.path.basename(report['json_path'])}")
            print(f"    HTML: {os.path.basename(report['html_path'])}")
            print(f"    PDF: {os.path.basename(report['pdf_path'])}")
            if report['image_paths']:
                print(f"    Images: {len(report['image_paths'])} files")
        
        print(f"\nAll reports generated successfully!")
        print(f"Check the output directory: {os.path.abspath(args.output_directory)}")
        
    except Exception as e:
        print(f"Error generating AVM reports: {e}")
        logger.error(f"AVM report generation failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
