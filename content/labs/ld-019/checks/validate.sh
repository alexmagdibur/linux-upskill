chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
A=/home/student/app
chk points_to_v2 '[ -L $A/config ] && [ "$(readlink -f $A/config)" = $A/releases/v2/app.conf ]'
chk app_sees_new '[ "$(cat /home/student/.ex/out)" = LEVEL=new ]'
chk no_copy '[ "$(cat $A/old/app.conf)" = LEVEL=old ] && [ "$(cat $A/releases/v2/app.conf)" = LEVEL=new ]'
