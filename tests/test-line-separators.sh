#!/bin/bash
set -eu

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
test_dir=$(mktemp -d)
trap 'rm -rf -- "$test_dir"' EXIT
cp "$repo_dir/uspace.sty" "$repo_dir/tests/line-separators.tex" "$test_dir/"
cd "$test_dir"

if [ "$#" -eq 0 ]; then
    set -- pdflatex xelatex lualatex
fi

status=0
for engine in "$@"; do
    if "$engine" -interaction=nonstopmode -halt-on-error -jobname="$engine" \
        line-separators.tex >"$engine.output" 2>&1; then
        echo "$engine: line separator tests passed"
    else
        cat "$engine.output"
        status=1
    fi
done
exit "$status"
