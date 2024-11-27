from flask import Flask, render_template, redirect, request, url_for
from flask_login import LoginManager, login_user,logout_user, current_user, login_required
from extensions import db, migrate, bcrypt
from models import Company, Job, Comment, Location, Users, Industry, JobType, JobCategory
from urllib.parse import urlparse



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
    next_page = request.url  # Capture the original URL
    return redirect(url_for('betterLog', next=next_page))

############### APP DB MANAGEMENT ###############
#daniel local connection:
SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@localhost:{port}/{databasename}".format(
    username="root",
    password="12345678",
    port="3306",
    databasename="jobboard2",
)
#
# #Jun local connection:
#
# SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@localhost:{port}/{databasename}".format(
#     username="root",
#     password="Tlsguswns97!",
#     port="3306",
#     databasename="jobboard",
# )
#
# #prodaction connection:
# SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@{hostname}/{databasename}".format(
#     username="ddanielhasan",
#     password="danieljun123!",
#     hostname="ddanielhasan.mysql.pythonanywhere-services.com",
#     databasename="ddanielhasan$comments",
# )


app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_POOL_RECYCLE"] = 299
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)
migrate.init_app(app, db)
bcrypt.init_app(app)
#########################################

############ ROUTES ##############

@app.route('/')
def index():
    return render_template('index2.html')

@app.route('/jobsearch', methods=['GET'])
def jobsearch():
    keywords = request.args.get('keywords', '')
    job_category = request.args.get('job_category', '')
    # Query with filter if keywords are provided
    jobs_query = (
        Job.query
        .join(Company)
        .join(Location, Job.location_id == Location.location_id)
        .join(JobType, Job.job_type_id == JobType.job_type_id)
        .join(JobCategory, Job.category_id == JobCategory.category_id)
        .add_columns(
            Job.job_id,
            Job.title,
            Job.description,
            Job.company_id,
            Company.name.label('company_name'),
            Company.logo_url.label('company_logo'),
            Location.city.label('location_city'),
            Location.state.label('location_state'),
            Location.country.label('location_country'),
            JobType.type_name.label('job_type'),
            JobCategory.category_name.label('job_category')
        )
    )
    if keywords:
        jobs_query = jobs_query.filter(Job.title.ilike(f'%{keywords}%'))
    if job_category:
        jobs_query = jobs_query.filter(JobCategory.category_name.ilike(job_category))

    # Add other filters here as needed, similar to the keywords filter
    categories = JobCategory.query.all()
    jobs = jobs_query.all()
    return render_template('jobsearch.html', jobs=jobs, categories=categories, job_category=job_category)

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


from flask import flash  # Import flash for user feedback


@app.route('/sign_up_page', methods=['GET', 'POST'])
def sign_up_page():
    if request.method == "GET":
        return render_template('sign-up.html')

    elif request.method == "POST":
        # Get form data
        user_name = request.form.get('username')
        passwd = request.form.get('password')
        passwd_validation = request.form.get('password_validation')  # Confirm password field
        email = request.form.get('email')

        # Check if username already exists
        existing_user = Users.query.filter_by(user_name=user_name).first()
        if existing_user:
            flash("Username already exists. Please choose another one.", "error")
            return render_template('sign-up.html')

        # Check if passwords match
        if passwd != passwd_validation:
            flash("Passwords do not match. Please try again.", "error")
            return render_template('sign-up.html')

        # Hash password and add user to database
        hashed_passwd = bcrypt.generate_password_hash(passwd).decode('utf-8')
        user = Users(user_name=user_name, password=hashed_passwd, email=email)

        try:
            db.session.add(user)
            db.session.commit()
            flash("Account created successfully. Please log in.", "success")
            return redirect('/')
        except Exception as e:
            flash("An error occurred while creating your account. Please try again.", "error")
            db.session.rollback()
            return render_template('sign-up.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "GET":
        # Render the login page and pass along the 'next' parameter for GET requests
        next_page = request.args.get('next', '/')
        return render_template('login.html', previous_page=next_page)

    elif request.method == "POST":
        user_name = request.form.get('username')
        passwd = request.form.get('password')

        # Query for user
        user = Users.query.filter(Users.user_name == user_name).first()

        if not user:
            flash('User name not found', 'error')
            return redirect(url_for('login', next=request.form.get('next', '/')))

        # Check password
        if bcrypt.check_password_hash(user.password, passwd):
            login_user(user)

            # Get the 'next' parameter from the form data or default to home
            next_page = request.form.get('next', '/')

            # Ensure 'next_page' is either a safe relative URL or an internal absolute path
            if next_page.startswith('http'):
                next_page = urlparse(next_page).path  # Parse and extract the path
            if not next_page.startswith('/'):
                next_page = '/'  # Default to home for invalid paths

            flash(f"Welcome, {user.user_name}!", "success")
            return redirect(next_page)

        flash('Incorrect password', 'error')
        return redirect(url_for('login', next=request.form.get('next', '/')))


@app.route('/logout')
def logout():
    logout_user()
    return redirect('/')

##DELETE THIS ROUTE!!
@app.route('/betterLog')
def betterLog():
    # Capture the 'next' parameter or default to the home page if not present
    next_page = request.args.get('next') or url_for('index')  # Default to homepage
    return render_template('betterLog.html', previous_page=next_page)

if __name__ == '__main__':
    app.run(debug=True)

