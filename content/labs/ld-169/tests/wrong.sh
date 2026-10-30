cd ~ && tar czf backup.tar.gz data && sha256sum backup.tar.gz > backup.sha256 && tar xzf backup.tar.gz -C ~/restore
