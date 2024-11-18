from flask import Flask, render_template, redirect, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user,logout_user, current_user, login_required
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from models import Company, Job, Comment, Location, Users, Industry

app = Flask(__name__, template_folder='templates')

#neta, user management
app.secret_key = "super secret key"
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def user_loader(uid):
    return Users.query.get(uid)
@login_manager.unauthorized_handler
def unauthorized_call():
    if current_user.is_authenticated:
        return redirect('/tease_neta')
    return redirect('/betterLog')


bcrypt = Bcrypt(app)
##################################




############### APP DB MANAGEMENT ###############
#daniel local connection:
SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@localhost:{port}/{databasename}".format(
    username="root",
    password="12345678",
    port="3306",
    databasename="jobboard2",
)
# '''
# #Jun local connection:
#
# SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@localhost:{port}/{databasename}".format(
#     username="root",
#     password="Tlsguswns97!",
#     port="3306",
#     databasename="jobboard",
# )
# '''
# #prodaction connection:
# SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@{hostname}/{databasename}".format(
#     username="ddanielhasan",
#     password="danieljun123!",
#     hostname="ddanielhasan.mysql.pythonanywhere-services.com",
#     databasename="ddanielhasan$comments",
# )
'''
'''

app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_POOL_RECYCLE"] = 299
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

migrate = Migrate(app, db)
#########################################

############### DB MODELS ###############
# class Comment(db.Model):
#     __tablename__ = "comments"
#     id = db.Column(db.Integer, primary_key=True)
#     content = db.Column(db.String(4096))
#
# class Company(db.Model):
#     __tablename__ = 'companies'
#     company_id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String, nullable=False)
#     description = db.Column(db.Text)
#     website = db.Column(db.String(255))
#     logo_url = db.Column(db.String(255))
#     jobs = db.relationship('Job', back_populates='company', lazy=True)
#     locations = db.relationship('Location',
#                                 secondary='company_locations',
#                                 backref=db.backref('companies', lazy=True))
#     industries = db.relationship('Industry',
#                                  secondary='company_industries',
#                                  backref=db.backref('companies', lazy=True))
#
# class Job(db.Model):
#     __tablename__ = 'jobs'
#     job_id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String, nullable=False)
#     description = db.Column(db.String, nullable=False)
#     company_id = db.Column(db.Integer, db.ForeignKey('companies.company_id'), nullable=False)
#     company = db.relationship('Company', back_populates='jobs')
#
# class Location(db.Model):
#     __tablename__ = 'locations'
#     location_id = db.Column(db.Integer, primary_key=True)
#     city = db.Column(db.String(100))
#     state = db.Column(db.String(100))
#     country = db.Column(db.String(100), nullable=False)
#
# class Industry(db.Model):
#     __tablename__ = 'industries'
#     industry_id = db.Column(db.Integer, primary_key=True)
#     industry_name = db.Column(db.String(100), nullable=False)
#
# class Users(db.Model, UserMixin):
#     __tablename__ = 'users'
#     uid = db.Column(db.Integer, primary_key=True)
#     user_name = db.Column(db.String(80), nullable=False, unique=True)
#     password = db.Column(db.String(80), nullable=False)
#     email = db.Column(db.String(80), nullable=False)
#
#     def get_id(self):
#         return self.uid
#
#
# company_locations = db.Table('company_locations',
#     db.Column('company_id', db.Integer, db.ForeignKey('companies.company_id'), primary_key=True),
#     db.Column('location_id', db.Integer, db.ForeignKey('locations.location_id'), primary_key=True)
# )
#
# company_industries = db.Table('company_industries',
#     db.Column('company_id', db.Integer, db.ForeignKey('companies.company_id'), primary_key=True),
#     db.Column('industry_id', db.Integer, db.ForeignKey('industries.industry_id'), primary_key=True)
# )

###########################################################################
@app.route('/')
def index():
    return render_template('index2.html')

@app.route('/jobsearch', methods=['GET'])
def jobsearch():
    keywords = request.args.get('keywords', '')
    # Query with filter if keywords are provided
    jobs_query = Job.query.join(Company).add_columns(Job.job_id, Job.title, Job.description,Job.company_id, Company.name.label('company_name'))
    if keywords:
        jobs_query = jobs_query.filter(Job.title.ilike(f'%{keywords}%'))

    # Add other filters here as needed, similar to the keywords filter
    jobs = jobs_query.all()
    return render_template('jobsearch.html', jobs=jobs)

@app.route('/companies')
def companies():
    companies = Company.query.all()
    return render_template('companies.html', companies=companies)
@app.route('/company/<int:company_id>')
def company_detail(company_id):
    company = Company.query.get_or_404(company_id)
    # No need for extra queries since we have relationships defined
    return render_template('company_detail.html',
                         company=company,
                         jobs=company.jobs,
                         locations=company.locations,
                         industries=company.industries)

@app.route("/comments_page", methods=["GET", "POST"])
@login_required
def comments_page():
    if request.method == "GET":
        return render_template("comments_page.html", comments=Comment.query.all())

    comment = Comment(content=request.form["contents"])
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('comments_page'))

@app.route('/tease_neta')
@login_required
def tease_neta():
    return render_template('tease_neta.html', current_user=current_user)


@app.route('/sign_up_page', methods=['GET','POST'])
def sign_up_page():
    if request.method == "GET":
        return render_template('sign-up.html')
    elif request.method == "POST":
        user_name = request.form.get('username')
        passwd = request.form.get('password')
        email = request.form.get('email')

        #hash password
        hashed_passwd = bcrypt.generate_password_hash(passwd)

        #add to db
        user = Users(user_name=user_name, password=hashed_passwd, email=email)

        db.session.add(user)
        db.session.commit()

        return redirect('/',current_user=current_user.user_name)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == "GET":
        return render_template('login.html')
    elif request.method == "POST":
        user_name = request.form.get('username')
        passwd = request.form.get('password')

        #query for user
        user = Users.query.filter(Users.user_name == user_name).first()

        #check password
        if bcrypt.check_password_hash(user.password, passwd):
            login_user(user)

            # Get the 'next' parameter from the URL (where the user was trying to go)
            next_page = request.args.get('next')

            # Redirect the user to the next page or to the default page ('/test')
            return redirect('/')
        else:
            return redirect('/betterLog')

@app.route('/logout')
def logout():
    logout_user()
    return redirect('/')

##DELETE THIS ROUTE!!
@app.route('/betterLog')
def betterLog():
    return render_template('betterLog.html',previous_page=request.referrer)


if __name__ == '__main__':
    app.run(debug=True)

