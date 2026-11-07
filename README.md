# Outdoor Movie Night

A mobile-first Django registration site for a campus screening. Students submit their name, registration number, phone and student ID photo, then pay ₹500 online or reserve and pay ₹600 at the venue. The signup page uses the supplied outdoor cinema photo with a frosted glass panel inspired by the design reference.

## Stack

- Python 3.12, Django 5.x, PostgreSQL in production and SQLite locally
- Django templates, HTMX, and Tailwind CSS 3
- PhonePe Standard Checkout (server initiation, callback checksum, server status confirmation)
- Pillow-validated ID photos stored in Cloudinary or S3-compatible storage
- WhiteNoise and Gunicorn, configured for Render
- pytest-django

## Local setup

1. Create a virtual environment with Python 3.12 and activate it.
2. Install dependencies: `pip install -r requirements-dev.txt`.
3. Copy `.env.example` to `.env`. The defaults use SQLite, local media, and the mock checkout. Keep `.env` out of version control.
4. Install Node dependencies and build CSS: `npm install && npm run css`.
5. Run `python manage.py migrate` and create staff login with `python manage.py createsuperuser`.
6. Start the site with `python manage.py runserver`.

The student flow is at `/`. The custom staff dashboard is at `/manage/`; use its **Edit featured movie** link or open `/manage/movie/` to publish a movie title and poster. Django admin is at `/admin/`, where the featured-movie record is also available. Staff accounts use Argon2 for new passwords.

## PhonePe sandbox

The default local mode (`PHONEPE_MOCK=True`) provides a simulated checkout that never charges a card or UPI account. To exercise real PhonePe sandbox checkout, use merchant credentials from PhonePe and set `PHONEPE_MOCK=False`, `PHONEPE_MERCHANT_ID`, `PHONEPE_SALT_KEY`, and `PHONEPE_SALT_INDEX` in `.env`. Set the base URL to the PhonePe sandbox endpoint, and configure the redirect and callback URLs to a publicly reachable HTTPS development tunnel. Register the callback URL with PhonePe when required by your merchant account.

The callback is CSRF-exempt because it is server-to-server; it must carry a valid `X-VERIFY`. The application then checks transaction status directly with PhonePe and validates merchant ID, merchant transaction ID, and the expected ₹500 (50000 paise) amount before marking a registration paid. The browser return page only reads registration state. Do not use the local mock mode in production.

## ID image storage

Development can store re-encoded JPEGs under `media/`. For production, set `CLOUDINARY_URL` or the S3-compatible `AWS_*` values in the environment. Student ID-card photos and movie posters are checked for format, byte size, and dimensions, decoded, and re-encoded as JPEG before storage. Render disks are ephemeral; configure remote storage before accepting registrations or publishing a movie poster in production.

## Render deployment

1. Push this project to a GitHub repository.
2. In Render, create a Blueprint from the repository and apply `render.yaml`; it provisions a web service and managed Postgres database.
3. Add `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` for the deployed domain, PhonePe merchant credentials and callback URLs, and `CLOUDINARY_URL` or bucket credentials in the web service environment.
4. Confirm production `PHONEPE_MOCK=False` and configure PhonePe's callback to `https://<your-domain>/payments/callback/`.
5. Deploy. Render installs Python and Node dependencies, builds the Tailwind stylesheet, collects static files, and runs migrations in the pre-deploy command. The sample Blueprint uses paid service and database plans so pre-deploy migrations are supported and the database does not expire after 30 days.
6. Create a staff superuser through a Render shell: `python manage.py createsuperuser`.

Production settings enforce HTTPS, secure HttpOnly cookies, HSTS, and environment-provided secrets. PostgreSQL is selected from `DATABASE_URL`.

## Tests

Run the project suite with `pytest`. It covers reserve/pay flows and callback verification, including checksum rejection, API amount validation, and duplicate callback handling.

## Important configuration

Event date, venue, gates, screening time, and contact email are in `config/settings/base.py` under `EVENT`; update both `when` and `date` before launch. The `date` value controls when staff payment confirmation closes. Amounts are configured there as ₹500 online and ₹600 reserved (₹100 surcharge). Student registration numbers must be exactly 10 alphanumeric characters and are unique at the database level. Failed payment attempts are discarded and the registration stays pending for retry. Staff can confirm pending ₹500 payments or reserved ₹600 payments before the event date.




