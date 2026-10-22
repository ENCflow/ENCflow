# ENCflow/examples/delta/Makefile
#   make        ../../bin/ の実行ファイルへのリンクを作り、入力(z_*.txt, sd_*.txt)を生成する
#   make clean  リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
CASES	= base sand mud varq fix wave

all: links inputs

inputs: $(foreach c,$(CASES),z_$(c).txt sd_$(c).txt)

z_%.txt: make_init.py
	@python3 make_init.py $* z > $@

sd_%.txt: make_init.py
	@python3 make_init.py $* sd > $@

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

install: all

clean:
	rm -rf result_* save_*
	rm -f encflow encflow_mpi a.out Screen*.log z_*.txt sd_*.txt timeseries_*.csv

.PHONY: all links inputs install clean
