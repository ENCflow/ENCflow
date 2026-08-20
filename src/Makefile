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
	  m_boundary_structure.o \
	  m_geomorph.o m_geomorph_creep.o m_geomorph_fluvial.o m_geomorph_suspend.o \
	  m_geomorph_wash.o m_geomorph_splash.o m_geomorph_debris.o \
	  m_gwflow.o m_gwflow_bucket.o m_gwflow_greenampt.o \
	  m_gwflow_lateral.o m_gwflow_layer2.o m_gwflow_conduit.o m_gwflow_pump.o m_gwflow_frost.o m_saltwater.o m_evap.o m_meteo.o m_wq.o m_snow.o m_glacier.o \
	  m_intercept.o m_intercept_fixed.o m_intercept_initloss.o \
	  m_state.o m_record.o m_swflow.o m_swflow_enc.o m_swflow_enc_adv.o m_swflow_enc_bc.o \
	  m_swflow_enc_channel.o m_swflow_enc_diff.o \
	  m_output.o m_swflow_stg.o \
	  $(PAR_OBJ) \
	  list_sysparam.o list_geoinfo.o list_channel.o list_precip.o list_geomorph.o list_gwflow.o \
	  list_intercept.o list_evap.o list_meteo.o list_wq.o list_snow.o list_glacier.o \
	  list_initial.o list_record.o list_tide.o list_boundary.o list_structure.o list_enc.o \
	  m_ffactor.o user_geoinfo.o user_initial.o m_sysdep_util.o m_fileio.o m_georef.o \
	  m_geotiff.o m_geotiff_codec.o m_geotiff_inflate.o m_util.o

OBJS	= main.o $(LIBOBJS)

LIB	= libencflow.a

# ---------------------------------------------------------------
# 実行ファイル名(§3)
#   serial(OpenMP)版 = encflow、MPI ハイブリッド版 = encflow_mpi。
#   別名にするのは、bin/ で両モードを共存させるためと、
#   「serial バイナリを mpirun で起動する」事故(全プロセスが独立に
#   nproc=1 で走り気づきにくい)を名前の段階で防ぐため。
# ---------------------------------------------------------------
ifeq ($(MODE),mpi)
TARGET	= encflow_mpi
else
TARGET	= encflow
endif

BINDIR	= ../bin

all: $(TARGET) $(LIB)

$(TARGET): $(OBJS)
	$(FRT) -o $@ $(FFLAGS) $(OBJS) $(LDFLAGS)

$(LIB): $(LIBOBJS)
	$(AR) $(ARFLAGS) $@ $(LIBOBJS)

# ---------------------------------------------------------------
# MODE / MPI 実装 / 実数精度(PREC)切り替え時の安全装置
#   前回ビルドと MODE・MPI 実装(module 環境)・PREC のいずれかが
#   変わっていたら全オブジェクトを作り直す。
#   (serial/mpi の .o、m_parallel.mod、異なる MPI の mpi.mod、
#    異なる実数サイズの .o/.mod の混在リンクを防ぐ)
#   MPIID: MPI ラッパーの -show 出力(実装ごとに異なる)のハッシュ。
#          MPI モードでのみ計算する。serial ではスタンプにハッシュを
#          付けない — 非ラッパーの -show は「失敗して空」とは限らず、
#          nvfortran は -show を認識し、出力に一時ファイル名を含む
#          (毎回変化)ため、serial でハッシュを取ると呼び出しごとに
#          スタンプ名が変わり全再ビルドが繰り返される。
# ---------------------------------------------------------------
ifeq ($(MODE),mpi)
MPIID	:= _$(shell $(FRT) -show 2>/dev/null | md5sum | cut -c1-8)
else
MPIID	:=
endif
MODESTAMP	= .mode_$(MODE)_$(MPIID)_$(PREC)

$(OBJS): $(MODESTAMP) ../make.inc

$(MODESTAMP):
	@rm -f *.o *.mod *.smod .mode_*
	@touch $@

# ---------------------------------------------------------------
# モジュール依存関係
# ---------------------------------------------------------------
main.o: m_main.o
m_main.o: m_sysparam.o m_geoinfo.o m_precip.o m_tide.o m_boundary.o m_state.o m_geomorph.o m_gwflow.o \
	m_saltwater.o \
	m_intercept.o m_evap.o m_meteo.o m_wq.o m_snow.o m_glacier.o m_record.o m_swflow.o m_output.o m_fileio.o m_sysdep_util.o $(PAR_OBJ)
