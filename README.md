# Capstone DCP



## Getting started

To make it easy for you to get started with GitLab, here's a list of recommended next steps.

Already a pro? Just edit this README.md and make it your own. Want to make it easy? [Use the template at the bottom](#editing-this-readme)!

## Add your files

- [ ] [Create](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#create-a-file) or [upload](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#upload-a-file) files
- [ ] [Add files using the command line](https://docs.gitlab.com/ee/gitlab-basics/add-file.html#add-a-file-using-the-command-line) or push an existing Git repository with the following command:

```
cd existing_repo
git remote add origin https://gitlab.com/abhishekb7/capstone-dcp.git
git branch -M main
git push -uf origin main
```

## Integrate with your tools

- [ ] [Set up project integrations](https://gitlab.com/abhishekb7/capstone-dcp/-/settings/integrations)

## Collaborate with your team

- [ ] [Invite team members and collaborators](https://docs.gitlab.com/ee/user/project/members/)
- [ ] [Create a new merge request](https://docs.gitlab.com/ee/user/project/merge_requests/creating_merge_requests.html)
- [ ] [Automatically close issues from merge requests](https://docs.gitlab.com/ee/user/project/issues/managing_issues.html#closing-issues-automatically)
- [ ] [Enable merge request approvals](https://docs.gitlab.com/ee/user/project/merge_requests/approvals/)
- [ ] [Set auto-merge](https://docs.gitlab.com/ee/user/project/merge_requests/merge_when_pipeline_succeeds.html)

## Test and Deploy

Use the built-in continuous integration in GitLab.

- [ ] [Get started with GitLab CI/CD](https://docs.gitlab.com/ee/ci/quick_start/)
- [ ] [Analyze your code for known vulnerabilities with Static Application Security Testing (SAST)](https://docs.gitlab.com/ee/user/application_security/sast/)
- [ ] [Deploy to Kubernetes, Amazon EC2, or Amazon ECS using Auto Deploy](https://docs.gitlab.com/ee/topics/autodevops/requirements.html)
- [ ] [Use pull-based deployments for improved Kubernetes management](https://docs.gitlab.com/ee/user/clusters/agent/)
- [ ] [Set up protected environments](https://docs.gitlab.com/ee/ci/environments/protected_environments.html)

***

# Editing this README
# DCP AI Scouting Platform 


## Clone the Repository
```
git clone https://gitlab.com/abhishekb7/capstone-dcp.git
cd capstone-dcp/backend
```

---

## Create and Configure Environment Variables

### create a `.env` file
Copy the example environment file and update it with your database, Redis, and API keys.



Then, update `.env` with the correct values:


### DB_URL=
### REDIS_URL=
### SERPAPI_KEY=


---

## Install Dependencies

Create a virtual environment and install required dependencies.

```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Set Up PostgreSQL

### Install PostgreSQL
- **Mac (Homebrew)**  
```
brew install postgresql
brew services start postgresql
```

### Create Database and User
```
psql postgres
CREATE DATABASE dcp_ai;

-- Create a user (replace `your_user` and `your_password`)
CREATE USER your_user WITH PASSWORD 'your_password';
ALTER ROLE your_user SET client_encoding TO 'utf8';
ALTER ROLE your_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE your_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE dcp_ai TO your_user;
```

---

## Set Up Redis

### Install and Start Redis
- **Mac (Homebrew)**  
```
brew install redis
brew services start redis
```

---


## Create Database Tables

After setting up PostgreSQL, run the following to create all necessary tables:

python create_tables.py

---

## Run the Application

```
uvicorn main:app --reload
```

This will start the FastAPI server at `http://127.0.0.1:8000`.

---
## Running Tests

Run the automated tests to ensure everything is working:

```
python tests.py founder "Elon Musk"
python tests.py company "Tesla"
```
