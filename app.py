from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from collections import defaultdict
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import os
import csv
from flask import Response as FlaskResponse

app = Flask(__name__, template_folder="code/templates")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///responses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------- DATABASE MODEL ----------
class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    dept = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    likes = db.Column(db.Text)
    suggestions = db.Column(db.Text)
    recommend = db.Column(db.String(10), nullable=False)

# ---------- HOME PAGE ----------
@app.route("/")
def index():
    return render_template("index.html")

# ---------- FORM SUBMISSION ----------
@app.route("/submit", methods=["POST"])
def submit():
    data = Response(
        name=request.form['name'],
        email=request.form['email'],
        age=int(request.form['age']),
        gender=request.form['gender'],
        dept=request.form['dept'],
        rating=int(request.form['rating']),
        likes=request.form.get('likes', ''),
        suggestions=request.form.get('suggestions', ''),
        recommend=request.form['recommend']
    )
    db.session.add(data)
    db.session.commit()
    return redirect("/thankyou")  # Redirect to thank you page

# ---------- THANK YOU PAGE ----------
@app.route("/thankyou")
def thankyou():
    return render_template("thankyou.html")

# ---------- RESULTS & ANALYSIS ----------
@app.route("/results")
def results():
    responses = Response.query.all()
    total_responses = len(responses)
    average_age = round(sum(r.age for r in responses) / total_responses, 2) if responses else 0
    unique_names = list(set(r.name for r in responses))

    dept_ratings_map = defaultdict(list)
    gender_count_map = defaultdict(int)
    name_rating_map = defaultdict(list)

    for r in responses:
        dept_ratings_map[r.dept].append(r.rating)
        gender_count_map[r.gender] += 1
        name_rating_map[r.name].append(r.rating)

    chart_data = {
        'dept_labels': list(dept_ratings_map.keys()),
        'dept_ratings': [round(sum(ratings)/len(ratings), 2) for ratings in dept_ratings_map.values()],
        'gender_labels': list(gender_count_map.keys()),
        'gender_counts': list(gender_count_map.values()),
        'line_labels': list(name_rating_map.keys()),
        'line_ratings': [round(sum(ratings)/len(ratings), 2) for ratings in name_rating_map.values()]
    }

    # ---------- WORD CLOUD ----------
    combined_text = " ".join([(r.likes or "") + " " + (r.suggestions or "") for r in responses])
    img_path = None
    if combined_text.strip():
        wordcloud = WordCloud(width=800, height=400, background_color='white').generate(combined_text)
        img_path = os.path.join("static", "wordcloud.png")
        wordcloud.to_file(img_path)

    return render_template("results.html",
                           responses=responses,
                           total_responses=total_responses,
                           average_age=average_age,
                           unique_names=unique_names,
                           chart_data=chart_data,
                           wordcloud_path=img_path)

# ---------- UPLOAD CSV ----------
@app.route("/upload", methods=["GET", "POST"])
def upload_csv():
    if request.method == "POST":
        file = request.files['file']
        if file and file.filename.endswith('.csv'):
            stream = file.stream.read().decode("utf-8").splitlines()
            reader = csv.DictReader(stream)
            for row in reader:
                new_entry = Response(
                    name=row['Name'],
                    email=row['Email'],
                    age=int(row['Age']),
                    gender=row['Gender'],
                    dept=row['Department'],
                    rating=int(row['Rating']),
                    likes=row.get('Likes', ''),
                    suggestions=row.get('Suggestions', ''),
                    recommend=row['Recommend']
                )
                db.session.add(new_entry)
            db.session.commit()
            return "✅ CSV uploaded successfully! <a href='/results'>View Results</a>"
        return "⚠️ Invalid file format. Please upload a CSV file."
    return '''
    <h3>📤 Upload CSV</h3>
    <form method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept=".csv" required>
        <input type="submit" value="Upload">
    </form>
    '''

# ---------- DOWNLOAD CSV ----------
@app.route('/download')
def download_csv():
    responses = Response.query.all()
    si = []
    header = ['Name', 'Email', 'Age', 'Gender', 'Department', 'Rating', 'Likes', 'Suggestions', 'Recommend']
    si.append(header)

    for r in responses:
        si.append([
            r.name, r.email, r.age, r.gender, r.dept,
            r.rating, r.likes or '', r.suggestions or '', r.recommend
        ])

    def generate():
        for row in si:
            yield ','.join(map(str, row)) + '\n'

    return FlaskResponse(generate(), mimetype='text/csv',
                         headers={"Content-Disposition": "attachment;filename=survey_responses.csv"})

# ---------- MAIN ----------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
