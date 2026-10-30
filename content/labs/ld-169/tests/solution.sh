cd ~ && tar czpf backup.tar.gz data && sha256sum backup.tar.gz > backup.sha256 && tar xzpf backup.tar.gz -C ~/restore
