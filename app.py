"""Development entry point.

    flask --app app run          (or)   python app.py

Configure with environment variables — see .env.example.
"""
import os

from blog_api import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
