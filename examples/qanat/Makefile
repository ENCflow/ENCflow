# ENCflow/examples/qanat/Makefile
#   make        ../../bin/ の実行ファイルへのリンクと入力(gen_data.py)を作る
#   make run    3 ケースを順に計算する(1 ケース 1 スレッドで 25 分ほど)
#   make clean  リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
CASES	= qanat well2 well5

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

inputs: data_qanat/z.txt

data_qanat/z.txt: gen_data.py
	python3 gen_data.py

run: all
	@for c in $(CASES); do \
	    if [ $$c = qanat ]; then p=param.txt; else p=param_$$c.txt; fi; \
	    ./encflow $$p | tee Screen_$$c.log; \
	done

install: all

clean:
	rm -rf result_* data_qanat
	rm -f encflow encflow_mpi Screen*.log

.PHONY: all links inputs run install clean
