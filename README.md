# data-processor

JSON transformation pipeline with unit and integration tests, hooked up to Jenkins.

## what it does

Takes raw JSON, flattens nested fields, filters by value, renames keys, and gives basic stats.

## run locally

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
```

## structure

```
src/processor.py          main logic
tests/unit/               unit tests (36)
tests/integration/        integration tests (12)
Jenkinsfile               CI/CD pipeline
```

## jenkins setup

create a pipeline job pointing at this repo, set script path to `Jenkinsfile`.
needs two credentials: `deploy-ssh-host` and `deploy-ssh-key`.
