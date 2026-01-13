import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

st.set_page_config(page_title="Honda OEM PDF Converter", layout="wide")

st.title("🚗 Honda OEM PDF Converter")
st.markdown("""
Upload your Honda OEM PDF files to extract product data and automatically link PO numbers to their respective rows.
""")

def process_pdf(file):
    all_rows = []
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                
                # 1. Determine Page Number
                page_num_str = "Unknown"
                page_match = re.search(r'หน้าที่\s*:\s*(\d+)/', text)
                if page_match:
                    page_num_str = page_match.group(1)
                else:
                    page_num_str = str(page.page_number)

                # 2. Extract PO number from the page
                current_page_po = ""
                po_match = re.search(r'PO\d+', text)
                if po_match:
                    current_page_po = po_match.group()

                lines = [l.strip() for l in text.split("\n") if l.strip()]
                page_has_products = False

                for line in lines:
                    # 3. Extract product rows (No, Code, Name, Qty, Price, Total)
                    match = re.search(r'^(\d+)\s+([A-Z0-9-]+)\s+(.*?)\s+(\d+)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})$', line)
                    if match:
                        page_has_products = True
                        all_rows.append({
                            "Page": page_num_str,
                            "No": int(match.group(1)),
                            "Product Code": match.group(2),
                            "Part Name": match.group(3).strip(),
                            "Qty": int(match.group(4)),
                            "Price": float(match.group(5).replace(",", "")),
                            "Total": float(match.group(6).replace(",", "")),
                            "PO": current_page_po 
                        })
                
                # 4. Keep PO Row if no products found on that page
                if current_page_po and not page_has_products:
                    all_rows.append({
                        "Page": page_num_str,
                        "No": None,
                        "Product Code": "PO LOCATION",
                        "Part Name": "Found PO at bottom of page",
                        "Qty": 0, "Price": 0, "Total": 0,
                        "PO": current_page_po
                    })

        if not all_rows:
            return None

        df = pd.DataFrame(all_rows)
        # Global Backfill logic
        df['PO'] = df['PO'].replace('', pd.NA).bfill().fillna('')
        return df

    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        return None

# File uploader
uploaded_file = st.file_uploader("Choose a Honda OEM PDF file", type="pdf")

if uploaded_file is not None:
    with st.spinner('Processing your PDF...'):
        df = process_pdf(uploaded_file)
    
    if df is not None:
        st.success("Successfully processed!")
        
        # Display data preview
        st.dataframe(df, use_container_width=True)

        # Download Buttons
        col1, col2 = st.columns(2)
        
        # Excel Export
        buffer_excel = io.BytesIO()
        with pd.ExcelWriter(buffer_excel, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        
        col1.download_button(
            label="📥 Download Excel",
            data=buffer_excel.getvalue(),
            file_name=f"{uploaded_file.name.rsplit('.', 1)[0]}_Converted.xlsx",
            mime="application/vnd.ms-excel"
        )

        # TSV Export
        tsv_data = df.to_csv(index=False, sep='\t').encode('utf-8-sig')
        col2.download_button(
            label="📥 Download TSV (for Google Sheets)",
            data=tsv_data,
            file_name=f"{uploaded_file.name.rsplit('.', 1)[0]}_Converted.tsv",
            mime="text/tab-separated-values"
        )
    else:
        st.warning("No data found in the uploaded PDF.")
