ls ~/lab > /dev/null; echo "ok=$?" > ~/codes.txt
ls ~/lab/missing 2> /dev/null; echo "fail=$?" >> ~/codes.txt
echo "No such file or directory: файл не существует" > ~/why.txt
