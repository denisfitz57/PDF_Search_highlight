from flask_wtf import FlaskForm
from wtforms import StringField, FileField, SubmitField
from wtforms.validators import DataRequired

class SearchForm(FlaskForm):
    search_term = StringField('Search Term', validators=[DataRequired()])
    pdf_file = FileField('Upload PDF', validators=[DataRequired()])
    submit = SubmitField('Highlight and Generate PDF')