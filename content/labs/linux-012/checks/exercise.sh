cd ~
rm -f ~/.hello_out
{ bash -lc 'hello' 2>/dev/null; bash -ic 'hello' 2>/dev/null; } | head -n 1 > ~/.hello_out
true
