cd /usr/local/src/hello-lab && make && sudo make install PREFIX=/opt/hello-lab
echo 'export PATH=$PATH:/opt/hello-lab/bin' | sudo tee /etc/profile.d/hello-lab.sh > /dev/null
