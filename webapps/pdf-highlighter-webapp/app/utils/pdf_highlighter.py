import os
import pandas as pd
import pymupdf  # PyMuPDF
from pypdf import PdfWriter

def search_and_highlight(search_term, base_folder, output_directory='.'):
    try:
        df = pd.read_csv('text_with_position.csv')
    except FileNotFoundError:
        return None, "Error: text_with_position.csv not found"
    
    search_results = df[df['text'].str.contains(search_term, case=False, na=False)]
    
    if len(search_results) == 0:
        return None, f"No results found for '{search_term}'"
    
    output_pdf_path = os.path.join(output_directory, f"highlighted_{search_term.replace(' ', '_')}.pdf")
    pdf_writer = PdfWriter()
    processed_files = set()
    search_results = search_results.sort_values(by=['date', 'page_number'])
    
    for index, row in search_results.iterrows():
        pdf_path = os.path.join(base_folder, row['filename'])
        
        if not os.path.exists(pdf_path):
            continue
        
        file_id = (pdf_path, 0)
        
        if file_id in processed_files:
            continue
        
        try:
            doc = pymupdf.open(pdf_path)
            page = doc[0]
            rect = pymupdf.Rect(row['bbx0'], row['bby0'], row['bbx1'], row['bby1'])
            highlight = page.add_highlight_annot(rect)
            temp_path = f"_tmp_{index}.pdf"
            doc.save(temp_path, incremental=False)
            doc.close()
            pdf_writer.append(temp_path)
            processed_files.add(file_id)
        except Exception as e:
            continue
    
    pdf_writer.write(output_pdf_path)
    
    for index in range(len(search_results)):
        temp_path = f"_tmp_{index}.pdf"
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    return output_pdf_path, f"Created PDF with {len(processed_files)} highlighted pages."