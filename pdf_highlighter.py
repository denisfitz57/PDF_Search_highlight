import pymupdf  # PyMuPDF
import os
import sys
import glob
from pypdf import PdfWriter
import pandas as pd
import fitz  # PyMuPDF

def highlight_search_results(csv_path, base_folder, output_directory, add_watermarks=False, add_bookmarks=False, custom_pdf_name=None):
    """
    Creates a highlighted PDF from search results
    
    Parameters:
    csv_path: Path to the CSV file with search results
    base_folder: Base folder where PDF files are stored
    output_directory: Directory where to save output file
    add_watermarks: Whether to add filename watermarks to pages
    add_bookmarks: Whether to add bookmarks for each file in the PDF outline
    
    Returns:
    Tuple containing (pdf_path, status_message, pages_count, highlights_count)
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_directory):
        try:
            os.makedirs(output_directory)
            print(f"Created output directory: {output_directory}")
        except Exception as e:
            print(f"Warning: Failed to create output directory {output_directory}: {e}")
            # Fall back to current directory if creation fails
            output_directory = '.'

    # Extract search term from CSV filename
    if custom_pdf_name:
        # Use custom PDF filename
        if not custom_pdf_name.endswith('.pdf'):
            custom_pdf_name += '.pdf'
        output_pdf_path = os.path.join(output_directory, custom_pdf_name)
    else:
        # Use default filename generation (existing logic)
        search_term_filename = os.path.basename(csv_path).replace('search_results_', '').replace('.csv', '')
        if not search_term_filename.startswith('highlighted_'):
            output_pdf_path = os.path.join(output_directory, f"highlighted_{search_term_filename}.pdf")
        else:
            output_pdf_path = os.path.join(output_directory, f"{search_term_filename}.pdf")
    
    # Read search results
    search_results = pd.read_csv(csv_path)
    
    if len(search_results) == 0:
        return None, "No search results found in CSV", 0, 0
    
    # Check if this is a co-occurrence search by looking for specific columns
    is_co_occurrence = 'co_occurring_terms' in search_results.columns
    has_similarity = 'similarity' in search_results.columns
    
    # Create a PDF writer for the output file
    pdf_writer = PdfWriter()
    
    # Keep track of temporary files
    temp_files = []
    processed_count = 0
    highlighted_count = 0
    
    try:
        # Get unique filenames while preserving sort order
        unique_filenames = search_results['filename'].drop_duplicates().tolist()
        
        # Process each file in the sorted order
        for filename in unique_filenames:
            pdf_path = os.path.join(base_folder, filename)
            
            # Check if the file exists
            if not os.path.exists(pdf_path):
                print(f"Warning: File not found: {pdf_path}")
                continue
            
            # Get all highlights for this file
            file_results = search_results[search_results['filename'] == filename]
            
            try:
                # Open the PDF
                doc = pymupdf.open(pdf_path)
                page = doc[0]  # Single-page PDFs
                
                # Apply all highlights for this page
                hits_count = 0
                for _, row in file_results.iterrows():
                    # Create a rectangle from the bounding box coordinates
                    rect = pymupdf.Rect(row['bbx0'], row['bby0'], row['bbx1'], row['bby1'])
                    
                    # Determine highlight color
                    if has_similarity:
                        # Use similarity-based coloring for regular searches
                        similarity = row['similarity']
                        if similarity == 100:  # Exact match - bright yellow
                            highlight_color = (1, 1, 0)  # Yellow
                        elif similarity >= 90:  # Very similar - light orange
                            highlight_color = (1, 0.8, 0.3)
                        elif similarity >= 80:  # Similar - light green
                            highlight_color = (0.6, 1, 0.6)
                        else:  # Less similar - light blue
                            highlight_color = (0.6, 0.8, 1)
                    elif is_co_occurrence:
                        # For co-occurrence searches, use term-based coloring if available
                        if 'search_term' in row:
                            # Get a color based on the term (consistent per term)
                            term = row['search_term']
                            term_hash = hash(term) % 5
                            term_colors = [
                                (1, 1, 0),     # Yellow
                                (1, 0.8, 0.3),  # Orange
                                (0.6, 1, 0.6),  # Green
                                (0.6, 0.8, 1),  # Blue
                                (1, 0.6, 0.6)   # Pink
                            ]
                            highlight_color = term_colors[term_hash]
                        else:
                            # Default highlight color if no term information
                            highlight_color = (1, 1, 0)  # Yellow
                    else:
                        # Default highlight color when no special information
                        highlight_color = (1, 1, 0)  # Yellow
                    
                    # Apply the highlight
                    highlight = page.add_highlight_annot(rect)
                    highlight.set_colors(stroke=highlight_color)
                    highlight.update()
                    
                    hits_count += 1
                
                # Add watermark if required
                if add_watermarks:
                    # Add the filename as a watermark
                    page = add_filename_watermark(
                        page, 
                        pdf_path,  # Pass the current filename
                        opacity=0.2,  # 20% opacity (80% transparent)
                        color=(0, 0, 0.7),  # Dark blue color
                        font_size=36  # Larger text size
                    )
                
                # Create a temporary highlighted PDF
                temp_path = f"_tmp_{filename.replace(' ', '_').replace(',', '').replace('.pdf', '')}.pdf"
                doc.save(temp_path, incremental=False)
                doc.close()
                
                # Track temp files
                temp_files.append(temp_path)
                
                # Add the temporary PDF to our output PDF
                pdf_writer.append(temp_path)
                
                # Add bookmark for the current file if required
                if add_bookmarks:
                    # Create a bookmark for the first page of this file
                    first_page_number = pdf_writer.get_num_pages() - 1  # Current last page
                    bookmark_title = os.path.basename(filename)
                    if bookmark_title.lower().endswith('.pdf'):
                        bookmark_title = bookmark_title[:-4]
                        
                    try:
                        # Try the standard method first
                        pdf_writer.add_outline_item(
                            title=bookmark_title,
                            page_number=first_page_number,
                            parent=None  # Top-level bookmark
                        )
                    except AttributeError:
                        # Fallback for older PyPDF versions
                        try:
                            # For older versions of PyPDF
                            pdf_writer.addBookmark(
                                title=bookmark_title,
                                pagenum=first_page_number
                            )
                        except Exception as e:
                            print(f"Warning: Could not add bookmark for {bookmark_title}: {e}")
                
                processed_count += 1
                highlighted_count += hits_count
                
            except Exception as e:
                print(f"Error processing {pdf_path}: {str(e)}")
        
        # Save the final PDF if we have any pages
        if processed_count > 0:
            pdf_writer.write(output_pdf_path)
            status_message = f"Created PDF with {processed_count} pages and {highlighted_count} highlighted terms"
            
            return output_pdf_path, status_message, processed_count, highlighted_count
        else:
            return None, "No pages were successfully processed. No output PDF created.", 0, 0
            
    finally:
        # Clean up temporary files
        for temp_path in temp_files:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as e:
                    print(f"Failed to remove {temp_path}: {e}")
        
        # Catch any missed temporary files
        for temp_file in glob.glob("_tmp_*.pdf"):
            try:
                os.remove(temp_file)
            except Exception:
                pass

def add_filename_watermark(page, filename, opacity=0.15, color=(0, 0, 0.7), font_size=36):
    """
    Adds a semi-transparent filename watermark to a PDF page
    
    Parameters:
    page: PyMuPDF page object
    filename: String containing the filename to display
    opacity: Float between 0-1 for transparency level (default reduced to 0.15)
    color: RGB tuple (0-1 scale) for text color
    font_size: Size of the font for the watermark
    """
    # Get page dimensions
    rect = page.rect
    
    # Extract just the filename without path and possibly trim extension
    display_name = os.path.basename(filename)
    if display_name.lower().endswith('.pdf'):
        display_name = display_name[:-4]  # Remove .pdf extension
    
    # Move watermark more to the left side of center
    center_x = rect.width * 0.4  # Moved left from 0.5 to 0.4
    center_y = rect.height * 0.5
    
    try:
        # Create a watermark as an annotation - this makes it non-selectable
        # and provides better transparency control
        watermark_rect = fitz.Rect(
            center_x - rect.width * 0.4,  # Expanded left boundary
            center_y - font_size,
            center_x + rect.width * 0.4,  # Expanded right boundary
            center_y + font_size
        )
        
        # Create a text annotation with appropriate properties
        annot = page.add_freetext_annot(
            rect=watermark_rect,
            text=display_name,
            fontsize=font_size,
            fontname="helv-bold",
            text_color=color,
            fill_color=(1, 1, 1, 0),  # Transparent background
            rotate=45  # Rotate text by 45 degrees
        )
        
        # Make the annotation non-printing and set opacity
        annot.set_opacity(opacity)
        annot.update(border_width=0, border_color=None)  # No border
        
        return page
    
    except Exception as e1:
        print(f"Warning: Using fallback watermark method for {display_name}: {e1}")
        try:
            # Fallback 1: Use standard text insertion with reduced opacity
            page.insert_text(
                fitz.Point(center_x, center_y),
                display_name,
                fontsize=font_size,
                fontname="helv-bold",
                color=color,
                rotate=45
            )
            return page
        except Exception as e2:
            print(f"Warning: Using simple watermark method for {display_name}: {e2}")
            try:
                # Fallback 2: Simplest possible approach
                page.insert_text(
                    fitz.Point(center_x, center_y),
                    display_name,
                    fontsize=font_size
                )
                return page
            except Exception as e3:
                print(f"Warning: Could not add watermark to {display_name}: {e3}")
                return page  # Return unmodified page