# =====================================================================
# ENCflow 共通コンパイラ設定
#   src/ と utils/ 以下の各 Makefile から include する。
#
#   FRT, FFLAGS : メインプログラムおよび src のモジュールを使う
#                 ユーティリティ用(.mod/ABI 互換のため PREC を含めて
#                 src と utils/rerecord 等で必ず同一にすること)
#   FRT_UTIL, FFLAGS_UTIL : src のモジュールを使わない独立ユーティリティ用
#                 (calc_catchmentarea, modify_* など。常に既定精度)
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
# 実数精度切り替え
#   double : 既定 real を倍精度に昇格(従来動作。既定)
#   single : 昇格なし(メモリ半減。結果は倍精度と一致しないため
#            既存 reference との回帰比較は不可。§1 参照)
#   各コンパイラブロックの R8 に「そのコンパイラの倍精度化フラグ」を
#   定義し、FFLAGS には -r8 系を直接書かず $(RFLAG) を使うこと。
#   切替後の全再ビルドは make.inc 依存により自動。
# ---------------------------------------------------------------
PREC	= double
#PREC	= single

# ---------------------------------------------------------------
# コンパイラ本体(FC)と MPI ラッパー(FC_MPI)
#   使う組をコメント切り替え。FRT は MODE に応じて自動決定される。
# ---------------------------------------------------------------
# Intel oneAPI (-ipo: リンク時に全体最適化。アーカイバは oneAPI の llvm-ar)
FC	= ifx
FC_MPI	= mpiifx
R8	= -r8
FFLAGS	= -g -fopenmp -warn all -fpe0 -Ofast -xHost -ipo $(RFLAG)
#FFLAGS	= -g -O0 -traceback -check all -warn all -fpe0 $(RFLAG)
#LDFLAGS =

# GNU Fortran (with MPICH or OpenMPI)
#   -flto=auto: リンク時最適化(-ipo 相当)。auto で LTO 処理を並列化。
#   アーカイバは gcc-ar(LTO プラグイン対応。llvm-ar は不可)
#   -ffree-line-length-none: gfortran は行長 132 桁をバイト数で数えるため、
#     日本語コメントを含む行が誤って弾かれるのを防ぐ(生成コードに影響なし)。
#     ただし行長の検査役もなくなるので、他コンパイラ(nfort 等)のために
#     1 行 132 バイト以内を目安に保つこと
#FC	= gfortran
#FC_MPI	= mpifort
#R8	= -fdefault-real-8 -fdefault-double-8
#FFLAGS	= -g -fopenmp -Ofast -march=native -flto=auto -Wall -ffpe-trap=zero,overflow -ffree-line-length-none $(RFLAG)
#FFLAGS	= -g -fopenmp -Ofast -Wall -ffpe-trap=zero,overflow -ffree-line-length-none $(RFLAG) -fcheck=all -fbacktrace
#FFLAGS	= -g -Og -fcheck=all -fbacktrace -Wall -ffpe-trap=invalid,zero,overflow -ffree-line-length-none $(RFLAG) -Wno-conversion -finit-real=snan -finit-integer=-88888888
#LDFLAGS =

# NVIDIA HPC SDK (-ipo/-flto 相当なし: -Mipa は 23.3 で無効化済み)
#   行長: gfortran の -ffree-line-length-none に相当するオプションは無いが、
#   既定で 132 桁を超える自由形式行を受け付けるため不要(-Mextend は
#   固定形式専用)。行長で弾かれる報告があれば要再確認
#FC	= nvfortran
#FC_MPI	= mpif90
#R8	= -Mr8
#FFLAGS	= -gopt -mp=multicore -Ofast -Minform=inform -Ktrap=divz,ovf $(RFLAG)
#FFLAGS	= -gopt -mp=multicore -Ofast -Minform=inform -Ktrap=divz,ovf $(RFLAG) -Mbounds -Mchkptr -Mchkstk
#LDFLAGS =

