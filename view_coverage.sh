coverage run --source=. --branch -m unittest discover
coverage html
python3 -c "import webbrowser; webbrowser.open('htmlcov/index.html')"
