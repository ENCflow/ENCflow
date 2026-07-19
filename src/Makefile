# ENCflow/src/Makefile
#   コンパイラ設定・並列モード(MODE)は ../make.inc に集約
include ../make.inc

# ---------------------------------------------------------------
# 並列層の実装選択
#   MODE=serial → m_parallel_serial.o
#   MODE=mpi    → m_parallel_mpi.o
#   どちらも同名モジュール m_parallel を提供する(同一インターフェース)
# ---------------------------------------------------------------
PAR_OBJ	= m_parallel_$(MODE).o

# ---------------------------------------------------------------
# main.o 以外の全オブジェクト → libencflow.a に格納
# (utils/ 以下のユーティリティはこのライブラリをリンクする)
# ---------------------------------------------------------------
LIBOBJS	= m_main.o m_sysparam.o m_geoinfo.o m_precip.o m_tide.o m_boundary.o \
	  m_state.o m_record.o m_swflow.o m_swflow_enc.o m_swflow_stg.o \
	  m_swflow_dev.o $(PAR_OBJ) \
	  list_sysparam.o list_geoinfo.o list_precip.o \
	  list_initial.o list_record.o list_tide.o list_boundary.o list_enc.o \
	  m_ffactor.o user_geoinfo.o user_initial.o sysdep_util.o m_fileio.o m_util.o

OBJS	= main.o $(LIBOBJS)

LIB	= libencflow.a

BINDIR	= ../bin

all: a.out $(LIB)

a.out: $(OBJS)
	$(FRT) -o $@ $(FFLAGS) $(OBJS) $(LDFLAGS)

$(LIB): $(LIBOBJS)
	$(AR) $(ARFLAGS) $@ $(LIBOBJS)

# ---------------------------------------------------------------
# MODE 切り替え時の安全装置
#   前回ビルドと MODE が変わっていたら全オブジェクトを作り直す。
#   (serial/mpi の .o や m_parallel.mod の混在リンクを防ぐ)
# ---------------------------------------------------------------
MODESTAMP	= .mode_$(MODE)

$(OBJS): $(MODESTAMP) ../make.inc

$(MODESTAMP):
	@rm -f *.o *.mod *.smod .mode_*
	@touch $@

# ---------------------------------------------------------------
# モジュール依存関係
# ---------------------------------------------------------------
main.o: m_main.o
m_main.o: m_sysparam.o m_geoinfo.o m_precip.o m_tide.o m_boundary.o m_state.o \
	m_record.o m_swflow.o m_fileio.o sysdep_util.o $(PAR_OBJ)
m_sysparam.o: list_sysparam.o m_util.o $(PAR_OBJ)
m_geoinfo.o: m_sysparam.o list_geoinfo.o m_fileio.o $(PAR_OBJ)
m_precip.o: m_sysparam.o list_precip.o m_state.o m_geoinfo.o m_util.o m_fileio.o $(PAR_OBJ)
m_tide.o: m_sysparam.o list_tide.o m_geoinfo.o $(PAR_OBJ)
m_boundary.o: m_sysparam.o m_geoinfo.o m_state.o list_boundary.o $(PAR_OBJ)
m_state.o: m_sysparam.o m_geoinfo.o list_initial.o
m_record.o: m_sysparam.o list_record.o m_geoinfo.o m_state.o $(PAR_OBJ)
m_swflow.o: m_sysparam.o m_geoinfo.o m_boundary.o m_state.o \
	m_swflow_enc.o m_swflow_stg.o m_swflow_dev.o $(PAR_OBJ)
m_swflow_enc.o: m_sysparam.o list_enc.o m_geoinfo.o m_boundary.o \
	m_precip.o m_state.o m_ffactor.o $(PAR_OBJ)
m_swflow_dev.o: m_sysparam.o list_enc.o m_geoinfo.o m_boundary.o \
	m_precip.o m_state.o m_ffactor.o $(PAR_OBJ)
m_swflow_stg.o: m_sysparam.o m_geoinfo.o m_precip.o m_boundary.o m_state.o
list_sysparam.o: $(PAR_OBJ)
list_geoinfo.o: m_sysparam.o $(PAR_OBJ)
list_precip.o: m_sysparam.o $(PAR_OBJ)
list_tide.o: m_sysparam.o $(PAR_OBJ)
list_initial.o: m_sysparam.o $(PAR_OBJ)
list_record.o: m_sysparam.o $(PAR_OBJ)
list_boundary.o: m_sysparam.o $(PAR_OBJ)
list_enc.o: m_sysparam.o $(PAR_OBJ)
user_geoinfo.o: m_sysparam.o m_geoinfo.o
user_initial.o: m_sysparam.o m_state.o m_geoinfo.o
m_fileio.o: m_sysparam.o sysdep_util.o
m_ffactor.o: $(PAR_OBJ)
m_util.o: $(PAR_OBJ)
sysdep_util.o: m_sysparam.o $(PAR_OBJ)

# 並列層は今のところ他モジュールに依存しない
#   通信を使うモジュールが増えたら「m_xxx.o: ... $(PAR_OBJ)」を追記すること
$(PAR_OBJ):


.SUFFIXES:
.SUFFIXES: .o .f90
.f90.o:
	$(FRT) -c $(FFLAGS) $<


clean:
	rm -f *.o *.mod *.smod a.out $(LIB) gmon.out *__genmod.* .mode_*

install: a.out
	mkdir -p $(BINDIR)
	cp -f a.out $(BINDIR)

.PHONY: all clean install
