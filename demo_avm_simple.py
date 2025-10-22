#!/usr/bin/env python3
"""
AVM Demo - Simple Test Script

This script tests the basic AVM generation functionality without requiring
additional PDF/image libraries. It demonstrates the core functionality:

1. Loading AVM prompts
2. Generating synthetic property data using AI  
3. Creating HTML reports
4. Saving in multiple formats

This follows the same testing approach as the existing form filling system.
"""

import json
import os
import sys
from datetime import datetime

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)


def test_avm_basic_functionality():
    """
    Test basic AVM report generation without external PDF/image dependencies.
    This mirrors the approach used in the existing system for testing.
    """
    
    print("🏠 AVM Report Generator - Basic Functionality Test")
    print("=" * 60)
    print("Testing core AVM generation capabilities...")
    print()
    
    # Step 1: Check environment setup
    print("🔧 Checking environment setup...")
    
    try:
        # Try to load environment variables
        from dotenv import load_dotenv, find_dotenv
        load_dotenv(find_dotenv())
        print("✅ Environment variables loaded")
    except ImportError:
        print("⚠️  python-dotenv not available, using system environment")
    
    # Check Azure OpenAI setup
    try:
        from openai import AzureOpenAI
        
        required_vars = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"❌ Missing required environment variables:")
            for var in missing_vars:
                print(f"   - {var}")
            print("\nPlease add these to your .env file:")
            print("AZURE_OPENAI_API_KEY=your_api_key_here")
            print("AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/")
            print("AZURE_OPENAI_GPT4O_MINI_DEPLOYMENT=gpt-4o-mini")
            return False
        
        # Initialize client
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        print("✅ Azure OpenAI client initialized")
        
    except ImportError:
        print("❌ OpenAI package not available. Please install with: pip install openai")
        return False
    
    # Step 2: Load AVM prompts
    print("\n📋 Loading AVM prompts configuration...")
    
    prompts_file = "data/avm_prompts.json"
    if not os.path.exists(prompts_file):
        print(f"❌ Prompts file not found: {prompts_file}")
        print("Please ensure the AVM prompts file exists.")
        return False
    
    try:
        with open(prompts_file, 'r', encoding='utf-8') as f:
            prompts = json.load(f)
        print("✅ AVM prompts loaded successfully")
        print(f"   📄 Prompts file: {prompts_file}")
    except Exception as e:
        print(f"❌ Error loading prompts: {e}")
        return False
    
    # Step 3: Generate synthetic AVM data
    print("\n🤖 Generating synthetic AVM data using AI...")
    
    try:
        data_prompt = prompts["avm"]["dataGeneration"]
        
        # Add variability (same approach as existing system)
        import uuid
        random_seed = uuid.uuid4().int % 1_000_000
        prompt_with_seed = data_prompt + f"\n\n### VARIABILITY\nRandomization seed: {random_seed}"
        
        print(f"   🎲 Using randomization seed: {random_seed}")
        
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_GPT4O_MINI_DEPLOYMENT", "gpt-4o-mini"),
            response_format={"type": "json_object"},
            temperature=0.8,
            max_tokens=4000,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional real estate appraiser generating comprehensive AVM reports with realistic, mathematically consistent data."
                },
                {"role": "user", "content": prompt_with_seed}
            ]
        )
        
        avm_data = json.loads(response.choices[0].message.content)
        print("✅ Synthetic AVM data generated successfully")
        
    except Exception as e:
        print(f"❌ Error generating AVM data: {e}")
        return False
    
    # Step 4: Display generated data summary
    print(f"\n📊 Generated AVM Report Summary:")
    print(f"   🏠 Property: {avm_data['property']['address']}")
    print(f"   📍 Location: {avm_data['property']['city']}, {avm_data['property']['state']} {avm_data['property']['zip_code']}")
    print(f"   💰 Estimated Value: ${avm_data['valuation']['estimated_value']:,}")
    print(f"   📏 Square Feet: {avm_data['property']['square_feet']:,}")
    print(f"   🛏️  Layout: {avm_data['property']['bedrooms']} bed / {avm_data['property']['bathrooms']} bath")
    print(f"   📈 Confidence Score: {avm_data['valuation']['confidence_score']}%")
    print(f"   🏘️  Comparables: {len(avm_data.get('comparables', []))} properties")
    print(f"   🏫 School Rating: {avm_data['neighborhood_info']['school_rating']}/10")
    
    # Step 5: Save data and create output files
    print(f"\n💾 Saving generated data...")
    
    output_dir = "output/avm_demo"
    os.makedirs(output_dir, exist_ok=True)
    
    # Save JSON data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"avm_sample_{timestamp}.json"
    json_path = os.path.join(output_dir, json_filename)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(avm_data, f, indent=2)
    print(f"✅ JSON data saved: {json_path}")
    
    # Step 6: Generate HTML report
    print(f"\n🌐 Creating HTML report...")
    
    try:
        html_content = create_simple_avm_html_report(avm_data)
        
        html_filename = f"avm_report_{timestamp}.html"
        html_path = os.path.join(output_dir, html_filename)
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ HTML report saved: {html_path}")
        print(f"   🌐 Open this file in your web browser to view the report")
        
    except Exception as e:
        print(f"❌ Error creating HTML report: {e}")
        return False
    
    # Step 7: Success summary
    print(f"\n🎉 AVM Demo Test Completed Successfully!")
    print(f"📂 Output directory: {os.path.abspath(output_dir)}")
    print(f"📄 Files generated:")
    print(f"   • {json_filename} - Raw AVM data")
    print(f"   • {html_filename} - Professional HTML report")
    
    print(f"\n💡 Next Steps:")
    print(f"   1. Open the HTML file in your browser to see the report")
    print(f"   2. Install PDF libraries for full functionality: pip install weasyprint")
    print(f"   3. Run full batch generation: python avm_template_generator.py --num_reports 5")
    print(f"   4. Check the existing form system for comparison patterns")
    
    return True