m_sysparam.o: list_sysparam.o m_fileio.o m_util.o $(PAR_OBJ)
m_geoinfo.o: m_sysparam.o list_geoinfo.o list_channel.o m_fileio.o m_georef.o m_geotiff.o m_util.o $(PAR_OBJ)
m_precip.o: m_sysparam.o list_precip.o m_state.o m_geoinfo.o m_meteo.o m_util.o m_fileio.o $(PAR_OBJ)
m_geomorph.o: m_sysparam.o list_geomorph.o m_state.o m_geoinfo.o m_util.o $(PAR_OBJ)
m_geomorph_creep.o: m_geomorph.o $(PAR_OBJ)
m_geomorph_fluvial.o: m_geomorph.o m_swflow_enc.o $(PAR_OBJ)
m_geomorph_suspend.o: m_geomorph.o $(PAR_OBJ)
m_geomorph_wash.o: m_geomorph.o $(PAR_OBJ)
m_geomorph_splash.o: m_geomorph.o $(PAR_OBJ)
m_geomorph_debris.o: m_geomorph.o m_swflow_enc.o $(PAR_OBJ)
list_geomorph.o: m_sysparam.o $(PAR_OBJ)
m_gwflow.o: m_sysparam.o list_gwflow.o m_state.o m_geoinfo.o m_gwflow_bucket.o \
	m_gwflow_greenampt.o m_gwflow_lateral.o m_gwflow_layer2.o m_gwflow_conduit.o \
	m_gwflow_pump.o m_gwflow_frost.o m_meteo.o m_util.o $(PAR_OBJ)
m_gwflow_frost.o: m_sysparam.o m_state.o m_geoinfo.o m_meteo.o m_fileio.o \
	m_sysdep_util.o $(PAR_OBJ)
m_gwflow_pump.o: m_sysparam.o m_state.o m_geoinfo.o m_boundary.o m_gwflow_layer2.o \
	m_util.o $(PAR_OBJ)
m_gwflow_conduit.o: m_sysparam.o m_state.o m_geoinfo.o m_gwflow_lateral.o \
	m_gwflow_layer2.o m_fileio.o m_sysdep_util.o $(PAR_OBJ)
m_saltwater.o: m_sysparam.o m_state.o m_geoinfo.o m_gwflow_lateral.o \
	m_fileio.o m_sysdep_util.o $(PAR_OBJ)
m_gwflow_layer2.o: m_sysparam.o m_state.o m_geoinfo.o m_gwflow_lateral.o \
	m_fileio.o m_sysdep_util.o $(PAR_OBJ)
m_gwflow_bucket.o: m_sysparam.o m_state.o m_geoinfo.o $(PAR_OBJ)
m_gwflow_greenampt.o: m_sysparam.o m_state.o m_geoinfo.o $(PAR_OBJ)
m_gwflow_lateral.o: m_sysparam.o m_state.o m_geoinfo.o $(PAR_OBJ)
list_gwflow.o: m_sysparam.o $(PAR_OBJ)
m_evap.o: m_sysparam.o m_geoinfo.o m_state.o m_boundary.o m_intercept.o m_meteo.o \
	list_evap.o m_util.o $(PAR_OBJ)
list_evap.o: m_sysparam.o $(PAR_OBJ)
m_meteo.o: m_sysparam.o m_geoinfo.o m_state.o m_boundary.o list_meteo.o m_fileio.o \
	m_util.o $(PAR_OBJ)
list_meteo.o: m_sysparam.o $(PAR_OBJ)
m_wq.o: m_sysparam.o m_geoinfo.o m_state.o m_boundary.o m_swflow_enc.o list_wq.o \
	m_fileio.o m_sysdep_util.o m_util.o $(PAR_OBJ)
list_wq.o: m_sysparam.o $(PAR_OBJ)
m_snow.o: m_sysparam.o m_geoinfo.o m_state.o m_meteo.o m_swflow_enc.o list_snow.o \
	m_fileio.o m_sysdep_util.o $(PAR_OBJ)
list_snow.o: m_sysparam.o $(PAR_OBJ)
m_glacier.o: m_sysparam.o m_geoinfo.o m_state.o m_meteo.o m_swflow_enc.o list_glacier.o \
	m_fileio.o m_sysdep_util.o m_util.o $(PAR_OBJ)
