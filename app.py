import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

# --- Core Logic Function ---
def process_pdf(uploaded_file):
    all_rows = []
    
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                
                # 1. Page Number extraction
                page_num_str = "Unknown"
                page_match = re.search(r'หน้าที่\s*:\s*(\d+)/', text)
                if page_match:
                    page_num_str = page_match.group(1)
                else:
                    page_num_str = str(page.page_number)

                # 2. PO number extraction
                current_page_po = ""
                po_match = re.search(r'PO\d+', text)
                if po_match:
                    current_page_po = po_match.group()

                lines = [l.strip() for l in text.split("\n") if l.strip()]
                for line in lines:
                    # 3. Product row extraction
                    match = re.search(r'^(\d+)\s+([A-Z0-9-]+)\s+(.*?)\s+(\d+)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})$', line)
                    if match:
                        all_rows.append({
                            "Page": page_num_str,
                            "No": int(match.group(1)),
                            "Product Code": match.group(2),
                            "Name": match.group(3).strip(),
                            "Qty": int(match.group(4)),
                            "Price": float(match.group(5).replace(",", "")),
                            "Total": float(match.group(6).replace(",", "")),
                            "PO": current_page_po
                        })
        
        return pd.DataFrame(all_rows)
    except Exception as e:
        st.error(f"Processing failed: {str(e)}")
        return None

# --- Streamlit UI Setup ---
st.set_page_config(page_title="Honda OEM Converter", layout="centered")

st.title("🚗 Honda OEM PDF Converter")
st.write("Upload your PDF to extract Page Numbers and PO data.")

# File Uploader
uploaded_file = st.file_uploader("Choose a Honda OEM PDF file", type="pdf")

if uploaded_file is not None:
    # Process the data
    df = process_pdf(uploaded_file)
    
    if df is not None and not df.empty:
        st.success(f"Success! Found {len(df)} items.")
        
        # Show a preview of the data
        st.dataframe(df, use_container_width=True)
        
        st.divider()
        st.subheader("Download Options")
        
        col1, col2 = st.columns(2)
        
        # 1. Export to Excel
        output_excel = io.BytesIO()
        with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        
        col1.download_button(
            label="📥 Download Excel",
            data=output_excel.getvalue(),
            file_name=f"{uploaded_file.name}_processed.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        # 2. Export to TSV
        tsv = df.to_csv(sep='\t', index=False, encoding='utf-8-sig').encode('utf-8-sig')
        
        col2.download_button(
            label="📥 Download TSV",
            data=tsv,
            file_name=f"{uploaded_file.name}_processed.tsv",
            mime="text/tab-separated-values"
        )
    else:
        st.warning("No products detected in the PDF. Please check the file format.")