# ENCflow/examples/paddy_basin/Makefile
#   make        ../../bin/ の実行ファイルへのリンクと、入力(data/)・設定(runs/)を作る(make_basin.py)
#   make run    39 ケースを計算する(1 ケース 1 スレッドで NP ケースずつ。4 コアで約 50 分。計算済みのケースは飛ばす)
#   make figs   図(figs/ と en/figs/)を描き、数表を書く
#   make clean  リンクと生成物(data/・runs/)を削除する
# 並列数は NP(既定 4): make run NP=2

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
NP	?= 4

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ]; then $(MAKE) -C $(SRCDIR) install; fi
	@mkdir -p runs
	@ln -sf $(BINDIR)/encflow encflow
	@ln -sf ../$(BINDIR)/encflow runs/encflow

inputs: runs/cases.txt

runs/cases.txt: make_basin.py
	python3 make_basin.py

run: all
	./run_cases.sh $(NP)

figs:
	python3 plot_results.py
	python3 plot_results.py en > /dev/null

install: all

clean:
	rm -rf runs data __pycache__
	rm -f encflow

.PHONY: all links inputs run figs install clean
