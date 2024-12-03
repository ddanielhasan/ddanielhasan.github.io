import pandas as pd
from models import db, Company, Location, Industry, Job, JobSkill, Skill , JobCategory, JobType  # Import models
from sqlalchemy.exc import IntegrityError
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def load_company_data_to_db(excel_path):
    """Preprocess the company data from an Excel file and return the cleaned DataFrame."""
    # Load the data
    data = pd.read_excel(excel_path)

    # Drop unnecessary columns
    data.drop(columns=['pagination', 'web-scraper-order', 'web-scraper-start-url', 'links', 'links-href'], inplace=True)

    # Preprocess num_employee column
    data['num_employee'] = data['num_employee'].apply(lambda x: re.sub(r'\s+', ' ', str(x).strip()))

    def categorize_num_employee(num_employee_text):
        if re.search(r'\b\d{4}\b', num_employee_text):  # Detects a year
            return "Unknown"
        match = re.search(r'(\d+)', num_employee_text)
        if match:
            num_employees = int(match.group(1).replace(",", ""))
            if num_employees >= 1000:
                return "many (1000+)"
            elif 100 <= num_employees < 1000:
                return "normal (100-999)"
            else:
                return "less (<100)"
        return "Unknown"

    data['employee_count'] = data['num_employee'].apply(lambda x: categorize_num_employee(str(x)))

    # Preprocess company_category column
    def split_categories(categories_text):
        """Split categories by newline or comma and strip whitespace."""
        if pd.isna(categories_text):  # Handle NaN values
            return []
        return [category.strip() for category in re.split(r'[\n,]+', str(categories_text)) if category.strip()]

    data['company_category'] = data['company_category'].apply(split_categories)

    # Clean company_overview column
    data['description'] = data['company_overview'].apply(lambda x: re.sub(r'\s+', ' ', str(x).strip()))

    # Prepare columns for final output
    data = data.rename(columns={
        'company_title': 'name',
        'company_logo-src': 'logo_url',
        'company_location': 'location',
        'company_website-href': 'website'
    })

    # Keep company_category column as a list
    final_columns = ['name', 'logo_url', 'location', 'company_category', 'description', 'employee_count', 'website']
    clean_data = data[final_columns]

    """
    Loads preprocessed company data into the database, using industry_id mappings for Industry table.
    :param excel_path: Path to the preprocessed Excel file
    """

    def get_or_create_industry(industry_name):
        """
        Get the industry_id for the given industry_name from the database, creating it if necessary.
        """
        industry = Industry.query.filter_by(industry_name=industry_name).first()
        if industry:
            return industry
        else:
            # Truncate if industry_name is too long
            if len(industry_name) > 100:
                industry_name = industry_name[:100]

            new_industry = Industry(industry_name=industry_name)
            db.session.add(new_industry)
            try:
                db.session.commit()
                return new_industry
            except IntegrityError:  # Handle potential race conditions
                db.session.rollback()
                return Industry.query.filter_by(industry_name=industry_name).first()

    def clean_category(category):
        """
        Cleans the company_category field by ensuring it's a list of strings.
        """
        if not category:
            return []

        if isinstance(category, list):
            # Ensure all items are stripped of whitespace
            return [cat.strip() for cat in category if cat.strip()]
        elif isinstance(category, str):
            # Remove brackets and strip quotes
            category = category.strip("[]").replace("'", "").replace('"', "").strip()
            # Split categories by comma and return as list
            return [cat.strip() for cat in category.split(",") if cat.strip()]
        else:
            # Return empty list for other types
            return []

    try:
        # use the DF from cleaning
        df = clean_data
        df = df.where(pd.notnull(df), None)
        logging.info("Preprocessed Excel file successfully read.")
    except Exception as e:
        logging.error(f"Error reading Excel file: {e}")
        raise

    for _, row in df.iterrows():
        try:
            # Validate company name
            #company_name = row['name']
            #print(company_name)
            #if not company_name or company_name == 'nan' or pd.isna(company_name):
            #    logging.error(f"Invalid company name for row {row.to_dict()}")
            #    continue  # Skip this row

            # Truncate website field if too long
            website = row['website']
            if pd.notna(website) and len(website) > 1024:
                website = website[:1024]

            # Add or update company (check both name and website)
            company = Company.query.filter_by(name=row['name']).first()
            if not company:
                company = Company(
                    name=row['name'],
                    description=row['description'] if pd.notna(row['description']) else None,
                    website=website,
                    logo_url=row['logo_url'] if pd.notna(row['logo_url']) else None,
                )
                db.session.add(company)
                db.session.flush()  # Generate company_id

            # Add or update location
            if pd.notna(row['location']):
                location_parts = row['location'].split(',')
                city = location_parts[0].strip() if len(location_parts) > 0 else None
                state = location_parts[1].strip() if len(location_parts) > 1 else None
                country = location_parts[2].strip() if len(location_parts) > 2 else ""

                location = Location.query.filter_by(city=city, state=state, country=country).first()
                if not location:
                    location = Location(city="Unknown", state="Unknown", country="Unknown")
                    db.session.add(location)
                    db.session.flush()

                if location not in company.locations:
                    company.locations.append(location)

            # Process company categories
            if row['company_category']:
                categories = clean_category(row['company_category'])
                for category in categories:
                    # Get or create the industry
                    industry = get_or_create_industry(category)

                    # Link company and industry
                    if industry not in company.industries:
                        company.industries.append(industry)

        except Exception as e:
            logging.error(f"Error processing row {row.to_dict()}: {e}")
            continue  # Skip problematic rows

    # Commit all changes
    try:
        db.session.commit()
        logging.info("All changes successfully committed to the database.")
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error committing changes: {e}")
        raise

