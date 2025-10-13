# Web Application Exercise

A little exercise to build a web application following an agile development process. See the [instructions](instructions.md) for more detail.

## Product vision statement

A small campus lost & found web app so students can report, browse, search, edit, and remove items from their phones.

## User stories

[Click here to view all user stories](https://github.com/swe-students-fall2025/2-web-app-lgtm/issues?q=is%3Aissue)

## Steps necessary to run the software

- Clone this repository  

- Install the required Python packages  
  - On Windows: `pip install -r requirements.txt`  
  - On macOS: `python3 -m pip install -r requirements.txt`

- Start MongoDB (for example using Docker Desktop or a local MongoDB instance)  
  Ensure MongoDB is running on `localhost:27017` before starting the app.

- Create a copy of the provided `env.example` file and rename it to `.env`.
  Update values if necessary for your local environment.

- Run the Flask app  
  - On Windows: `python app.py`
  - On macOS: `python3 app.py`
  - or `flask run` for both

- Open a browser and go to  
  `http://127.0.0.1:5000`

## Task boards

[lgtm - Sprint 1](https://github.com/orgs/swe-students-fall2025/projects/9)
