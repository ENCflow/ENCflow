# ENCflow/examples/landslide_tsunami/Makefile
#   make        ../../bin/ の実行ファイルへのリンクと入力(z.txt, slide.txt, submarine.txt)を作る
#   make clean  リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src

all: links inputs

inputs: z.txt slide.txt submarine.txt

z.txt slide.txt submarine.txt: make_init.py
	python3 make_init.py z > z.txt
	python3 make_init.py slide > slide.txt
	python3 make_init.py submarine > submarine.txt

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
	rm -rf result result_* save
	rm -f encflow encflow_mpi a.out Screen*.log z.txt slide.txt submarine.txt

.PHONY: all links install clean
