# ENCflow/test/nhbottom/Makefile
#   make              ドライバ uplift(ライブラリ API で底面を動かす)を
#                     src の libencflow.a からビルドし、encflow へのリンクも張る
#   make MODE=mpi     MPI 版(uplift_mpi。src も MPI でビルドされる)
#   make inputs       海底地滑りケースの入力(z.txt, submarine.txt)を生成
#   make inputs_bm    構成 3(fn_bedmotion)のスナップショット表と変位ファイル(bm/)を生成
#   make clean
TOPDIR	= ../..
include $(TOPDIR)/make.inc

BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
LIB	= $(SRCDIR)/libencflow.a
LSDIR	= $(TOPDIR)/examples/landslide_tsunami

ifeq ($(MODE),mpi)
EXE	= uplift_mpi
else
EXE	= uplift
endif

all: $(EXE) links inputs

$(EXE): uplift.o $(LIB)
	$(FRT) -o $@ $(FFLAGS) uplift.o $(LIB) $(LDFLAGS)

# .mod は src 側。モード切替で m_parallel の .mod が変わるので毎回コンパイル
uplift.o: uplift.f90 $(LIB)
	$(FRT) -c $(FFLAGS) -I$(SRCDIR) uplift.f90

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

inputs: z.txt submarine.txt

inputs_bm: bm/bmlist.txt bm_ls/bmlist.txt

bm/bmlist.txt:
	python3 Bedmotion_inputs.py

bm_ls/bmlist.txt:
	python3 Bedmotion_inputs.py ls

z.txt:
	python3 $(LSDIR)/make_init.py z > $@

submarine.txt:
	python3 $(LSDIR)/make_init.py submarine > $@

FORCE:

clean:
	rm -rf result result_* save_bm bm bm_ls
	rm -f uplift uplift_mpi *.o *.mod encflow encflow_mpi a.out Screen*.log z.txt submarine.txt

cleanref:
	rm -rf reference

.PHONY: all links inputs inputs_bm clean cleanref FORCE
