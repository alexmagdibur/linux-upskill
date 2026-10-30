mkdir -p ~/logs
cat > ~/logs/app.log <<'EOT'
req=r001 user=alice token=tok_ABC123 msg=login
req=r002 user=bob password=hunter2 msg=signup
req=r003 user=carol msg=ok
req=r004 user=dave api_key=sk_live_99XYZ msg=call
req=r005 user=erin token=tok_QRS789 password=p4ssw0rd msg=reset
req=r006 user=frank msg=logout
EOT
