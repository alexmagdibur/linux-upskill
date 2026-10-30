grep -vE 'token=|password=|api_key=' ~/logs/app.log > ~/logs/sanitized.log
