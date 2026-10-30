mkdir -p ~/release ~/received
printf 'alpha-artifact\n' > ~/release/a.bin
printf 'beta-artifact\n' > ~/release/b.bin
printf 'gamma-artifact\n' > ~/release/c.bin
cp ~/release/*.bin ~/received/
echo tampered >> ~/received/b.bin
