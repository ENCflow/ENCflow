# ENCflow/examples/timberyard/Makefile
#   make        ../../bin/ の実行ファイルへのリンクと入力(make_terrain.py)を作る
#   make run    4 ケースを順に計算する(1 ケース 4 スレッドで 1 分前後)
#   make supp   補足(材木がどこに残るかを決めるパラメータ)の 2 ケースを計算する
#   make clean  リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
CASES	= ise hold far wall4
SUPP	= vstop0 refloat

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

inputs: z.txt

z.txt: make_terrain.py
	python3 make_terrain.py

run: all
	@for c in $(CASES); do \
	    if [ $$c = ise ]; then p=param.txt; else p=param_$$c.txt; fi; \
	    ./encflow $$p | tee Screen_$$c.log; \
	done

supp: all
	@for c in $(SUPP); do \
	    ./encflow param_$$c.txt | tee Screen_$$c.log; \
	done

install: all

clean:
	rm -rf result_* save
	rm -f encflow encflow_mpi a.out Screen*.log z.txt z_wall4.txt gv.txt sw.txt stock.txt stock_far.txt

.PHONY: all links inputs run supp install clean
