# ENCflow/utils/modify_sealand/Makefile
#   src のモジュールを使わない独立ユーティリティ群。
#   コンパイラは make.inc で一元管理し、フラグは FFLAGS_UTIL
#   (-r8 なし)を使う。
TOPDIR	= ../..
include $(TOPDIR)/make.inc

BINDIR	= $(TOPDIR)/bin

PROGS	= modify_sealand

all: $(PROGS)

modify_sealand: modify_sealand.o
	$(FRT_UTIL) -o $@ $(FFLAGS_UTIL) $(LDFLAGS) modify_sealand.o


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
