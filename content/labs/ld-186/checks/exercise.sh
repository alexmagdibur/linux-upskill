mkdir -p /tmp/.ex
sudo /opt/lab/writer.sh > /tmp/.ex/writer.out 2>&1; echo $? > /tmp/.ex/writer.rc
true
