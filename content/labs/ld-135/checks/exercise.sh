rm -rf ~/.ex; mkdir -p ~/.ex/out
printf 't1 1\nt2 1\nt3 1\nt4 1\nt5 1\nt6 1\n' > ~/.ex/tasks.txt
printf 'slow 5\nfast 0.2\n' > ~/.ex/tasks2.txt
[ -f ~/bin/batch.py ] || exit 0
timeout 6 python3 ~/bin/batch.py --dry-run --out ~/.ex/out ~/.ex/tasks.txt > ~/.ex/dry.log 2>/dev/null < /dev/null; echo $? > ~/.ex/dry.rc
ls -A ~/.ex/out | wc -l > ~/.ex/dry.n
timeout 10 python3 ~/bin/batch.py --max-parallel 2 --out ~/.ex/out ~/.ex/tasks.txt > ~/.ex/run.log 2>/dev/null < /dev/null; echo $? > ~/.ex/run.rc
ls ~/.ex/out | sort > ~/.ex/run.files
rm -f ~/.ex/out/*
timeout 8 python3 ~/bin/batch.py --timeout 1 --out ~/.ex/out ~/.ex/tasks2.txt > ~/.ex/to.log 2>/dev/null < /dev/null; echo $? > ~/.ex/to.rc
ls ~/.ex/out | sort > ~/.ex/to.files
true
