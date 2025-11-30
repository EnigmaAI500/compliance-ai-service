"""
Test the Excel batch processing with the sample file.
"""
from app.excel_processor import process_excel_batch


def test_excel_processing():
    """Test processing the sample Excel file."""
    input_file = r"c:\Users\FirdavsMuzaffarov\Desktop\agent-projects\compliance-ai-service\customers_example_list.xlsx"
    output_file = r"c:\Users\FirdavsMuzaffarov\Desktop\agent-projects\compliance-ai-service\customers_RESULT.xlsx"
    
    print("Reading input file...")
    with open(input_file, "rb") as f:
        input_bytes = f.read()
    
    print(f"Input file size: {len(input_bytes)} bytes")
    
    print("Processing with pure algorithm...")
    output_bytes = process_excel_batch(input_bytes, use_llm=False)
    
    print(f"Output file size: {len(output_bytes)} bytes")
    
    print(f"Writing output to: {output_file}")
    with open(output_file, "wb") as f:
        f.write(output_bytes)
    
    print("✅ Processing complete!")
    print(f"   Output saved to: {output_file}")


if __name__ == "__main__":
    test_excel_processing()
