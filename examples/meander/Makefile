# ENCflow/examples/meander/Makefile
#   make        ../../bin/ の実行ファイルへのリンクを作る
#   make clean  リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src

all: links inputs

inputs: z.txt h.txt sd.txt

z.txt h.txt sd.txt: make_init.py
	@python3 make_init.py z > z.txt && python3 make_init.py h > h.txt && python3 make_init.py sd > sd.txt

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
	rm -rf result save
	rm -f encflow encflow_mpi a.out Screen*.log z.txt h.txt sd.txt

.PHONY: all links inputs install clean
