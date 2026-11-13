# ENCflow/examples/delta/Makefile
#   make        ../../bin/ の実行ファイルへのリンクを作り、入力(z_*.txt, sd_*.txt, sw_tide.txt, tide_m2.txt)を生成する
#   make ens    実現ごとの違いを見るアンサンブル 6 実現の入力と設定(z_ens_*.txt, param_ens_*.txt)を生成する
#   make clean  リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
CASES	= base sand mud varq fix wave baseqb
ENS	= ens_w1 ens_w2 ens_w3 ens_w4 ens_w5 ens_c1

all: links inputs

inputs: $(foreach c,$(CASES),z_$(c).txt sd_$(c).txt) sw_tide.txt tide_m2.txt

z_%.txt: make_init.py
	@python3 make_init.py $* z > $@

sd_%.txt: make_init.py
	@python3 make_init.py $* sd > $@

sw_tide.txt: make_init.py
	@python3 make_init.py tide sw > $@

tide_m2.txt: make_init.py
	@python3 make_init.py tide tide > $@

ens: all $(foreach c,$(ENS),z_$(c).txt param_$(c).txt)

param_ens_%.txt: make_init.py param.txt
	@python3 make_init.py ens_$* param > $@

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
	rm -f encflow encflow_mpi a.out Screen*.log z_*.txt sd_*.txt sw_tide.txt tide_m2.txt timeseries_*.csv param_ens_*.txt

.PHONY: all links inputs install clean ens
