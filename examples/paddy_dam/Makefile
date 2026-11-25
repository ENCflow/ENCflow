# ENCflow/examples/paddy_dam/Makefile
#   make        ../../bin/ の実行ファイルへのリンクと入力(data/。make_district.py)を作る
#   make run    10 m の区画の解像(B)の 4 ケース(N・D・Du・Dd)と、30 m の表現 A の 4 ケース(片方向・双方向 ×
#               通常・田んぼダム)を順に計算する(4 コアの計算機で B は 1 ケース 10〜20 分、A は 2 分前後)
#   make figs   図(figs/・en/figs/)と数表(標準出力)
#   make clean  リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
CASES	= N D Du Dd A30_N A30_D A30_N2 A30_D2

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

inputs: data/z.txt

data/z.txt: make_district.py
	python3 make_district.py

run: all
	@for c in $(CASES); do \
	    ./encflow param_$$c.txt | tee Screen_$$c.log; \
	done

figs:
	python3 plot_results.py
	python3 plot_results.py en

install: all

clean:
	rm -rf result_* data
	rm -f encflow encflow_mpi a.out Screen*.log

.PHONY: all links inputs run figs install clean
