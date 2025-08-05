from flask import Blueprint, render_template, request, send_file
from werkzeug.utils import secure_filename
import os
from .utils.pdf_highlighter import search_and_highlight

app_routes = Blueprint('app_routes', __name__)

@app_routes.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        search_term = request.form['search_term']
        base_folder = request.form['base_folder']
        output_dir = 'output'  # Specify output directory for generated PDFs

        # Ensure the output directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Call the search and highlight function
        output_pdf_path = search_and_highlight(search_term, base_folder, output_dir)

        if output_pdf_path:
            return render_template('results.html', pdf_path=output_pdf_path)

    return render_template('index.html')

@app_routes.route('/download/<path:pdf_filename>')
def download(pdf_filename):
    pdf_path = os.path.join('output', pdf_filename)
    return send_file(pdf_path, as_attachment=True)