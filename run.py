"""
Flask application entry point.
Creates the Flask app instance and runs the development server.
"""
from app import create_app

# Create Flask application
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
