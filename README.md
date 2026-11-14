# Outdoor Movie Night

A mobile-first Django registration site for a campus screening. Students reserve one seat for ₹500 by submitting their name, registration number, and phone number. No online payment is collected. On-site payments are ₹600 per person.

## Local development

1. Create and activate a virtual environment, then install `requirements.txt`.
2. Copy `.env.example` to `.env` and set a long `SECRET_KEY`.
3. Run `python manage.py migrate` and `python manage.py runserver`.

The registration page creates a reservation immediately. Staff can search, export, or remove registrations at `/crew-console-7x4q/`. The featured movie title and poster can be edited there as well.

## Deployment

The Render blueprint provisions the Django web service and Postgres database. It runs migrations and creates the shared database cache table before deployment. Render generates `SECRET_KEY`; set explicit `ALLOWED_HOSTS`, HTTPS `CSRF_TRUSTED_ORIGINS`, and poster storage credentials in the service environment. Use a unique 50-character-or-longer secret and keep database and image-storage credentials private. Run `python manage.py check --deploy` with the production settings before release.

Event date, venue, gates, screening time, and contact email are configured in `config/settings/base.py` under `EVENT`. Student registration numbers must be exactly 10 alphanumeric characters and are unique at the database level.

