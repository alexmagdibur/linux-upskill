v=~/exp/vault
before=$(stat -c %a $v)
chmod u+x $v
after=$(stat -c %a $v)
echo "before=$before after=$after" > ~/exp/answer.txt
