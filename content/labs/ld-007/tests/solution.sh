cat > ~/lib/safe.sh <<'EOT'
godir() {
  cd -- "$HOME/dirs/$1"
}
EOT
