# ENCflow/examples/bedrock_cover/Makefile
#   make        ../../bin/ の実行ファイルへのリンクと入力(make_init.py)を作る
#   make run    7 構成(A_p A_a A_pa B_p B_a C_pa D_p)を順に計算する(合わせて約 5 分)
#   make clean  リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
CASES	= A_p A_a A_pa B_p B_a C_pa D_p

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

inputs: zinit_6.txt

zinit_6.txt: make_init.py
	python3 make_init.py

run: all
	@for c in $(CASES); do \
	    ./encflow param_$$c.txt 2>&1 | tee Screen_$$c.log; \
	done

install: all

clean:
	rm -rf result result_* save save_*
	rm -f encflow encflow_mpi a.out Screen.log Screen_*.log analysis*.txt
	rm -f zinit_*.txt hinit_*.txt sd_*.txt sdzero_*.txt

.PHONY: all links inputs run install clean
