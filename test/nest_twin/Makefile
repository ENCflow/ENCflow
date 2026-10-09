# ENCflow/test/nest_twin/Makefile
#   make              ドライバ twin(複数インスタンス交互実行)を src の
#                     libencflow.a からビルドし、encflow へのリンクも張る
#   make MODE=mpi     MPI 版(twin_mpi。src も MPI でビルドされる)
#   make clean
TOPDIR	= ../..
include $(TOPDIR)/make.inc

BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
LIB	= $(SRCDIR)/libencflow.a

ifeq ($(MODE),mpi)
EXE	= twin_mpi
else
EXE	= twin
endif

all: $(EXE) links

$(EXE): twin.o $(LIB)
	$(FRT) -o $@ $(FFLAGS) twin.o $(LIB) $(LDFLAGS)

# .mod は src 側。モード切替で m_parallel の .mod が変わるので毎回コンパイル
twin.o: twin.f90 $(LIB)
	$(FRT) -c $(FFLAGS) -I$(SRCDIR) twin.f90

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
	rm -rf result_* single_*
	rm -f twin twin_mpi *.o *.mod encflow encflow_mpi a.out Screen*.log

.PHONY: all links clean FORCE
