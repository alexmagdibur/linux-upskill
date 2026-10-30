cd ~/maze/a/b && printf '{"cwd":"%s","home":"%s","bash":"%s"}\n' "$PWD" "$HOME" "$(command -v bash)" > ~/answer.json
