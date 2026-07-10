# ENCflow/src/Makefile
#   コンパイラ設定は ../make.inc に集約
include ../make.inc

# ---------------------------------------------------------------
# main.o 以外の全オブジェクト → libencflow.a に格納
# (utils/ 以下のユーティリティはこのライブラリをリンクする)
# ---------------------------------------------------------------
LIBOBJS	= m_main.o m_sysparam.o m_geoinfo.o m_precip.o m_tide.o m_boundary.o \
	  m_state.o m_record.o m_swflow.o m_swflow_enc.o m_swflow_stg.o \
	  m_swflow_enc0.o \
	  list_sysparam.o list_geoinfo.o list_precip.o \
	  list_initial.o list_record.o list_tide.o list_boundary.o list_enc.o \
	  m_ffactor.o user_geoinfo.o user_initial.o sysdep_util.o m_fileio.o m_util.o

OBJS	= main.o $(LIBOBJS)

LIB	= libencflow.a

BINDIR	= ../bin

all: a.out $(LIB)

a.out: $(OBJS)
	$(FRT) -o $@ $(FFLAGS) $(LDFLAGS) $(OBJS)

$(LIB): $(LIBOBJS)
	$(AR) $(ARFLAGS) $@ $(LIBOBJS)

# ---------------------------------------------------------------
# モジュール依存関係
# ---------------------------------------------------------------
main.o: m_main.o
m_main.o: m_sysparam.o m_geoinfo.o m_precip.o m_tide.o m_boundary.o m_state.o \
	m_record.o m_swflow.o m_fileio.o sysdep_util.o
m_sysparam.o: list_sysparam.o m_util.o
m_geoinfo.o: m_sysparam.o list_geoinfo.o m_fileio.o
m_precip.o: m_sysparam.o list_precip.o m_state.o m_geoinfo.o m_util.o m_fileio.o
m_tide.o: m_sysparam.o list_tide.o m_geoinfo.o
m_boundary.o: m_sysparam.o m_geoinfo.o m_state.o list_boundary.o
m_state.o: m_sysparam.o m_geoinfo.o list_initial.o
m_record.o: m_sysparam.o list_record.o m_geoinfo.o m_state.o
m_swflow.o: m_sysparam.o m_geoinfo.o m_boundary.o m_state.o m_swflow_enc.o m_swflow_stg.o m_swflow_enc0.o
m_swflow_enc.o: m_sysparam.o list_enc.o m_geoinfo.o m_boundary.o m_precip.o m_state.o m_ffactor.o
m_swflow_enc0.o: m_sysparam.o list_enc.o m_geoinfo.o m_boundary.o m_precip.o m_state.o m_ffactor.o
m_swflow_stg.o: m_sysparam.o m_geoinfo.o m_precip.o m_boundary.o m_state.o
list_sysparam.o:
list_geoinfo.o: m_sysparam.o
list_precip.o: m_sysparam.o
list_tide.o: m_sysparam.o
list_initial.o: m_sysparam.o
list_record.o: m_sysparam.o
list_boundary.o: m_sysparam.o
list_enc.o: m_sysparam.o
user_geoinfo.o: m_sysparam.o m_geoinfo.o
user_initial.o: m_sysparam.o m_state.o m_geoinfo.o
m_fileio.o: m_sysparam.o sysdep_util.o
m_ffactor.o:
m_util.o:
sysdep_util.o: m_sysparam.o


.SUFFIXES:
.SUFFIXES: .o .f90
.f90.o:
	$(FRT) -c $(FFLAGS) $<


clean:
	rm -f *.o *.mod *.smod a.out $(LIB) gmon.out *__genmod.*

install: a.out
	mkdir -p $(BINDIR)
	cp -f a.out $(BINDIR)

.PHONY: all clean install
