from flask import Flask, render_template, url_for, request, redirect
import json
import os
import requests

app = Flask(__name__)

def load_users():
    if os.path.exists("users.json"):
        with open("users.json", "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

def load_books():
    with open("lib.json", "r") as f:
        return json.load(f)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        users = load_users()
        if username in users:
            return redirect(url_for('dashboard', username=username))
        else:
            return render_template('login.html', error="Username not found.")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        if not username:
            return render_template('signup.html', error="Username cannot be empty.")
        users = load_users()
        if username in users:
            return render_template('signup.html', error="Username already exists.")
        # Create new user with defaults
        users[username] = {
            "level": 1,
            "books": [],
            "balance": 100
        }
        save_users(users)
        return redirect(url_for('dashboard', username=username))

    return render_template('signup.html')

@app.route('/dashboard/<username>')
def dashboard(username):
    users = load_users()
    user_data = users.get(username)
    lib_books = load_books()
    if user_data:
        return render_template('dashboard.html', username=username, data=user_data, books=lib_books)
    return "User not found", 404

@app.route('/browser/<username>')
def browse(username):
    books = load_books()
    users = load_users()
    user_data = users.get(username)
    return render_template("browser.html", username=username, bdata=books, data=user_data)

@app.route('/checkout/<username>', methods=['POST'])
def checkout(username):
    title = request.form['book_title']

    # Load books and users
    with open("lib.json", "r") as f:
        books = json.load(f)

    with open("users.json", "r") as f:
        users = json.load(f)

    # Safety: make sure user exists
    if username not in users:
        return "User not found", 404

    # Prevent duplicate checkout
    if title in users[username]["books"]:
        return redirect(url_for('browse', username=username))  # already has book

    # Proceed if copies are available
    if books[title]["copiesav"] > 0:
        books[title]["copiesav"] -= 1
        users[username]["books"].append(title)

        # Save updated files
        with open("lib.json", "w") as f:
            json.dump(books, f, indent=4)

        with open("users.json", "w") as f:
            json.dump(users, f, indent=4)

    return redirect(url_for('browse', username=username))

@app.route('/admin/<username>')
def admin(username):
    users = load_users()
    books = load_books()

    user_data = users.get(username)
    if not user_data:
        return "User not found", 404

    # Check if user is an admin
    if user_data.get("level", 1) < 2:
        return "Access denied", 403

    return render_template("admin.html", username=username, users=users, books=books)

@app.route('/admin/<username>/add', methods=['POST'])
def add_book(username):
    users = load_users()
    if users[username]["level"] < 2:
        return "Access denied", 403

    title = request.form['title']
    author = request.form['author']
    series = request.form['series']
    totalcopies = int(request.form['totalcopies'])

    with open("lib.json", "r") as f:
        books = json.load(f)

    if title in books:
        return "Book already exists", 400

    books[title] = {
        "author": author,
        "series": series,
        "totalcopies": totalcopies,
        "copiesav": totalcopies
    }

    with open("lib.json", "w") as f:
        json.dump(books, f, indent=4)

    return redirect(url_for('admin', username=username))

@app.route('/admin/<username>/edit', methods=['POST'])
def edit_book(username):
    users = load_users()
    if users[username]["level"] < 2:
        return "Access denied", 403

    old_title = request.form['old_title']
    new_title = request.form['title']
    author = request.form['author']
    series = request.form['series']
    totalcopies = int(request.form['totalcopies'])
    copiesav = int(request.form['copiesav'])

    with open("lib.json", "r") as f:
        books = json.load(f)

    # Delete old title if renamed
    if old_title != new_title:
        books.pop(old_title)

    books[new_title] = {
        "author": author,
        "series": series,
        "totalcopies": totalcopies,
        "copiesav": copiesav
    }

    with open("lib.json", "w") as f:
        json.dump(books, f, indent=4)

    return redirect(url_for('admin', username=username))

@app.route('/admin/<username>/delete', methods=['POST'])
def delete_book(username):
    users = load_users()
    if users[username]["level"] < 2:
        return "Access denied", 403

    title = request.form['title']

    with open("lib.json", "r") as f:
        books = json.load(f)

    books.pop(title, None)

    with open("lib.json", "w") as f:
        json.dump(books, f, indent=4)

    return redirect(url_for('admin', username=username))

@app.route('/update-data', methods=['POST'])
def update_data():
    username = request.form.get('username')
    book = request.form.get('book')

    if not username or not book:
        return "Missing data", 400

    users = load_users()
    books = load_books()

    # Safety checks
    if username not in users:
        return "User not found", 404
    if book not in books:
        return "Book not found", 404
    if book not in users[username]['books']:
        return "Book not checked out by user", 400

    # Remove book from user
    users[username]['books'].remove(book)
    # Increase available copies
    books[book]['copiesav'] += 1

    # Save changes
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)
    with open("lib.json", "w") as f:
        json.dump(books, f, indent=4)


    return redirect(url_for('dashboard', username=username))

@app.route("/update")
def updatewebsite():
    url = "https://raw.githubusercontent.com/hiltslash/wwlibrary/main/app.py"

    # Make a GET request to download the file
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code == 200:
        with open("app.py", "w", encoding="utf-8") as file:
            file.write(response.text)
        print("Downloaded and saved as app.py")
    else:
        print(f"Failed to download file. Status code: {response.status_code}")
    return "success."
    redirect("/")


if __name__ == '__main__':
   app.run(debug=True, port=5001, host='0.0.0.0')
