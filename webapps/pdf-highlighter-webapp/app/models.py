from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class SearchResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    search_term = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    page_number = db.Column(db.Integer, nullable=False)
    bounding_box = db.Column(db.String(255), nullable=False)  # Store bounding box as a string

    def __repr__(self):
        return f'<SearchResult {self.search_term} in {self.filename}>'