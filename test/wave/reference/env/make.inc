# =====================================================================
# ENCflow 共通コンパイラ設定
#   src/ と utils/ 以下の各 Makefile から include する。
#
#   FRT, FFLAGS : メインプログラムおよび src のモジュールを使う
#                 ユーティリティ用(-r8 必須。.mod 互換のため
#                 src と utils/rerecord 等で必ず同一にすること)
#   FRT_UTIL, FFLAGS_UTIL : src のモジュールを使わない独立ユーティリティ用
#                 (calc_catchmentarea, modify_* など。-r8 なし)
#
#   注意: コンパイラやフラグ(特に -ipo/-flto の有無)を変更したら
#         必ず make clean すること。
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
# Intel oneAPI (-ipo: リンク時に全体最適化。アーカイバは oneAPI の llvm-ar)
FC	= ifx
FC_MPI	= mpiifx
FFLAGS	= -g -fopenmp -warn all -fpe0 -Ofast -xHost -ipo -r8
#FFLAGS	= -g -O0 -traceback -check all -warn all -fpe0 -r8
#LDFLAGS =

# GNU Fortran (with MPICH or OpenMPI)
#   -flto=auto: リンク時最適化(-ipo 相当)。auto で LTO 処理を並列化。
#   アーカイバは gcc-ar(LTO プラグイン対応。llvm-ar は不可)
#FC	= gfortran
#FC_MPI	= mpifort
#FFLAGS	= -g -fopenmp -Ofast -march=native -flto=auto -Wall -ffpe-trap=zero,overflow -fdefault-real-8 -fdefault-double-8
#FFLAGS	= -g -fopenmp -Ofast -Wall -ffpe-trap=zero,overflow -fdefault-real-8 -fdefault-double-8 -fcheck=all -fbacktrace
#FFLAGS	= -g -Og -fcheck=all -fbacktrace -Wall -ffpe-trap=invalid,zero,overflow -fdefault-real-8 -fdefault-double-8 -Wno-conversion -finit-real=snan -finit-integer=-88888888
#LDFLAGS =

# NVIDIA HPC SDK (-ipo/-flto 相当なし: -Mipa は 23.3 で無効化済み)
#FC	= nvfortran
#FC_MPI	= mpif90
#FFLAGS	= -gopt -mp=multicore -Ofast -Minform=inform -Ktrap=divz,ovf -Mr8
#FFLAGS	= -gopt -mp=multicore -Ofast -Minform=inform -Ktrap=divz,ovf -Mr8 -Mbounds -Mchkptr -Mchkstk 
#LDFLAGS =

# AMD AOCC (with MPI build by AOCC)
#   -flto: リンク時最適化(-ipo 相当)。アーカイバは AOCC 同梱の llvm-ar
#FC	= flang
#FC_MPI	= mpifort
#FFLAGS	= -g -fopenmp -Ofast -march=native -flto -Wall -r8 -ffast-math -Mcache_align
#LDFLAGS =

# LLVM Flang
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
#   LTO 不要のため -flto は付けない
# ---------------------------------------------------------------
#FRT_UTIL	= ifx
#FFLAGS_UTIL	= -g -O2 -warn all -fpe0
#FFLAGS_UTIL	= -g -O0 -traceback -check all -warn all -fpe0

FRT_UTIL	= gfortran
FFLAGS_UTIL	= -g -O2 -Wall -ffpe-trap=invalid,zero,overflow
#FFLAGS_UTIL	= -g -Og -fcheck=all -Wall -ffpe-trap=invalid,zero,overflow -Wno-conversion

#FRT_UTIL	= nvfortran
#FFLAGS_UTIL	= -g -O2 -Minform=inform -Ktrap=fp

#FRT_UTIL	= flang
#FFLAGS_UTIL	= -g -O2 -march=native

#FRT_UTIL	= flang-20
#FFLAGS_UTIL	= -g -O2 -Werror

# ---------------------------------------------------------------
# 静的ライブラリ作成コマンド(コンパイラと LTO の有無で自動選択)
#
#   ifx の -ipo および flang 系の -flto は .o が LLVM ビットコードに、
#   gfortran の -flto は GIMPLE バイトコードになるため、いずれも
#   システムの ar ではシンボル索引を作れない。対応表:
#     ifx (+-ipo)        → oneAPI 同梱の llvm-ar (bin/compiler/ 下)
#     gfortran + -flto   → gcc-ar (LTO プラグインを自動ロードする
#                          ラッパー。llvm-ar は不可)
#     flang 系 + -flto   → llvm-ar (AOCC なら module load で PATH に入る)
#     それ以外           → ar
#   mpiifx/mpifort 等のラッパー使用時も判定は FC 側で行う。
# ---------------------------------------------------------------
ifneq (,$(findstring ifx,$(FC)))
IFXBIN	:= $(dir $(shell which ifx))
AR	= $(IFXBIN)compiler/llvm-ar
else ifneq (,$(findstring -flto,$(FFLAGS)))
  ifeq ($(FC),gfortran)
AR	= gcc-ar
  else
AR	= llvm-ar
  endif
else
AR	= ar
endif
ARFLAGS	= rcs
