mkdir -p ~/site/css ~/site/img ~/restore
echo "<h1>Hello</h1>" > ~/site/index.html
echo "body{margin:0}" > ~/site/css/style.css
echo "LOGO" > ~/site/img/logo.txt
mkdir -p ~/.stage && echo alpha > ~/.stage/a.txt && echo beta > ~/.stage/b.txt
tar czf ~/backup.tar.gz -C ~/.stage a.txt b.txt && rm -rf ~/.stage
