import pandas as pd
from models import db, Company, Location, Industry  # Import models
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def load_excel_data_to_db(excel_path):
    """
    Loads Excel data into the database, updating Company, Location, and Industry tables.
    :param excel_path: Path to the Excel file
    """
    try:
        # Read Excel file
        df = pd.read_excel(excel_path)
        logging.info("Excel file successfully read.")
    except Exception as e:
        logging.error(f"Error reading Excel file: {e}")
        raise

    for _, row in df.iterrows():
        try:
            # Truncate website field if too long
            website = row['website']
            if pd.notna(website) and len(website) > 1024:
                website = website[:1024]

            # Add or update company
            company = Company.query.filter_by(name=row['name']).first()
            if not company:
                company = Company(
                    name=row['name'],
                    description=row['description'] if pd.notna(row['description']) else None,
                    website=website,
                    logo_url=row['logo_url'] if pd.notna(row['logo_url']) else None,
                )
                db.session.add(company)
                db.session.flush()  # Flush to generate company_id
            logging.info(f"Processed company: {company.name}")

            # Add or update location
            if pd.notna(row['location']):
                location_parts = row['location'].split(',')
                city = location_parts[0].strip() if len(location_parts) > 0 else None
                state = location_parts[1].strip() if len(location_parts) > 1 else None
                country = location_parts[2].strip() if len(location_parts) > 2 else ""

                location = Location.query.filter_by(city=city, state=state, country=country).first()
                if not location:
                    location = Location(city=city, state=state, country=country)
                    db.session.add(location)
                    db.session.flush()

                if location not in company.locations:
                    company.locations.append(location)
            logging.info(f"Processed location: {city}, {state}, {country}")

            # Add or update industry
            if pd.notna(row['industry_name']):
                industry = Industry.query.filter_by(industry_name=row['industry_name']).first()
                if not industry:
                    industry = Industry(industry_name=row['industry_name'])
                    db.session.add(industry)
                    db.session.flush()

                if industry not in company.industries:
                    company.industries.append(industry)
            logging.info(f"Processed industry: {row['industry_name']}")

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
