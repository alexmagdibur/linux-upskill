cd ~/release && sha256sum *.bin > SHA256SUMS
cd ~/received && sha256sum -c ~/release/SHA256SUMS 2>/dev/null | grep FAILED | cut -d: -f1 > ~/bad.txt
true
