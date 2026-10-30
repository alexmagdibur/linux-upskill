sed -E 's/(token|password|api_key)=[^ ]+/\1=[REDACTED]/g' ~/logs/app.log > ~/logs/sanitized.log
