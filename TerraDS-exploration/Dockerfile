FROM python:3.13.7-slim

WORKDIR /app

COPY requirements.txt .
COPY process_commits.py .
COPY all_module.tar .
COPY immut-export/ ./immut-export/

RUN python3 -m venv venv
RUN . venv/bin/activate && pip install --no-cache-dir -r requirements.txt

ENV PATH="/app/venv/bin:$PATH"

ENTRYPOINT ["python", "process_commits.py"]
CMD ["-nw", "12", "-tar", "all_module.tar"]