list_glacier.o: m_sysparam.o $(PAR_OBJ)
m_intercept.o: m_sysparam.o list_intercept.o m_state.o m_geoinfo.o m_intercept_fixed.o \
	m_intercept_initloss.o m_util.o $(PAR_OBJ)
m_intercept_fixed.o: m_sysparam.o m_state.o m_geoinfo.o m_fileio.o $(PAR_OBJ)
m_intercept_initloss.o: m_sysparam.o m_state.o m_geoinfo.o m_fileio.o m_sysdep_util.o $(PAR_OBJ)
list_intercept.o: m_sysparam.o $(PAR_OBJ)
m_tide.o: m_sysparam.o list_tide.o m_geoinfo.o m_state.o m_fileio.o m_util.o $(PAR_OBJ)
m_boundary.o: m_sysparam.o m_geoinfo.o m_state.o list_boundary.o $(PAR_OBJ)
m_boundary_structure.o: m_boundary.o list_structure.o m_util.o $(PAR_OBJ)
m_state.o: m_sysparam.o m_geoinfo.o list_initial.o m_util.o m_sysdep_util.o m_fileio.o
m_record.o: m_sysparam.o list_record.o m_geoinfo.o m_state.o m_util.o m_sysdep_util.o $(PAR_OBJ)
m_swflow.o: m_sysparam.o m_geoinfo.o m_boundary.o m_state.o \
	m_swflow_enc.o m_swflow_stg.o $(PAR_OBJ)
m_swflow_enc.o: m_sysparam.o list_enc.o list_channel.o m_geoinfo.o m_boundary.o \
	m_precip.o m_state.o m_ffactor.o m_sysdep_util.o m_fileio.o $(PAR_OBJ)
m_swflow_stg.o: m_sysparam.o m_geoinfo.o m_precip.o m_boundary.o m_state.o $(PAR_OBJ)
m_swflow_enc_adv.o: m_swflow_enc.o m_state.o
m_swflow_enc_diff.o: m_swflow_enc.o m_state.o $(PAR_OBJ)
m_swflow_enc_bc.o: m_swflow_enc.o m_boundary.o m_state.o $(PAR_OBJ)
m_swflow_enc_channel.o: m_swflow_enc.o m_sysparam.o m_geoinfo.o m_state.o \
	list_channel.o m_util.o m_boundary.o $(PAR_OBJ)
list_sysparam.o: $(PAR_OBJ)
list_geoinfo.o: m_sysparam.o $(PAR_OBJ)
list_channel.o: m_sysparam.o $(PAR_OBJ)
list_precip.o: m_sysparam.o $(PAR_OBJ)
list_tide.o: m_sysparam.o $(PAR_OBJ)
list_initial.o: m_sysparam.o $(PAR_OBJ)
list_record.o: m_sysparam.o $(PAR_OBJ)
list_boundary.o: m_sysparam.o $(PAR_OBJ)
list_structure.o: m_sysparam.o $(PAR_OBJ)
list_enc.o: m_sysparam.o $(PAR_OBJ)
user_geoinfo.o: m_sysparam.o m_geoinfo.o
user_initial.o: m_sysparam.o m_state.o m_geoinfo.o
m_output.o: m_sysparam.o m_geoinfo.o m_state.o m_fileio.o m_georef.o $(PAR_OBJ)
m_fileio.o: m_geotiff.o m_georef.o m_util.o $(PAR_OBJ)
m_georef.o: m_util.o $(PAR_OBJ)
m_geotiff.o: m_geotiff_codec.o m_geotiff_inflate.o
m_ffactor.o: m_util.o $(PAR_OBJ)
m_util.o: $(PAR_OBJ)
m_sysdep_util.o: $(PAR_OBJ)

# 並列層は今のところ他モジュールに依存しない
#   通信を使うモジュールが増えたら「m_xxx.o: ... $(PAR_OBJ)」を追記すること
$(PAR_OBJ):


.SUFFIXES:
.SUFFIXES: .o .f90
.f90.o:
	$(FRT) -c $(FFLAGS) $<


clean:
	rm -f *.o *.mod *.smod encflow encflow_mpi a.out $(LIB) gmon.out *__genmod.* .mode_*

install: all
	mkdir -p $(BINDIR)
	cp -f $(TARGET) $(BINDIR)

# Check_mode.sh から「現環境での期待スタンプ名」を問い合わせるための
# ターゲット(make -s print-stamp MODE=... で使う)
print-stamp:
	@echo $(MODESTAMP)

.PHONY: all clean install print-stamp
