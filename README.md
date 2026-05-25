# LiquidSuite
LiquidSuite is a financial management application designed to help users track their expenses and transactions. It integrates with Gmail to import statements and ERPNext to sync financial data.
## Key Features
* Import statements from Gmail
* Categorize transactions using machine learning algorithms
* Sync financial data with ERPNext
* User authentication and authorization
* REST API for integrating with other applications
## Tech Stack
* Flask as the web framework
* PostgreSQL as the database
* Redis as the message broker
* Celery as the task queue
* ERPNext as the accounting system
## Installation
To install LiquidSuite, follow these steps:
1. Clone the repository: `git clone https://github.com/your-username/LiquidSuite.git`
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Create a PostgreSQL database and update the `DATABASE_URL` environment variable
6. Run the application: `flask run`
## Usage
To use LiquidSuite, follow these steps:
1. Create a user account and authenticate with Google
2. Import statements from Gmail
3. Categorize transactions using the machine learning algorithm
4. Sync financial data with ERPNext
## Required Environment Variables
The following environment variables are required to run LiquidSuite:
* `SECRET_KEY`: a secret key for encrypting session data
* `DATABASE_URL`: the URL of the PostgreSQL database
* `GOOGLE_CLIENT_ID`: the client ID for Google authentication
* `GOOGLE_CLIENT_SECRET`: the client secret for Google authentication
* `ERPNEXT_BASE_URL`: the base URL of the ERPNext instance
* `ERPNEXT_API_KEY`: the API key for ERPNext
* `ERPNEXT_API_SECRET`: the API secret for ERPNext