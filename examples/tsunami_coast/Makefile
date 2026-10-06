# ENCflow/examples/tsunami_coast/Makefile
#   make          ../../bin/ の実行ファイルへのリンクと入力(z.txt、bm/、bm_off/)を作る
#   make clean
TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
F2D	= $(TOPDIR)/utils/fault2disp

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

inputs: z.txt bm/bmlist.txt bm/bmlist_inst.txt bm_off/bmlist.txt

z.txt:
	python3 make_init.py > $@

$(F2D)/fault2disp:
	$(MAKE) -C $(F2D)

bm/bmlist.txt: fault2disp_all.txt $(F2D)/fault2disp
	$(F2D)/fault2disp fault2disp_all.txt

bm/bmlist_inst.txt: bm/bmlist.txt
	printf '# instantaneous: final displacement at t = 0\n0.0  bm/disp_0010.txt\n' > $@

bm_off/bmlist.txt: fault2disp_offshore.txt $(F2D)/fault2disp
	$(F2D)/fault2disp fault2disp_offshore.txt

clean:
	rm -rf result_* bm bm_off
	rm -f encflow encflow_mpi a.out Screen*.log z.txt

.PHONY: all links inputs clean
