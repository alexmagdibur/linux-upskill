ss -ltnp | grep ':9102 ' | grep -o 'pid=[0-9]*' | cut -d= -f2 > ~/pid.txt
