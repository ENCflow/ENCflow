# ENCflow/utils/fault2disp/Makefile
#   断層パラメータ → 地盤変位のスナップショット表(fn_bedmotion の入力)。
#   src のモジュールを使わない独立ユーティリティ(FRT_UTIL / FFLAGS_UTIL)
TOPDIR	= ../..
include $(TOPDIR)/make.inc

BINDIR	= $(TOPDIR)/bin
PROGS	= fault2disp

all: $(PROGS)

fault2disp: fault2disp.o
	$(FRT_UTIL) -o $@ $(FFLAGS_UTIL) fault2disp.o $(LDFLAGS)

.SUFFIXES:
.SUFFIXES: .o .f90
.f90.o:
	$(FRT_UTIL) -c $(FFLAGS_UTIL) $<

check: fault2disp
	./fault2disp -check

clean:
	rm -f *.o *.mod gmon.out $(PROGS)

install: $(PROGS)
	mkdir -p $(BINDIR)
	cp -f $(PROGS) $(BINDIR)

.PHONY: all check clean install
