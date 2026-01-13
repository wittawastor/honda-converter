import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

st.set_page_config(page_title="Honda Converter", layout="wide")

st.title("🚗 Honda OEM PDF Converter")

# File uploader
uploaded_file = st.file_uploader("Upload Honda PDF", type="pdf")

if uploaded_file:
    try:
        all_rows = []
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                
                # Extract PO
                po_match = re.search(r'PO\d+', text)
                current_po = po_match.group() if po_match else ""
                
                # Extract Table Rows
                lines = text.split("\n")
                for line in lines:
                    # Matches the specific Honda part row format
                    match = re.search(r'^(\d+)\s+([A-Z0-9-]+)\s+(.*?)\s+(\d+)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})$', line)
                    if match:
                        all_rows.append({
                            "Page": page.page_number,
                            "No": match.group(1),
                            "Product Code": match.group(2),
                            "Name": match.group(3),
                            "Qty": match.group(4),
                            "Price": match.group(5),
                            "Total": match.group(6),
                            "PO": current_po
                        })

        if all_rows:
            df = pd.DataFrame(all_rows)
            st.success(f"Extracted {len(df)} items!")
            st.dataframe(df)
            
            # Download Button
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", csv, "honda_data.csv", "text/csv")
        else:
            st.error("Could not find any part rows. Is this the correct Honda PDF format?")
            
    except Exception as e:
        st.error(f"An error occurred: {e}")
