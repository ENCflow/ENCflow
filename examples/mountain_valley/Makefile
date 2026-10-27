# ENCflow/examples/mountain_valley/Makefile
#   make        ../../bin/ の実行ファイルへのリンクを作る
#   make clean  リンクと生成物を削除する

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src

all: links

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
	rm -rf result result_* save save_*
	rm -f encflow encflow_mpi a.out Screen.log Screen_*.log analysis*.txt
	rm -f z_init*.txt h_init*.txt sd_zero*.txt up_base*.txt up_drop*.txt wthr_hill*.txt rock_base*.txt p_*.txt

.PHONY: all links install clean
