for p in 9301 9302; do echo | openssl s_client -connect 127.0.0.1:$p -servername app.lab.test -CAfile /etc/lab/ca/ca.crt 2>&1 | grep "Verify return code"; done
sudo sed -i 's#old\.#new.#g' /etc/lab/tls/labtls-2.env
sudo systemctl restart labtls@2
sleep 1
