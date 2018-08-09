#!/usr/bin/env bash
alias yw='java -jar ~/yesworkflow-0.2.2.0-SNAPSHOT-jar-with-dependencies.jar'

cat yw/Original_LinearParseYW.txt | yw graph -c extract.comment='#' > gv/Linear.gv

cat yw/2Original_SPParseYW.txt | yw graph -c extract.comment='#' > gv/Serial-Parallel.gv

dot -Tpdf gv/Linear.gv -o pdf/Linear.pdf

dot -Tpdf gv/Serial-Parallel.gv -o pdf/Serial-Parallel.pdf


dot -Tpng gv/Linear.gv -o png/Linear.png

dot -Tpng gv/Serial-Parallel.gv -o png/Serial-Parallel.png
