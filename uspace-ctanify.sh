#!/bin/bash
set -x
set -e

rm -f uspace.pdf || true
rm -f uspace-test.pdf || true

latexmk -gg -xelatex -interaction=nonstopmode uspace-test.tex >uspace-test.tex.output 2>&1 </dev/null &

latexmk -gg -lualatex -interaction=nonstopmode uspace.tex >uspace.tex.output 2>&1 </dev/null &

echo waiting for jobs to finish
wait

echo "uspace-test.tex.output:"
cat uspace-test.tex.output

echo "uspace.tex.output:"
cat uspace.tex.output

DOCDIR=doc/latex/uspace
LATEXDIR=tex/latex/uspace

TEMP_DIR=`mktemp -d -p "$PWD"`
read -d '' CTANIFY_MAP <<EOF || true
           uspace.sty=$LATEXDIR 
           README.md=$DOCDIR 
           LICENSE=$DOCDIR 
           uspace-test.tex=$DOCDIR 
           uspace-test.pdf=$DOCDIR 
           uspace.tex=$DOCDIR 
           uspace.pdf=$DOCDIR
           uspace-ctanify.sh=$DOCDIR
EOF

echo "map:" $CTANIFY_MAP

for entry in $CTANIFY_MAP ; do
    file=${entry%=*}
    #target_dir=${entry#*=}
    cp -v "$file" "$TEMP_DIR"
done

ROOT_DIR="$PWD"
(
    cd "$TEMP_DIR"
    setfacl -b *
    chmod +rw-x *
    chmod +x uspace-ctanify.sh
    ctanify --pkgname=uspace $CTANIFY_MAP
    mv -vf uspace.tar.gz "$ROOT_DIR"
)
        
tar tvvzf uspace.tar.gz

rm -rf "$TEMP_DIR"
