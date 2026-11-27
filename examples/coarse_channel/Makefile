# ENCflow/examples/coarse_channel/Makefile
#   make           ../../bin/ の実行ファイルへのリンクと、全系列の入力(runs/)を作る
#   make run       全系列を計算する(4 コアで 50 分前後。計算済みのケースは飛ばす)
#   make occ | axis | oblique | wide | mask | bend | wet | fmin   系列ごとに計算する
#   make figs      図(figs/ と en/figs/)を描き、数表を書く
#   make clean     リンクと runs/ を削除する
# 並列数は NP(既定 4): make run NP=2

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
SERIES	= occ axis oblique wide mask bend wet fmin
NP	?= 4

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ]; then $(MAKE) -C $(SRCDIR) install; fi
	@mkdir -p runs
	@ln -sf $(BINDIR)/encflow encflow
	@ln -sf ../$(BINDIR)/encflow runs/encflow

inputs: runs/cases_occ.txt

runs/cases_occ.txt: make_cases.py
	python3 make_cases.py gen

run: all
	@for s in $(SERIES); do ./run_series.sh $$s $(NP) || exit 1; done

$(SERIES): all
	./run_series.sh $@ $(NP)

figs:
	python3 plot_results.py
	python3 plot_results.py en > /dev/null

install: all

clean:
	rm -rf runs __pycache__
	rm -f encflow

.PHONY: all links inputs run figs install clean $(SERIES)
