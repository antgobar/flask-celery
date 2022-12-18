import os
import time

from flask import Flask, request, render_template, redirect, url_for
from tasks import make_celery
from redis import Redis

app = Flask(__name__)
app.config.update(
    CELERY_CONFIG={
        "broker_url": os.environ.get("CELERY_BROKER_URL", "amqp://localhost:5672"),
        "result_backend": os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379"),
    }
)
celery = make_celery(app)

from celery.result import AsyncResult


r = Redis("redis", 6379)


@celery.task()
def name_length(name):
    length = len(name)
    time.sleep(length)
    return length


@app.route("/", methods=('GET', 'POST'))
def index():
    if request.method == 'POST':
        artist_name = request.form["artist_name"]
        num = int(request.form["num"])
        for _ in range(num):
            task = name_length.delay(artist_name)
        return redirect(url_for("resolve", task_id=task.id))
    return render_template("index.html")


@app.route("/task/<task_id>")
def resolve(task_id):
    task_result = AsyncResult(task_id, app=celery)
    if task_result.ready():
        return render_template("resolve.html", task_result=task_result)

    return "Try again later"


@app.route("/purge")
def purge():
    for key in r.scan_iter():
        if "celery" in key.decode():
            r.delete(key)
    return "Purged keys"


@app.route("/delete/<task_id>")
def clear_task(task_id):
    celery.AsyncResult(task_id).forget()
    return f"Task ID: {task_id} cleared"
