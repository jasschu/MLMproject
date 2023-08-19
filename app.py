import csv
from datetime import date
from flask import Flask, request, render_template, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from werkzeug.security import check_password_hash

import helpers


# create the app
app = Flask(__name__)
# configure the SQLite database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///income.db"
# initialize the app with the extension
db = SQLAlchemy(app)
# migration for db changes
migrate = Migrate(app, db)

app.secret_key = ""

# DB Tables

# login details for admin users
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    hash = db.Column(db.String(60))

    def __repr__(self):
        return '<User %r>' % self.username


class MLM(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    date_last_modified = db.Column(db.DateTime, nullable=False,
                                   default=datetime.utcnow)
    mlm = db.relationship('MLM_Income_Tier', backref='MLM', lazy=True)

    def __repr__(self):
        return '<MLM %r>' % self.id

#annual income details for each MLM level
class MLM_Income_Tier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.Integer)
    MLM_id = db.Column(db.Integer, db.ForeignKey('mlm.id'), nullable=False)
    median_income = db.Column(db.Float)
    average_income = db.Column(db.Float)
    percentage = db.Column(db.Float)

#link to income statement
class Income_Statement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer)
    link = db.Column(db.String(255), unique=True, nullable=False)
    MLM_id = db.Column(db.Integer, db.ForeignKey('mlm.id'), nullable=False)


@app.route("/")
def index():
    return render_template('index.html')

#sign in to admin portal
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        # ensure username and password were entered
        if not request.form.get("username") or not request.form.get("password"):
            error = 'Please ensure Username and Password have been entered'
            return render_template('admin/login.html', message=error)
        # check username and password against DB
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if not user or check_password_hash(user.hash, password) == False:
            error = 'Invalid Username or Password'
            return render_template('admin/login.html', message=error)
        # Log user in if credentuals are valid
        session["id"] = user.id
        return render_template('admin/login_success.html')

    else:
        message = ('Please Enter admin credentials')
        return render_template('admin/login.html', message=message)


@app.route('/search', methods=["POST"])
def search():
    # search for an MLM
    search_term = request.form.get("name")
    mlms = MLM.query.filter(MLM.name.like('%'+search_term+'%'))
    return render_template('results.html', mlms=mlms)

#load mlm libraries
@app.route('/library', methods=["GET"])
def library():
    mlms= db.session.execute(db.select(MLM).order_by(MLM.name)).scalars()
    return render_template('library.html',mlms=mlms)

# logic for uploading income statements
@app.route("/admin/upload", methods=["GET", "POST"])
@helpers.login_required
def upload_statement():
    if request.method == "POST":
        #return error if form not filled in
        if not helpers.form_filled(request.form):
            error = "Please Fill all fields"
            return render_template('admin/home.html', message=error)
        company = MLM(name=request.form.get('name'))
        #retrun error if MLM already exists
        if MLM.query.filter_by(name=company.name) is None:
            error="MLM already exists in database"
            return render_template('admin/home.html', message=error)
        db.session.add(company)
        db.session.flush()
        #once form data validated, add to DB
        Statement = Income_Statement(year=request.form.get(
            'year'), link=request.form.get('link'), MLM_id=company.id)
        db.session.add(Statement)
        file = request.files['file']
        reader = csv.DictReader(file.read().decode('utf8').splitlines())
        for row in reader:
            income = MLM_Income_Tier(
                level=row['Level'], MLM_id=company.id, median_income=row.get('Median',None), average_income=row.get('Average',None), percentage=row['Percentage'])
            db.session.add(income)
        db.session.commit()
        message = "File upload successful"
        return render_template('admin/home.html', message=message)
    else:
        message = "Enter the name of the mlm, The link to the income disclosure statement and upload the disclosure statement as a csv"
        return render_template('admin/home.html', message=message)

#generate data and visuals for a particular MLM
@app.route('/mlm/<mlm_name>', methods=["GET"])
def lookup_mlm(mlm_name):
    #query DB for MLM and send averages/median data to front end for chart generation.
    mlm = MLM.query.filter_by(name=mlm_name).first()
    statement = Income_Statement.query.filter_by(MLM_id=mlm.id).first()
    levels_data = MLM_Income_Tier.query.filter_by(MLM_id=mlm.id)
    levels = [l.level for l in levels_data]
    medians = [l.median_income for l in levels_data]
    averages = [l.average_income for l in levels_data]
    percentages = [l.percentage for l in levels_data]
    return render_template('mlm_info.html', mlm=mlm, statement=statement, levels=levels, medians=medians, averages=averages, percentages=percentages)
