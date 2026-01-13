import streamlit as st
import pdfplumber
import pandas as pd
import re
import io
import streamlit.components.v1 as components

st.set_page_config(page_title="Honda OEM PDF Converter", layout="wide")

st.title("🚗 Honda OEM PDF Converter")
st.markdown("Upload a PDF, then click **Copy for Google Sheets** to instantly paste your data into your spreadsheet.")

def process_pdf(file):
    all_rows = []
    try:
        with pdfplumber.open(file) as pdf:
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
                page_has_products = False

                for line in lines:
                    # 3. Product row extraction
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
                
                # 4. Keep PO only rows
                if current_page_po and not page_has_products:
                    all_rows.append({
                        "Page": page_num_str, "No": None, "Product Code": "PO LOCATION",
                        "Part Name": "Found PO at bottom", "Qty": 0, "Price": 0, "Total": 0,
                        "PO": current_page_po
                    })

        if not all_rows: return None
        df = pd.DataFrame(all_rows)
        df['PO'] = df['PO'].replace('', pd.NA).bfill().fillna('')
        return df

    except Exception as e:
        st.error(f"Error: {e}")
        return None

uploaded_file = st.file_uploader("Choose a Honda OEM PDF file", type="pdf")

if uploaded_file is not None:
    df = process_pdf(uploaded_file)
    
    if df is not None:
        st.success("Data Processed!")
        
        # --- COPY TO CLIPBOARD SECTION ---
        # Convert dataframe to TSV string (Best for Google Sheets)
        tsv_text = df.to_csv(index=False, sep='\t')
        
        # Custom Javascript for the Copy Button
        copy_button_html = f"""
        <div style="margin-bottom: 20px;">
            <button id="copy-btn" style="
                background-color: #4CAF50;
                color: white;
                padding: 10px 24px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-weight: bold;
                font-size: 16px;
                width: 100%;">
                📋 Click to Copy All for Google Sheets
            </button>
        </div>
        <textarea id="data-area" style="display:none;">{tsv_text}</textarea>
        <script>
            document.getElementById('copy-btn').onclick = function() {{
                var copyText = document.getElementById('data-area');
                copyText.style.display = 'block';
                copyText.select();
                document.execCommand('copy');
                copyText.style.display = 'none';
                this.innerHTML = '✅ Copied! Now paste into Google Sheets (Ctrl+Shift+V)';
                this.style.backgroundColor = '#217346';
            }}
        </script>
        """
        components.html(copy_button_html, height=70)
        
        # Display the data
        st.dataframe(df, use_container_width=True)
        
        # Original download buttons for safety
        col1, col2 = st.columns(2)
        buffer_excel = io.BytesIO()
        with pd.ExcelWriter(buffer_excel, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        col1.download_button("📥 Download Excel File", buffer_excel.getvalue(), "converted.xlsx")
        col2.download_button("📥 Download TSV File", tsv_text.encode('utf-8-sig'), "converted.tsv")

