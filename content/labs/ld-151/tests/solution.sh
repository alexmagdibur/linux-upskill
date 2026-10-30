sudo mkdir -p /etc/systemd/system/labseccomp.service.d
printf '[Service]\nSystemCallFilter=@system-service\nSystemCallErrorNumber=EPERM\n' | sudo tee /etc/systemd/system/labseccomp.service.d/seccomp.conf > /dev/null
