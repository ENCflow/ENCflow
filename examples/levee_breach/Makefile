# ENCflow/examples/levee_breach/Makefile
#   make          ../../bin/ の実行ファイルへのリンクと入力(z.txt 等、bm/)を作る
#   make clean
TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

inputs: z.txt bm/bmlist.txt

z.txt: make_terrain.py
	python3 make_terrain.py

bm/bmlist.txt: z.txt make_breach.py
	python3 make_breach.py --z z.txt --cols 21 22 --rows 48 52 --floor-col 23 \
	    --t0 70 --t1 90 --tdeep 10 --out bm

clean:
	rm -rf result result_vwall bm
	rm -f encflow encflow_mpi a.out Screen*.log z.txt z_vwall.txt rn.txt rw.txt

.PHONY: all links inputs clean
