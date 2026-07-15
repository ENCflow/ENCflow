# =====================================================================
# ENCflow 共通コンパイラ設定
#   src/ と utils/ 以下の各 Makefile から include する。
#
#   FRT, FFLAGS : メインプログラムおよび src のモジュールを使う
#                 ユーティリティ用(-r8 必須。.mod 互換のため
#                 src と utils/rerecord 等で必ず同一にすること)
#   FRT_UTIL, FFLAGS_UTIL : src のモジュールを使わない独立ユーティリティ用
#                 (calc_catchmentarea, modify_* など。-r8 なし)
# =====================================================================

# ---------------------------------------------------------------
# 並列モード切り替え
#   serial : 従来の OpenMP 版(m_parallel_serial.f90 を使用)
#   mpi    : MPI+OpenMP ハイブリッド版(m_parallel_mpi.f90 を使用)
#   ここを書き換えるほか、コマンドラインから
#       make MODE=mpi
#   でも上書きできる(トップレベル Makefile 経由でも全体に伝播する)
# ---------------------------------------------------------------
MODE	= serial
#MODE	= mpi

# ---------------------------------------------------------------
# コンパイラ本体(FC)と MPI ラッパー(FC_MPI)
#   使う組をコメント切り替え。FRT は MODE に応じて自動決定される。
# ---------------------------------------------------------------
FC	= ifx
FC_MPI	= mpiifx
FFLAGS	= -g -fopenmp -warn all -fpe0 -O3 -ipo -fp-model fast -r8
#FFLAGS	= -g -O0 -traceback -check all -warn all -fpe0 -r8
#LDFLAGS =

#FC	= gfortran
#FC_MPI	= mpifort
#FC_MPI	= mpifort.mpich
#FC_MPI	= mpifort.openmpi
#FFLAGS	= -g -fopenmp -Ofast -Wall -ffpe-trap=zero,overflow -fdefault-real-8 -fdefault-double-8
#FFLAGS	= -g -fopenmp -Ofast -Wall -ffpe-trap=zero,overflow -fdefault-real-8 -fdefault-double-8 -fcheck=all -fbacktrace
#FFLAGS	= -g -Og -fcheck=all -fbacktrace -Wall -ffpe-trap=invalid,zero,overflow -fdefault-real-8 -fdefault-double-8 -Wno-conversion -finit-real=snan -finit-integer=-88888888
#LDFLAGS =

#FC	= nvfortran
#FC_MPI	= mpif90
#FFLAGS	= -gopt -mp=multicore -Ofast -Minform=inform -Ktrap=divz,ovf -Mr8
#FFLAGS	= -gopt -mp=multicore -Ofast -Minform=inform -Ktrap=divz,ovf -Mr8 -Mbounds -Mchkptr -Mchkstk 
#LDFLAGS =

#FC	= flang-20
#FC_MPI	= mpifort
#FFLAGS	= -g -O3 -ffast-math -Werror -fdefault-real-8
#LDFLAGS =

# MODE に応じて実際に使うコンパイラを決定
ifeq ($(MODE),mpi)
FRT	= $(FC_MPI)
else ifeq ($(MODE),serial)
FRT	= $(FC)
else
$(error MODE は serial か mpi を指定してください (現在: '$(MODE)'))
endif

# ---------------------------------------------------------------
# 独立ユーティリティ用(MODE の影響を受けず常に逐次ビルド)
# ---------------------------------------------------------------
#FRT_UTIL	= ifx
#FFLAGS_UTIL	= -g -O2 -warn all -fpe0
#FFLAGS_UTIL	= -g -O0 -traceback -check all -warn all -fpe0

FRT_UTIL	= gfortran
FFLAGS_UTIL	= -g -O2 -Wall -ffpe-trap=invalid,zero,overflow
#FFLAGS_UTIL	= -g -Og -fcheck=all -Wall -ffpe-trap=invalid,zero,overflow -Wno-conversion

#FRT_UTIL	= nvfortran
#FFLAGS_UTIL	= -g -O2 -Minform=inform -Ktrap=fp

#FRT_UTIL	= flang-20
#FFLAGS_UTIL	= -g -O2 -Werror

# ---------------------------------------------------------------
# 静的ライブラリ作成コマンド
#   ifx の -ipo は LLVM LTO であり .o がビットコードになるため、
#   システムの ar ではシンボル索引を作れない。oneAPI 同梱の
#   llvm-ar(ifx と同じ bin の一段下 bin/compiler/ にある)を使う。
#   mpiifx も実体は ifx なので同じ扱い(findstring で両方に一致)。
# ---------------------------------------------------------------
ifneq (,$(findstring ifx,$(FC)))
IFXBIN	:= $(dir $(shell which ifx))
AR	= $(IFXBIN)compiler/llvm-ar
else
AR	= ar
endif
ARFLAGS	= rcs