def load_job_data_to_db(file_path):
    """
    Preprocess job data from an Excel file and return the cleaned DataFrame.

    :param file_path: Path to the input Excel file containing job data.
    :return: A pandas DataFrame with the processed job data.
    """
    # Load the Excel file
    data = pd.read_excel(file_path)

    # Combine info1, info2, info3, info4 into a single column
    data['combined_info'] = data[['info1', 'info2', 'info3', 'info4']].fillna('').agg(' '.join, axis=1)

    # Define a function to parse combined_info
    def parse_info(info):
        parsed = {
            'work_type': None,
            'minimum_salary': 'unknown',
            'max_salary': 'unknown',
            'avg_salary': 'unknown',
            'employee_level': 'unknown'
        }

        # Work Type
        if 'Remote' in info:
            parsed['work_type'] = 'Remote'
        elif 'Hybrid' in info:
            parsed['work_type'] = 'Hybrid'
        else:
            parsed['work_type'] = 'Onsite'

        # Salary
        salary_match = re.search(r'(\d+K)-(\d+K)', info)
        if salary_match:
            min_salary = int(salary_match.group(1).replace('K', '')) * 1000
            max_salary = int(salary_match.group(2).replace('K', '')) * 1000
            avg_salary = (min_salary + max_salary) // 2
            parsed['minimum_salary'] = min_salary
            parsed['max_salary'] = max_salary
            parsed['avg_salary'] = avg_salary

        # Employee Level
        levels = ['Entry level', 'Junior', 'Mid level', 'Senior level', 'Expert/Leader']
        for level in levels:
            if level in info:
                parsed['employee_level'] = level
                break

        return parsed

    # Apply the parse_info function to combined_info
    parsed_info = data['combined_info'].apply(parse_info)
    data['work_type'] = parsed_info.apply(lambda x: x['work_type'])
    data['minimum_salary'] = parsed_info.apply(lambda x: x['minimum_salary'])
    data['max_salary'] = parsed_info.apply(lambda x: x['max_salary'])
    data['avg_salary'] = parsed_info.apply(lambda x: x['avg_salary'])
    data['employee_level'] = parsed_info.apply(lambda x: x['employee_level'])

    # Clean the skills column
    def clean_skills(skills):
        if isinstance(skills, str):
            valid_skills = re.findall(
                r'<div class="py-xs px-sm d-inline-block rounded-3 fs-sm text-nowrap border">(.*?)</div>',
                skills
            )
            return valid_skills if valid_skills else None
        return None

    data['skills'] = data['skills'].apply(clean_skills)
    data = data[data['skills'].notnull()]

    # Retain only required columns and clean company_url
    columns_to_keep = [
        'job_summary', 'company_url-href', 'job_title',
        'company_title', 'skills', 'work_type',
        'minimum_salary', 'max_salary', 'avg_salary', 'employee_level'
    ]
    data = data[columns_to_keep]

    data.rename(columns={'company_url-href': 'company_url'}, inplace=True)

    # Clean company_url
    def clean_company_url(url):
        if isinstance(url, str) and url.startswith('http'):
            return url
        return 'unknown'

    data['company_url'] = data['company_url'].apply(clean_company_url)

    # Remove duplicate rows
    clean_data = data.drop_duplicates(subset=['job_title', 'company_title', 'company_url'])

    # Reset index after dropping rows
    clean_data.reset_index(drop=True, inplace=True)

    # Return the processed DataFrame
    #return data


    ######################################################
    def get_or_create_job_type(job_type_name):
        """
        Get or create a JobType entry in the database.
        """
        job_type = JobType.query.filter_by(type_name=job_type_name).first()
        if job_type:
            return job_type
        else:
            new_job_type = JobType(type_name=job_type_name)
            db.session.add(new_job_type)
            try:
                db.session.commit()
                return new_job_type
            except IntegrityError:
                db.session.rollback()
                return JobType.query.filter_by(type_name=job_type_name).first()

    def get_location_id_for_company(company_title, company_url):
        company = Company.query.filter_by(name=company_title, website=company_url).first()
        if company and company.locations:
            return company.locations[0].location_id
        return None

    def get_company_id(company_title, company_url):
        """
        Get the company_id for a given company_title and company_url. Returns None if the company does not exist.
        """
        company = Company.query.filter_by(name=company_title, website=company_url).first()
        #company = Company.query.filter_by(name=company_title).first()
        return company.company_id if company else None

    def clean_salary(value):
        """
        Clean salary data. If the value is not numeric, return None.
        """
        try:
            return float(value)  # Convert to float
        except (ValueError, TypeError):
            return None  # Replace invalid values with None

    try:
        # Load job data from Excel
        job_df = clean_data

        for _, row in job_df.iterrows():
            try:
                # Extract required fields
                job_title = row.get('job_title', None)
                job_description = row.get('job_summary', None)
                company_title = row.get('company_title', None)
                company_url = row.get('company_url', None)
                work_type = row.get('work_type', None)
                minimum_salary = clean_salary(row.get('minimum_salary'))
                max_salary = clean_salary(row.get('max_salary'))

                # Skip if job_title or job_description is missing
                if not job_title or not job_description:
                    continue

                # Get company_id
                company_id = get_company_id(company_title, company_url)
                print (company_id)
                if not company_id:
                    continue  # Skip this job if the company is not in the database

                location_id = get_location_id_for_company(company_title, company_url)
                if not location_id:
                    logging.info(f"No location found for company: {company_title}. Skipping.")
                    continue

                # Check for duplicate job
                duplicate_job = (
                    Job.query.join(Company, Job.company_id == Company.company_id)
                    .filter(
                        Job.title == job_title,
                        Company.website == company_url
                    )
                    .first()
                )
                if duplicate_job:
                    continue  # Skip this job if it already exists

                # Map work_type to job_type
                job_type = None
                if work_type:
                    job_type = get_or_create_job_type(work_type)

                # Add the job
                job = Job(
                    title=job_title,
                    description=job_description,
                    company_id=company_id,
                    job_type_id=job_type.job_type_id if job_type else None,  # Link job_type_id
                    salary_min=minimum_salary,
                    salary_max=max_salary,
                    location_id=location_id
                )
                db.session.add(job)
                db.session.flush()  # Generate job_id

                # Add skills if available
                if row['skills']:
                    skills = eval(row['skills']) if isinstance(row['skills'], str) else row['skills']
                    for skill_name in skills:
                        skill = Skill.query.filter_by(skill_name=skill_name).first()
                        if not skill:
                            skill = Skill(skill_name=skill_name)
                            db.session.add(skill)
                            db.session.flush()

                        # Link job and skill
                        job_skill = JobSkill(job_id=job.job_id, skill_id=skill.skill_id)
                        db.session.add(job_skill)

                logging.info(f"Job added: {job_title}")

            except Exception as inner_e:
                logging.error(f"Error processing row {row.to_dict()}: {inner_e}")
                continue  # Skip problematic rows

        # Commit all changes
        db.session.commit()
        logging.info("Job data successfully loaded into the database.")

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error loading job data: {e}")
