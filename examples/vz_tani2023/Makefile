# ENCflow/examples/vz_tani2023/Makefile
#   make        ../../bin/ の実行ファイルへのリンクと格子入力(data/)を作る
#   make clean  リンクと計算結果を削除する(論文から取り出した data/ の数値も消す)

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src

all: links data/zone.txt

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

data/zone.txt: make_case.py
	python3 make_case.py data

install: all

clean:
	rm -rf result_* data
	rm -f encflow encflow_mpi Screen*.log

.PHONY: all links install clean
