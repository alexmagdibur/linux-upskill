sudo sed -i 's#^    fds.append(open("/dev/null"))#    open("/dev/null").close()#' /opt/lab/leaky.py
sudo systemctl restart leaky
sleep 4
