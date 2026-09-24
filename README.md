## Email alerting - darktrace
This program checks the avalibale ALERTS (currently hardcoded) and checks for any duplicates to remove them, and sort them based on its severity. This sorted alerts are then used to create EMAILS using different templates, and send using SMPT and any email client.

Currenty this will only deals with EMAIL from SEVERITY_CHANNELS, because other methods like [sms, webhooks, siem, etc] are not inegrated in this.
These methods needs to be integrated later in the main project. 


Also, this project uses Celery + Redis for background email sending — Redis queues the jobs, Celery's worker sends them (including delayed sends for batching/digests) without blocking the main script.

----
### To run this program: 
start Redis (if not already running):  -- (please use multiple terminals for this)

        redis-server --daemonize yes

start the worker, stays running:

        celery -A celery_app worker --loglevel=info

*Confirm you see the [tasks] list with all 3 tasks

Run the main script:

        python3 main.py

----
### Result
The critical + High alerts are immediatly send. (duplicates are removed)
Medium alerts are Batched and send after a certain delay (now its set to 5min demo)
Low + informational alerts are Batched and send after a certain delay (demo set to 1minutes)

-----
### SMPT setup
Also create a new `.env` file and copy code from `.env.example`
Then fill the SMTP credentials got from any email provider's website like [mailgun , mailtrap].
If no SMTP credentials are given , the program will just DRY RUN without sending actuall emails.

----
### Requirments & additional informations
install these

        pip install celery redis
        sudo pacman -S redis

Start these:

        redis-server --daemonize yes
        celery -A celery_app worker --loglevel=info
        redis-cli ping

To wipes any stale queued tasks or old task results sitting in Redis, without shutting the server down.

        redis-cli FLUSHALL

