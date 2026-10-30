# ENCflow/examples/ashfall_lahar/Makefile
#   make        ../../bin/ の実行ファイルへのリンクと入力(make_init.py)を作る
#   make run    4 ケースを順に計算する(1 ケース数分)
#   make rotated  補足実験(谷の向きと格子): 0°・45° の谷 × 8・4 近傍の 4 ケース
#   make clean  リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
CASES	= preeruption water ash dam

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

z.txt: make_init.py
	python3 make_init.py

run: all
	@for c in $(CASES); do \
	    if [ $$c = ash ]; then p=param.txt; else p=param_$$c.txt; fi; \
	    ./encflow $$p | tee Screen_$$c.log; \
	done

rotated: links data_rot0/z.txt
	@for c in rot0_8 rot45_8 rot0_4 rot45_4; do \
	    ./encflow param_$$c.txt | tee Screen_$$c.log; \
	done

data_rot0/z.txt: make_rotated.py make_init.py
	python3 make_rotated.py

install: all

clean:
	rm -rf result_* save data_rot0 data_rot45
	rm -f encflow encflow_mpi a.out Screen*.log z.txt z_noash.txt z_dam.txt ash.txt ash_dam.txt

.PHONY: all links inputs run rotated install clean
