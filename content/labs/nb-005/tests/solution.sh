ls --help | grep -- '-S' > /dev/null
echo "-S : сортировка по размеру (size), крупные первыми" > ~/option.txt
ls -S ~/files > ~/sorted.txt
