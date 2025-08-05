import os
import pandas as pd
import pymupdf  # PyMuPDF
from pypdf import PdfWriter
import uuid

class PDFHighlighter:
    def __init__(self, app_config):
        """Initialize with application configuration"""
        self.data_dir = app_config.DATA_DIR
        self.pdf_dir = app_config.PDF_DIR
        self.output_dir = app_config.OUTPUT_DIR
        self.text_position_csv = os.path.join(self.data_dir, 'text_with_position.csv')
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Load text position data at initialization
        self._load_text_position_data()
    
    def _load_text_position_data(self):
        """Load text position data from CSV"""
        try:
            self.text_position_df = pd.read_csv(self.text_position_csv)
            self.data_loaded = True
        except FileNotFoundError:
            self.data_loaded = False
            self.error_message = f"Error: Text position data not found at {self.text_position_csv}"
    
    def search_and_highlight(self, search_term):
        """
        Search for term and create highlighted PDF from server-stored PDFs
        
        Parameters:
        search_term (str): Term to search for
        
        Returns:
        tuple: (pdf_path, message) - Path to the generated PDF and status message
        """
        if not self.data_loaded:
            return None, self.error_message
        
        # Generate unique ID for this search to avoid filename collisions
        search_id = str(uuid.uuid4())[:8]
        output_filename = f"highlighted_{search_term.replace(' ', '_')}_{search_id}.pdf"
        output_pdf_path = os.path.join(self.output_dir, output_filename)
        
        # Search for the term
        search_results = self.text_position_df[
            self.text_position_df['text'].str.contains(search_term, case=False, na=False)
        ]
        
        if len(search_results) == 0:
            return None, f"No results found for '{search_term}'"
        
        # Create PDF with highlights
        pdf_writer = PdfWriter()
        processed_files = set()
        search_results = search_results.sort_values(by=['date', 'page_number'])
        
        for index, row in search_results.iterrows():
            pdf_path = os.path.join(self.pdf_dir, row['filename'])
            
            if not os.path.exists(pdf_path):
                continue
            
            file_id = (pdf_path, 0)  # Assuming single-page PDFs
            
            if file_id in processed_files:
                continue
            
            try:
                doc = pymupdf.open(pdf_path)
                page = doc[0]  # Single-page PDFs
                rect = pymupdf.Rect(row['bbx0'], row['bby0'], row['bbx1'], row['bby1'])
                highlight = page.add_highlight_annot(rect)
                
                temp_path = os.path.join(self.output_dir, f"_tmp_{search_id}_{index}.pdf")
                doc.save(temp_path, incremental=False)
                doc.close()
                
                pdf_writer.append(temp_path)
                processed_files.add(file_id)
            except Exception as e:
                continue
        
        if len(processed_files) == 0:
            return None, "Could not process any PDFs for highlighting"
        
        pdf_writer.write(output_pdf_path)
        
        # Clean up temporary files
        for index in range(len(search_results)):
            temp_path = os.path.join(self.output_dir, f"_tmp_{search_id}_{index}.pdf")
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        # Return the relative path for URL generation
        relative_path = os.path.relpath(output_pdf_path, start=self.output_dir)
        return relative_path, f"Created PDF with {len(processed_files)} highlighted pages."
    
    def get_available_docs(self):
        """Get list of available documents on the server"""
        if not self.data_loaded:
            return []
        
        # Get unique documents from the dataset
        unique_docs = self.text_position_df['filename'].unique()
        return sorted(unique_docs)