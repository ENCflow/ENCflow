# ENCflow/test/nest_identity/Makefile
#   make              ドライバ nestcheck(比 1:1 自己ネスト恒等)を src の
#                     libencflow.a からビルドし、encflow へのリンクも張る
#   make MODE=mpi     MPI 版(nestcheck_mpi。src も MPI でビルドされる)
#   make clean
TOPDIR	= ../..
include $(TOPDIR)/make.inc

BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
LIB	= $(SRCDIR)/libencflow.a

ifeq ($(MODE),mpi)
EXE	= nestcheck_mpi
else
EXE	= nestcheck
endif

all: $(EXE) links

$(EXE): nestcheck.o $(LIB)
	$(FRT) -o $@ $(FFLAGS) nestcheck.o $(LIB) $(LDFLAGS)

# .mod は src 側。モード切替で m_parallel の .mod が変わるので毎回コンパイル
nestcheck.o: nestcheck.f90 $(LIB)
	$(FRT) -c $(FFLAGS) -I$(SRCDIR) nestcheck.f90

$(LIB): FORCE
	$(MAKE) -C $(SRCDIR) libencflow.a

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

FORCE:

clean:
	rm -rf result_* data_chichibu_child hinit_*.txt
	rm -f nestcheck nestcheck_mpi *.o *.mod encflow encflow_mpi a.out Screen*.log

.PHONY: all links clean FORCE
