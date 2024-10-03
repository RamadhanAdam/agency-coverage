# Agency Analysis Dashboard

## Overview
This is a Dash-based web application to analyze sub-agency data and provide visualization of coverage for various agencies based on license plate data.

## Features
- Search by License Plate
- Select Agencies for analysis
- Upload License Plate coverage files
- Visualize state-wise coverage using interactive heatmaps

## Directory Structure
- `src`: Contains the main application code.
- `assets`: Used for storing CSS or JavaScript files.
- `components`: Contains reusable components (e.g., custom dropdowns or charts).
- `containers`: Contains layout definitions for different sections of the application.
- `data`: Stores the initial data files needed for the app.

## Setup Instructions
1. Install the necessary dependencies using the following command:
    ```bash
    pip install -r requirements.txt
    ```

2. Run the application using the command:
    ```bash
    python src/app.py
    ```

## Deployment
The app can be deployed using various platforms like Heroku, Render, or directly on a server using `waitress` or `gunicorn`.
