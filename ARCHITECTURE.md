# Architecture

## Tech Stack
- **Frontend/Backend:** Python/Flask (as indicated by app.py)
- **Machine Learning:** Scikit-learn, XGBoost (models.py)
- **Testing:** Pytest

## Main Modules
- `app.py`: Entry point for the application.
- `models.py`: Data structures and database models.
- `utils/`: Helper functions and core logic modules (e.g., budget, crypto, tax, etc.).
- `tests/`: Unit and integration tests.

## Data Flow
1. User interacts with the UI/API (app.py).
2. Requests are processed by business logic in `utils/`.
3. Database queries/updates are handled by `models.py`.
4. ML models are loaded and predict based on input data.
