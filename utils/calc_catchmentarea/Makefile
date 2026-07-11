# ENCflow/utils/calc_catchmentarea/Makefile
#   src のモジュールを使わない独立ユーティリティ群。
#   コンパイラは make.inc で一元管理し、フラグは FFLAGS_UTIL
#   (-r8 なし)を使う。
TOPDIR	= ../..
include $(TOPDIR)/make.inc

BINDIR	= $(TOPDIR)/bin

PROGS	= mkdowndir chkdowndir calcarea pickuparea

all: $(PROGS)

mkdowndir: mkdowndir.o
	$(FRT_UTIL) -o $@ $(FFLAGS_UTIL) mkdowndir.o $(LDFLAGS)

chkdowndir: chkdowndir.o
	$(FRT_UTIL) -o $@ $(FFLAGS_UTIL) chkdowndir.o $(LDFLAGS)

calcarea: calcarea.o
	$(FRT_UTIL) -o $@ $(FFLAGS_UTIL) calcarea.o $(LDFLAGS)

pickuparea: pickuparea.o
	$(FRT_UTIL) -o $@ $(FFLAGS_UTIL) pickuparea.o $(LDFLAGS)


.SUFFIXES:
.SUFFIXES: .o .f90
.f90.o:
	$(FRT_UTIL) -c $(FFLAGS_UTIL) $<


clean:
	rm -f *.o *.mod *.smod gmon.out *__genmod.* $(PROGS)

install: $(PROGS)
	mkdir -p $(BINDIR)
	cp -f $(PROGS) $(BINDIR)


.PHONY: all clean install
