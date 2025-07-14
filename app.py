from flask import Flask, render_template, request, redirect, Response as FlaskResponse
from collections import defaultdict
from wordcloud import WordCloud
from dotenv import load_dotenv
from flask_mail import Mail, Message
from supabase import create_client
import os
import csv

# ✅ Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# ✅ Email Config from .env
app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER")
app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT"))
app.config['MAIL_USE_TLS'] = os.getenv("MAIL_USE_TLS") == 'True'
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_DEFAULT_SENDER")

mail = Mail(app)

# ✅ Supabase config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- HOME PAGE ----------
@app.route("/")
def index():
    return render_template("index.html")

# ---------- FORM SUBMISSION ----------
@app.route("/submit", methods=["POST"])
def submit():
    data = {
        "name": request.form['name'],
        "email": request.form['email'],
        "age": int(request.form['age']),
        "gender": request.form['gender'],
        "dept": request.form['dept'],
        "rating": int(request.form['rating']),
        "likes": request.form.get('likes', ''),
        "suggestions": request.form.get('suggestions', ''),
        "recommend": request.form['recommend']
    }

    # ✅ Insert into Supabase
    supabase.table("responses").insert(data).execute()

    # ✅ Send confirmation email
    try:
        msg = Message(
            subject="Thank you for your feedback!",
            recipients=[data['email']],
            body=f"Hi {data['name']},\n\nThanks for submitting your feedback. We appreciate your input!\n\nRegards,\nTeam"
        )
        mail.send(msg)
    except Exception as e:
        print("⚠️ Email failed to send:", e)

    return redirect("/thankyou?email_sent=true")

   


# ---------- THANK YOU PAGE ----------
@app.route("/thankyou")
def thankyou():
    email_sent = request.args.get("email_sent") == "true"
    return render_template("thankyou.html", email_sent=email_sent)
# ---------- RESULTS PAGE ----------
@app.route("/results")
def results():
    result = supabase.table("responses").select("*").execute()
    responses = result.data if result else []

    total_responses = len(responses)
    average_age = round(sum(r['age'] for r in responses) / total_responses, 2) if responses else 0
    unique_names = list(set(r['name'] for r in responses))

    dept_ratings_map = defaultdict(list)
    gender_count_map = defaultdict(int)
    name_rating_map = defaultdict(list)

    for r in responses:
        dept_ratings_map[r['dept']].append(r['rating'])
        gender_count_map[r['gender']] += 1
        name_rating_map[r['name']].append(r['rating'])

    chart_data = {
        'dept_labels': list(dept_ratings_map.keys()),
        'dept_ratings': [round(sum(ratings)/len(ratings), 2) for ratings in dept_ratings_map.values()],
        'gender_labels': list(gender_count_map.keys()),
        'gender_counts': list(gender_count_map.values()),
        'line_labels': list(name_rating_map.keys()),
        'line_ratings': [round(sum(ratings)/len(ratings), 2) for ratings in name_rating_map.values()]
    }

    combined_text = " ".join([
        (r.get('likes') or "") + " " + (r.get('suggestions') or "")
        for r in responses
    ])
    img_path = None

    if combined_text.strip():
        try:
            os.makedirs("static", exist_ok=True)
            img_path = os.path.join("static", "wordcloud.png")
            if os.path.exists(img_path):
                os.remove(img_path)
            wordcloud = WordCloud(width=800, height=400, background_color='white').generate(combined_text)
            wordcloud.to_file(img_path)
        except Exception as e:
            print("⚠️ Wordcloud generation failed:", e)
            img_path = None

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
            entries = []
            for row in reader:
                entries.append({
                    "name": row['Name'],
                    "email": row['Email'],
                    "age": int(row['Age']),
                    "gender": row['Gender'],
                    "dept": row['Department'],
                    "rating": int(row['Rating']),
                    "likes": row.get('Likes', ''),
                    "suggestions": row.get('Suggestions', ''),
                    "recommend": row['Recommend']
                })
            supabase.table("responses").insert(entries).execute()
            return "✅ CSV uploaded successfully! <a href='/results'>View Results</a>"
        return "⚠️ Invalid file format. Please upload a CSV file."
    return '''
    <h3>📄 Upload CSV</h3>
    <form method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept=".csv" required>
        <input type="submit" value="Upload">
    </form>
    '''

# ---------- DOWNLOAD CSV ----------
@app.route("/download")
def download_csv():
    result = supabase.table("responses").select("*").execute()
    responses = result.data if result else []

    rows = [['Name', 'Email', 'Age', 'Gender', 'Department', 'Rating', 'Likes', 'Suggestions', 'Recommend']]
    for r in responses:
        rows.append([
            r['name'], r['email'], r['age'], r['gender'], r['dept'],
            r['rating'], r.get('likes', ''), r.get('suggestions', ''), r['recommend']
        ])

    def generate():
        for row in rows:
            yield ','.join(map(str, row)) + '\n'

    return FlaskResponse(generate(), mimetype='text/csv',
                         headers={"Content-Disposition": "attachment;filename=survey_responses.csv"})

# ---------- MAIN ----------
if __name__ == "__main__":
    app.run(debug=True)