def create_simple_avm_html_report(avm_data):
    """
    Create a simple but professional HTML report from AVM data.
    This is a simplified version of the full template for testing purposes.
    """
    
    # Generate comparables table
    comparables_html = ""
    for i, comp in enumerate(avm_data.get('comparables', []), 1):
        comparables_html += f"""
        <tr>
            <td>Comparable {i}</td>
            <td>{comp['address']}</td>
            <td>{comp['sale_date']}</td>
            <td>${comp['sale_price']:,}</td>
            <td>{comp['square_feet']:,}</td>
            <td>{comp['distance']}</td>
            <td>${comp['adjusted_price']:,}</td>
        </tr>"""
    
    # Generate amenities list
    amenities_html = ""
    for amenity in avm_data.get('neighborhood_info', {}).get('nearby_amenities', []):
        amenities_html += f"<li>{amenity}</li>"
    
    # Generate risk factors list
    risk_factors_html = ""
    for risk in avm_data.get('risk_factors', []):
        risk_factors_html += f"<li>{risk}</li>"
    
    # Generate disclaimers list
    disclaimers_html = ""
    for disclaimer in avm_data.get('disclaimers', []):
        disclaimers_html += f"<li>{disclaimer}</li>"
    
    # Determine trend styling
    trend_class = "trend-positive" if "+" in str(avm_data['market_analysis']['price_trend_6m']) else "trend-negative"
    
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AVM Report - {avm_data['property']['address']}</title>
    <style>
        /* Professional AVM Report Styling - Simplified Version */
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            line-height: 1.6; 
            color: #333; 
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        
        .container {{ 
            max-width: 900px; 
            margin: 0 auto; 
            background: white;
            border-radius: 8px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{ 
            background: linear-gradient(135deg, #1e3c72, #2a5298); 
            color: white; 
            padding: 30px; 
            text-align: center; 
        }}
        
        .header h1 {{ 
            font-size: 2.5em; 
            margin: 0 0 10px 0; 
            font-weight: 300;
        }}
        
        .header p {{ 
            margin: 5px 0; 
            font-size: 1.1em; 
            opacity: 0.9; 
        }}
        
        .section {{ 
            padding: 30px; 
            border-bottom: 1px solid #eee;
        }}
        
        .section:last-child {{
            border-bottom: none;
        }}
        
        .section h2 {{ 
            color: #1e3c72; 
            margin: 0 0 20px 0; 
            font-size: 1.8em; 
            font-weight: 400;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 10px;
        }}
        
        .value-highlight {{ 
            font-size: 2.5em; 
            font-weight: bold; 
            color: #27ae60; 
            text-align: center; 
            margin: 20px 0; 
            padding: 20px; 
            background: #f8f9fa; 
            border-radius: 8px; 
            border: 3px solid #27ae60;
        }}
        
        .info-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 20px; 
            margin: 20px 0; 
        }}
        
        .info-box {{ 
            background: #f8f9fa; 
            padding: 20px; 
            border-radius: 6px; 
            border-left: 4px solid #2a5298; 
        }}
        
        .info-box h3 {{ 
            margin: 0 0 10px 0; 
            color: #1e3c72; 
            font-size: 1.1em;
        }}
        
        .info-box p {{
            margin: 5px 0;
        }}
        
        table {{ 
            width: 100%; 
            border-collapse: collapse; 
            margin: 20px 0; 
            background: white;
            border-radius: 6px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        th {{ 
            background: #34495e; 
            color: white; 
            padding: 12px; 
            text-align: left; 
            font-weight: 600;
        }}
        
        td {{ 
            padding: 12px; 
            border-bottom: 1px solid #eee; 
        }}
        
        tr:nth-child(even) {{ 
            background: #f9f9f9; 
        }}
        
        ul {{ 
            margin: 15px 0; 
            padding-left: 20px; 
        }}
        
        li {{ 
            margin: 8px 0; 
        }}
        
        .confidence-score {{ 
            background: #27ae60; 
            color: white; 
            padding: 6px 12px; 
            border-radius: 20px; 
            font-weight: bold; 
            display: inline-block;
        }}
        
        .trend-positive {{ color: #27ae60; font-weight: bold; }}
        .trend-negative {{ color: #e74c3c; font-weight: bold; }}
        
        .footer {{ 
            background: #34495e; 
            color: white; 
            padding: 25px; 
            text-align: center; 
        }}
        
        .footer h3 {{
            margin: 0 0 15px 0;
        }}
        
        .footer ul {{
            text-align: left;
            max-width: 600px;
            margin: 0 auto;
            list-style: none;
            padding: 0;
        }}
        
        .footer li {{
            margin: 8px 0;
            padding-left: 20px;
            position: relative;
        }}
        
        .footer li:before {{
            content: "•";
            position: absolute;
            left: 0;
            color: #3498db;
            font-weight: bold;
        }}
        
        @media (max-width: 768px) {{
            .container {{ margin: 10px; }}
            .header h1 {{ font-size: 2em; }}
            .info-grid {{ grid-template-columns: 1fr; }}
            .value-highlight {{ font-size: 2em; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header Section -->
        <div class="header">
            <h1>🏠 AVM Property Report</h1>
            <p><strong>Report ID:</strong> {avm_data['report_info']['report_id']}</p>
            <p><strong>Generated:</strong> {avm_data['report_info']['report_date']} | <strong>Effective:</strong> {avm_data['report_info']['effective_date']}</p>
            <p><strong>Prepared by:</strong> {avm_data['report_info']['prepared_by']}</p>
        </div>
        
        <!-- Property Information -->
        <div class="section">
            <h2>Property Information</h2>
            <div class="info-grid">
                <div class="info-box">
                    <h3>Property Address</h3>
                    <p>{avm_data['property']['address']}</p>
                    <p>{avm_data['property']['city']}, {avm_data['property']['state']} {avm_data['property']['zip_code']}</p>
                    <p><strong>APN:</strong> {avm_data['property']['apn']}</p>
                </div>
                <div class="info-box">
                    <h3>Property Details</h3>
                    <p><strong>Type:</strong> {avm_data['property']['property_type']}</p>
                    <p><strong>Year Built:</strong> {avm_data['property']['year_built']}</p>
                    <p><strong>Condition:</strong> {avm_data['property']['condition']}</p>
                    <p><strong>Occupancy:</strong> {avm_data['property']['occupancy']}</p>
                </div>
                <div class="info-box">
                    <h3>Size & Layout</h3>
                    <p><strong>Living Space:</strong> {avm_data['property']['square_feet']:,} sq ft</p>
                    <p><strong>Lot Size:</strong> {avm_data['property']['lot_size']:,} sq ft</p>
                    <p><strong>Layout:</strong> {avm_data['property']['bedrooms']} bed / {avm_data['property']['bathrooms']} bath</p>
                </div>
                <div class="info-box">
                    <h3>Features</h3>
                    <p><strong>Garage:</strong> {avm_data['property']['garage']}</p>
                    <p><strong>Pool:</strong> {avm_data['property']['pool']}</p>
                </div>
            </div>
        </div>
        
        <!-- Valuation Summary -->
        <div class="section">
            <h2>Valuation Summary</h2>
            <div class="value-highlight">
                Estimated Market Value: ${avm_data['valuation']['estimated_value']:,}
            </div>
            <div class="info-grid">
                <div class="info-box">
                    <h3>Value Range</h3>
                    <p><strong>Low:</strong> ${avm_data['valuation']['value_range_low']:,}</p>
                    <p><strong>High:</strong> ${avm_data['valuation']['value_range_high']:,}</p>
                </div>
                <div class="info-box">
                    <h3>Confidence</h3>
                    <p><span class="confidence-score">{avm_data['valuation']['confidence_score']}% Confident</span></p>
                </div>
                <div class="info-box">
                    <h3>Price Metrics</h3>
                    <p><strong>Price/Sq Ft:</strong> ${avm_data['valuation']['price_per_sqft']}</p>
                </div>
                <div class="info-box">
                    <h3>Methodology</h3>
                    <p>{avm_data['valuation']['methodology']}</p>
                    <p><small>{avm_data['valuation']['data_sources']}</small></p>
                </div>
            </div>
        </div>
        
        <!-- Comparable Sales -->
        <div class="section">
            <h2>Comparable Sales Analysis</h2>
            <table>
                <thead>
                    <tr>
                        <th>Property</th>
                        <th>Address</th>
                        <th>Sale Date</th>
                        <th>Sale Price</th>
                        <th>Sq Ft</th>
                        <th>Distance</th>
                        <th>Adjusted Price</th>
                    </tr>
                </thead>
                <tbody>
                    {comparables_html}
                </tbody>
            </table>
        </div>
        
        <!-- Market Analysis -->
        <div class="section">
            <h2>Market Analysis</h2>
            <div class="info-grid">
                <div class="info-box">
                    <h3>Market Conditions</h3>
                    <p><strong>Status:</strong> {avm_data['market_analysis']['market_conditions']}</p>
                    <p><strong>Inventory:</strong> {avm_data['market_analysis']['inventory_level']}</p>
                </div>
                <div class="info-box">
                    <h3>Price Trends</h3>
                    <p><strong>6-Month Trend:</strong> <span class="{trend_class}">{avm_data['market_analysis']['price_trend_6m']}</span></p>
                    <p><strong>Median Price/Sq Ft:</strong> ${avm_data['market_analysis']['median_price_per_sqft']}</p>
                </div>
                <div class="info-box">
                    <h3>Market Activity</h3>
                    <p><strong>Avg Days on Market:</strong> {avm_data['market_analysis']['days_on_market_avg']} days</p>
                    <p><strong>Absorption Rate:</strong> {avm_data['market_analysis']['absorption_rate']}</p>
                </div>
            </div>
        </div>
        
        <!-- Neighborhood Information -->
        <div class="section">
            <h2>Neighborhood Profile</h2>
            <div class="info-grid">
                <div class="info-box">
                    <h3>Education</h3>
                    <p><strong>School District:</strong> {avm_data['neighborhood_info']['school_district']}</p>
                    <p><strong>School Rating:</strong> {avm_data['neighborhood_info']['school_rating']}/10</p>
                </div>
                <div class="info-box">
                    <h3>Community Metrics</h3>
                    <p><strong>Crime Rate:</strong> {avm_data['neighborhood_info']['crime_rate']}</p>
                    <p><strong>Walkability:</strong> {avm_data['neighborhood_info']['walkability_score']}/100</p>
                </div>
                <div class="info-box" style="grid-column: 1/-1;">
                    <h3>Nearby Amenities</h3>
                    <ul>
                        {amenities_html}
                    </ul>
                </div>
            </div>
        </div>
        
        <!-- Risk Factors -->
        <div class="section">
            <h2>Risk Factors & Considerations</h2>
            <ul>
                {risk_factors_html}
            </ul>
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <h3>Important Disclaimers</h3>
            <ul>
                {disclaimers_html}
            </ul>
            <p style="margin-top: 20px; font-size: 0.9em;">
                <strong>Report Generated:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
            </p>
            <p style="font-size: 0.9em;">
                <strong>Client:</strong> {avm_data['report_info']['client_name']} | 
                <strong>License:</strong> {avm_data['report_info'].get('appraiser_license', 'N/A')}
            </p>
        </div>
    </div>
</body>
</html>"""
    
    return html_template


if __name__ == "__main__":
    """
    Main execution - run the basic AVM functionality test
    """
    print("Starting AVM Demo Test...")
    print("This tests the core functionality without requiring PDF/image libraries.")
    print()
    
    success = test_avm_basic_functionality()
    
    if success:
        print(f"\n✅ AVM Demo Test PASSED!")
        print(f"The AVM generation system is working correctly.")
        print(f"You can now run the full system with additional features.")
    else:
        print(f"\n❌ AVM Demo Test FAILED!")
        print(f"Please check the error messages above and fix any issues.")
        print(f"Common issues:")
        print(f"  • Missing Azure OpenAI credentials in .env file")
        print(f"  • Missing Python packages (openai, python-dotenv)")
        print(f"  • Missing AVM prompts configuration file")
    
    print(f"\n🔚 Demo test completed.")
