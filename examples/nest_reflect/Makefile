# ENCflow/examples/nest_reflect/Makefile
#   make          ../../bin/ の実行ファイルへのリンクと、各格子の初期水位(data/。make_inputs.py)を作る
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

inputs: data/e_parent.txt

data/e_parent.txt: make_inputs.py
	python3 make_inputs.py

clean:
	rm -rf result_* data
	rm -f encflow encflow_mpi Screen*.log
