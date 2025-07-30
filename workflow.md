# 🛠️ Project Workflow: OpenAQ Data Pipeline

This document outlines the standard steps I follow to set up, run, and maintain this data pipeline project.

---

## 📁 Project Structure

> **Note:** The project structure diagram is best viewed in a code editor (like VS Code) or on GitHub, where the formatting and alignment are preserved. Some markdown renderers may not display the tree perfectly.

openaq_pipeline_project/
├── notebooks/
│   └── 00_scratchpad.ipynb
│   └── 01_pull_data.ipynb
│   └── 02_clean_data.ipynb
│   └── 03_eda_pm25.ipynb
│   └── 04_modeling.ipynb
│   └── 05_viz_report.ipynb
├── scripts/
│   └── config.py
├── .env
├── .gitignore
├── requirements.txt
├── README.md
└── workflow.md

## ✅ Project Setup (One-Time)

1. **Create virtual environment**
   ```bash
   python -m venv venv
   ```

2. Activate virtual environment
    ```bash
    .\venv\Scripts\activate
    ```

3. Install core packages
    ```bash
    pip install jupyter python-dotenv requests pandas
    ```

4. Freeze dependencies
    ```bash
    pip freeze > requirements.txt
    ```

5. Create .env file for secrets (e.g. API tokens)
    ```ini
    GITHUB_PAT=your_token_here
    ```

6. Add sensitive files to .gitignore
    ```bash
    .env
    ```

7. Initialize Git and push to GitHub
    ```bash
    git init
    git add .
    git commit -m "Initial commit"
    git branch -M main
    git remote add origin https://github.com/yourusername/repo-name.git
    git push -u origin main
    ```

## 🚀 Daily Workflow
Each time you start working on the project:

1. Activate virtual environment
    ```bash
    .\venv\Scripts\activate
    ```

2. Open notebook
    -  Launch VS Code
    -  Open project folder
    -  Open notebook
    -  Select virtual environment as a kernel (from the dropdown option)

3. Work inside notebooks or scripts. Save frequently. Commit logical chunks of work.

4. Update dependencies if needed
    ```bash
    pip freeze > requirements.txt
    ```

## 🌙 End-of-Day Routine

1. Run and save notebooks

2. Deactivate virtual environment
    ```bash
    deactivate
    ```

3. Commit and push changes
    ```bash
    git add .
    git commit -m "Meaningful commit message"
    git push
    ```

4. Confirm repos are in sync
    ```bash
    git fetch
    git status
    ```

