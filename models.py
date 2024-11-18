from app import db
from flask_login import UserMixin

#still not sure where this goes
#migrate = Migrate(app, db)
########


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(4096))

class Company(db.Model):
    __tablename__ = 'companies'
    company_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.Text)
    website = db.Column(db.String(255))
    logo_url = db.Column(db.String(255))
    jobs = db.relationship('Job', back_populates='company', lazy=True)
    locations = db.relationship('Location',
                                secondary='company_locations',
                                backref=db.backref('companies', lazy=True))
    industries = db.relationship('Industry',
                                 secondary='company_industries',
                                 backref=db.backref('companies', lazy=True))

class Job(db.Model):
    __tablename__ = 'jobs'
    job_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.company_id'), nullable=False)
    company = db.relationship('Company', back_populates='jobs')

class Location(db.Model):
    __tablename__ = 'locations'
    location_id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100), nullable=False)

class Industry(db.Model):
    __tablename__ = 'industries'
    industry_id = db.Column(db.Integer, primary_key=True)
    industry_name = db.Column(db.String(100), nullable=False)

class Users(db.Model, UserMixin):
    __tablename__ = 'users'
    uid = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(80), nullable=False)

    def get_id(self):
        return self.uid


company_locations = db.Table('company_locations',
    db.Column('company_id', db.Integer, db.ForeignKey('companies.company_id'), primary_key=True),
    db.Column('location_id', db.Integer, db.ForeignKey('locations.location_id'), primary_key=True)
)

company_industries = db.Table('company_industries',
    db.Column('company_id', db.Integer, db.ForeignKey('companies.company_id'), primary_key=True),
    db.Column('industry_id', db.Integer, db.ForeignKey('industries.industry_id'), primary_key=True)
)