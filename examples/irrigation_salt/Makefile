# ENCflow/examples/irrigation_salt/Makefile
#   make        ../../bin/ の実行ファイルへのリンクと入力(gen_data.py)を作る
#   make run    4 ケースを順に計算する(1 スレッドで計 2〜3 分)
#   make clean  リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
CASES	= nodrain drain leach drain_m100

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

inputs: data_irrigation/z_drain.txt

data_irrigation/z_drain.txt: gen_data.py
	python3 gen_data.py

run: all
	@for c in $(CASES); do \
	    OMP_NUM_THREADS=1 ./encflow param_$$c.txt > Screen_$$c.log 2>&1 || exit 1; \
	    echo "done $$c"; \
	done

install: all

clean:
	rm -rf result_* data_irrigation
	rm -f encflow encflow_mpi Screen*.log

.PHONY: all links inputs run install clean
