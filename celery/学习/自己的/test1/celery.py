from __future__ import absolute_import, unicode_literals
from celery import Celery

app = Celery('test1',
             broker='redis://localhost:6379/0',
             backend='redis://localhost:6379/1',
             include=['test1.tasks'])

# Optional configuration, see the application user guide.
app.conf.update(
    result_expires=3600,
)

if __name__ == '__main__':
    app.start()