# ENCflow/misc/rmdepress_river/Makefile
#   src のモジュール(libencflow.a と .mod)を利用するユーティリティ
TOPDIR	= ../..
include $(TOPDIR)/make.inc

BINDIR	= $(TOPDIR)/bin

SRCDIR	= $(TOPDIR)/src
LIB	= $(SRCDIR)/libencflow.a

all: rmdepress_river

rmdepress_river: rmdepress_river.o $(LIB)
	$(FRT) -o $@ $(FFLAGS) $(LDFLAGS) rmdepress_river.o $(LIB)

rmdepress_river.o: rmdepress_river.f90 $(LIB)
	$(FRT) -c $(FFLAGS) -I$(SRCDIR) rmdepress_river.f90

$(LIB): FORCE
	$(MAKE) -C $(SRCDIR) libencflow.a

FORCE:

clean:
	rm -f rmdepress_river *.o *.mod

install: rmdepress_river
	mkdir -p $(BINDIR)
	cp -f rmdepress_river $(BINDIR)

.PHONY: all clean install FORCE
