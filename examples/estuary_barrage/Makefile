# ENCflow/examples/estuary_barrage/Makefile
#   make          ../../bin/ の実行ファイルへのリンクと入力(data/。gen_data.py)を作る
#   make run      6 ケースを順に計算する(1 ケース 15 分前後。4 スレッド)
#   make clean
TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
CASES	= nobarrage barrage nobarrage_off barrage_off nobarrage_mix barrage_mix

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

inputs: data/tide.txt

data/tide.txt: gen_data.py
	python3 gen_data.py

run: all
	@for c in $(CASES); do ./encflow param_$$c.txt | tee Screen_$$c.log; done

clean:
	rm -rf data $(addprefix result_,$(CASES))
	rm -f encflow encflow_mpi a.out Screen*.log

.PHONY: all links inputs run clean
