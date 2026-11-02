# ENCflow/examples/debris_bedrock/Makefile
#   make        ../../bin/ の実行ファイルへのリンクと入力(make_init.py)を作る
#   make run    前半の 7 構成(T_b T_c C_b C_c T_b05 T_b20 W)を順に計算する(各 約 30 秒)
#   make long   補足(長期の連鎖): make_long.py の 50 構成を Run_long.sh で並列に回す($(NP) 並列で約 8 分)
#   make clean  リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
CASES	= T_b T_c C_b C_c T_b05 T_b20 W
NP	= 4

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
	    ./encflow param_$$c.txt 2>&1 | tee Screen_$$c.log; \
	done

long: all long/configs.txt
	./Run_long.sh $(NP) 2>&1 | tee Run_long.log

long/configs.txt: make_long.py make_init.py
	python3 make_long.py

install: all

clean:
	rm -rf result result_* save save_* long
	rm -f encflow encflow_mpi a.out Screen.log Screen_*.log Run_long.log analysis*.txt
	rm -f z.txt sd_*.txt

.PHONY: all links inputs run long install clean
