# ENCflow/examples/bridge_wood_jam/Makefile
#   make        ../../bin/ の実行ファイルへのリンクと入力(make_terrain.py)を作る
#   make run    基本の 3 ケース(流木なし・台帳だけ・集積の抵抗あり)を順に計算する
#   make sens   捕捉の仮定と抵抗の係数を変えた 4 ケースを計算する
#   make clean  リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
CASES	= nowood ledger jam
SENS	= e03 e01 loose dense

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

data/z.txt: make_terrain.py
	python3 make_terrain.py

run: all
	@for c in $(CASES); do \
	    if [ $$c = jam ]; then p=param.txt; else p=param_$$c.txt; fi; \
	    ./encflow $$p | tee Screen_$$c.log; \
	done

sens: all
	@for c in $(SENS); do \
	    ./encflow param_$$c.txt | tee Screen_$$c.log; \
	done

install: all

clean:
	rm -rf result_* save data
	rm -f encflow encflow_mpi a.out Screen*.log

.PHONY: all links inputs run sens install clean
