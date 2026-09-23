### Email alerting module
This program checks the avalibale ALERTS (currently hardcoded) and checks for any duplicates to remove them, and sort them based on its severity. This sorted alerts are then used to create EMAILS using different templates, and send using SMPT and any email client.

Currenty this will only deals with EMAIL from SEVERITY_CHANNELS, because other methods like [sms, webhooks, siem, etc] are not inegrated in this.
These methods needs to be integrated later in the main project. 

to run this

        python main.py 



##### SMPT setup
Also create a new `.env` file and copy code from `.env.example`
Then fill the SMTP credentials got from any email provider's website like [mailgun , mailtrap]





