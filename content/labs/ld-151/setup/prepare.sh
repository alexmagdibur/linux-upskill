install -d /opt/lab /var/lib/labapp
cat > /opt/lab/sc.py <<'EOT'
import ctypes, os, time
libc = ctypes.CDLL(None, use_errno=True)
while True:
    r = libc.mount(b"none", b"/mnt", b"tmpfs", 0, None)
    err = ctypes.get_errno()
    if r == 0:
        libc.umount(b"/mnt")
    with open("/var/lib/labapp/seccomp.txt", "w") as f:
        f.write("mount=%s\n" % ("blocked" if (r != 0 and err == 1) else "allowed"))
    with open("/var/lib/labapp/heartbeat2", "w") as f:
        f.write(str(time.time()))
    time.sleep(1)
EOT
cat > /etc/systemd/system/labseccomp.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/sc.py
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labseccomp >/dev/null 2>&1
sleep 2
