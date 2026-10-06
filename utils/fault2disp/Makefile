# ENCflow/utils/fault2disp/Makefile
#   断層パラメータ → 地盤変位のスナップショット表(fn_bedmotion の入力)。
#   地理参照(hdr / GeoTIFF)を本体と同じ部品で読むため libencflow.a を
#   リンクする(utils/rerecord と同じ型。FRT / FFLAGS は make.inc)
TOPDIR	= ../..
include $(TOPDIR)/make.inc

BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
LIB	= $(SRCDIR)/libencflow.a

all: fault2disp

fault2disp: fault2disp.o $(LIB)
	$(FRT) -o $@ $(FFLAGS) fault2disp.o $(LIB) $(LDFLAGS)

fault2disp.o: fault2disp.f90 $(LIB)
	$(FRT) -c $(FFLAGS) -I$(SRCDIR) fault2disp.f90

$(LIB): FORCE
	$(MAKE) -C $(SRCDIR) libencflow.a

FORCE:

check: fault2disp
	./fault2disp -check

clean:
	rm -f fault2disp *.o *.mod

install: fault2disp
	mkdir -p $(BINDIR)
	cp -f fault2disp $(BINDIR)

.PHONY: all check clean install FORCE