# AMD AOCC (with Open MPI build by AOCC)
#   -flto: リンク時最適化(-ipo 相当)。アーカイバは AOCC 同梱の llvm-ar
#FC	= flang
#FC_MPI	= mpifort
#R8	= -r8
#FFLAGS	= -g -fopenmp -Ofast -march=native -flto -Wall $(RFLAG) -ffast-math -Mcache_align
#LDFLAGS =

# LLVM flang-22 + libomp-22-dev
#FC	= flang-22
#FC_MPI	= mpifort
#R8	= -fdefault-real-8
#FFLAGS	= -g -O3 -fopenmp -ffast-math $(RFLAG)
#LDFLAGS =

# NEC SDK (SX-Aurora TSUBASA, Vector Engine 向けクロスコンパイル)
#   MPI ラッパーは NEC MPI の mpinfort。-flto/-ipo 相当なし(AR は素の ar)。
#   注意(他コンパイラとの流儀の違い):
#   - -ffast-math と -fassociative-math は nfort では既定で有効。
#     他コンパイラの -Ofast 相当が最初から入っている(§9 のコンパイラ間
#     ULP=1 の枠内。無効化して確認したいときは -fno-associative-math)
#   - FPE トラップはコンパイルオプションでなく実行時環境変数:
#       export VE_FPE_ENABLE=DIV,FOF,INV   (ゼロ除算, オーバーフロー, 無効演算)
#       export VE_TRACEBACK=VERBOSE        (-traceback でビルドした場合)
#     ジョブスクリプトか modulefile に入れておくこと
#   - -proginf は既定で有効(実行後に性能サマリが出る)。関数別の計測は
#     -ftrace を付けて ftrace コマンドで解析
#   - ベクトル化診断は -report-all(.L ファイルに整形リストが出る)
#FC	= nfort
#FC_MPI	= mpinfort
#R8	= -fdefault-real=8
#FFLAGS	= -g -fopenmp -O3 -finline-functions -Wall -traceback $(RFLAG)
#FFLAGS	= -g -fopenmp -O3 -finline-functions -Wall -traceback -report-all $(RFLAG)
#FFLAGS	= -g -O0 -fopenmp -fcheck=all -traceback=verbose -Wall $(RFLAG)
#LDFLAGS =

# MODE に応じて実際に使うコンパイラを決定
ifeq ($(MODE),mpi)
FRT	= $(FC_MPI)
else ifeq ($(MODE),serial)
FRT	= $(FC)
else
$(error MODE は serial か mpi を指定してください (現在: '$(MODE)'))
endif

# PREC に応じて精度フラグを決定(R8 は各コンパイラブロックで定義)
ifeq ($(PREC),double)
RFLAG	= $(R8)
else ifeq ($(PREC),single)
RFLAG	=
else
$(error PREC は double か single を指定してください (現在: '$(PREC)'))
endif

# ---------------------------------------------------------------
# 独立ユーティリティ用(MODE の影響を受けず常に逐次ビルド)
#   LTO 不要のため -flto は付けない
# ---------------------------------------------------------------
#FRT_UTIL	= ifx
#FFLAGS_UTIL	= -g -O2 -warn all -fpe0
#FFLAGS_UTIL	= -g -O0 -traceback -check all -warn all -fpe0

FRT_UTIL	= gfortran
FFLAGS_UTIL	= -g -O2 -Wall -ffpe-trap=invalid,zero,overflow -ffree-line-length-none
#FFLAGS_UTIL	= -g -Og -fcheck=all -Wall -ffpe-trap=invalid,zero,overflow -ffree-line-length-none -Wno-conversion

#FRT_UTIL	= nvfortran
#FFLAGS_UTIL	= -g -O2 -Minform=inform -Ktrap=fp

#FRT_UTIL	= flang
#FFLAGS_UTIL	= -g -O2 -march=native

#FRT_UTIL	= flang-22
#FFLAGS_UTIL	= -g -O2

# NEC SDK: ユーティリティは VH(x86 側)で動かすなら gfortran のままが楽。
# VE で動かす場合のみ nfort を使う
#FRT_UTIL	= nfort
#FFLAGS_UTIL	= -g -O2 -Wall -traceback

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
#   nfort は LTO 相当が無いため素の ar(既定分岐)でよい。
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
