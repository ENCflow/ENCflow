# ENCflow/misc/calc_catchmentarea/Makefile
#   src のモジュールを使わない独立ユーティリティ群。
#   コンパイラは make.inc で一元管理し、フラグは FFLAGS_UTIL
#   (-r8 なし)を使う。
TOPDIR	= ../..
include $(TOPDIR)/make.inc

BINDIR	= $(TOPDIR)/bin

PROGS	= modify_river

all: $(PROGS)

modify_river: modify_river.o
	$(FRT) -o $@ $(FFLAGS_UTIL) $(LDFLAGS) modify_river.o


.SUFFIXES:
.SUFFIXES: .o .f90
.f90.o:
	$(FRT) -c $(FFLAGS_UTIL) $<


clean:
	rm -f *.o *.mod *.smod gmon.out *__genmod.* $(PROGS)

install: $(PROGS)
	mkdir -p $(BINDIR)
	cp -f $(PROGS) $(BINDIR)


.PHONY: all clean install
