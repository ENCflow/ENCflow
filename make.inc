# =====================================================================
# ENCflow 共通コンパイラ設定
#   src/ と misc/ 以下の各 Makefile から include する。
#
#   FRT, FFLAGS : メインプログラムおよび src のモジュールを使う
#                 ユーティリティ用(-r8 必須。.mod 互換のため
#                 src と misc/rerecord 等で必ず同一にすること)
#   FRT_UTIL, FFLAGS_UTIL : src のモジュールを使わない独立ユーティリティ用
#                 (calc_catchmentarea, modify_* など。-r8 なし)
# =====================================================================

FRT	= ifx
FFLAGS	= -g -fopenmp -warn all -fpe0 -O3 -ipo -fp-model fast -r8
#FFLAGS	= -g -O0 -traceback -check all -warn all -fpe0 -r8
#LDFLAGS =

FRT_UTIL	= ifx
FFLAGS_UTIL	= -g -O2 -warn all -fpe0
#FFLAGS_UTIL	= -g -O0 -traceback -check all -warn all -fpe0
#LDFLAGS =

#FRT	= gfortran
#FFLAGS	= -g -fopenmp -Ofast -Wall -ffpe-trap=zero,overflow -fdefault-real-8 -fdefault-double-8
#FFLAGS	= -g -Og -fcheck=all -Wall -ffpe-trap=invalid,zero,overflow -fdefault-real-8 -fdefault-double-8 -Wno-conversion
#LDFLAGS =

#FRT_UTIL	= gfortran
#FFLAGS_UTIL	= -g -O2 -Wall -ffpe-trap=invalid,zero,overflow
#FFLAGS_UTIL	= -g -Og -fcheck=all -Wall -ffpe-trap=invalid,zero,overflow -Wno-conversion
#LDFLAGS =

#FRT	= nvfortran
#FFLAGS	= -g -mp=multicore -Ofast -Minform=inform -Ktrap=fp -Mr8
#LDFLAGS =

#FRT_UTIL	= nvfortran
#FFLAGS_UTIL	= -g -O2 -Minform=inform -Ktrap=fp
#LDFLAGS =

#FRT	= flang-20
#FFLAGS	= -g -O3 -ffast-math -Werror -fdefault-real-8
#LDFLAGS =

#FRT_UTIL	= flang-20
#FFLAGS_UTIL	= -g -O2 -Werror
#LDFLAGS =

# ---------------------------------------------------------------
# 静的ライブラリ作成コマンド
#   ifx の -ipo は LLVM LTO であり .o がビットコードになるため、
#   システムの ar ではシンボル索引を作れない。oneAPI 同梱の
#   llvm-ar(ifx と同じ bin の一段下 bin/compiler/ にある)を使う。
#   -ipo を使わない場合や gfortran 等では ar でよい。
# ---------------------------------------------------------------
ifeq ($(FRT),ifx)
IFXBIN	:= $(dir $(shell which ifx))
AR	= $(IFXBIN)compiler/llvm-ar
else
AR	= ar
endif
ARFLAGS	= rcs
