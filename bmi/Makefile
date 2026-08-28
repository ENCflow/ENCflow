# ENCflow/bmi/Makefile — CSDMS BMI アダプタ(optional ビルド)
#
#   make        検証ドライバ test_encflow_bmi をビルド
#               (必要なら ../src を先にビルドする)
#   make clean  生成物を削除
#
#   注意:
#   - src/ の既定ビルドは本ディレクトリに依存しない(方針10 追記
#     2026-08-28。BMI はあくまで libencflow のもう一つの入口)。
#   - 仕様モジュール bmif_2_0 は vendor/bmi.f90(CSDMS bmi-fortran、
#     MIT。NOTICE 参照)を同梱ビルドする。外部インストール不要。
#   - コンパイラ・精度(PREC)は ../make.inc に従う。src/ 側の
#     MODE / PREC を切り替えたときはここでも make clean すること
#     (libencflow.a・.mod と整合しない .o の混在リンクを防ぐ)。
#   - 現段階は逐次(MODE=serial)専用。

include ../make.inc

SRCDIR	= ../src
LIB	= $(SRCDIR)/libencflow.a

TARGET	= test_encflow_bmi
OBJS	= bmi.o bmi_encflow.o test_bmi.o

all: $(TARGET)

$(TARGET): $(OBJS) $(LIB)
	$(FRT) -o $@ $(FFLAGS) $(OBJS) $(LIB) $(LDFLAGS)

# libencflow.a が無ければ src を(現在の make.inc 設定で)ビルドする
$(LIB):
	$(MAKE) -C $(SRCDIR)

# BMI 仕様(bmif_2_0)。実数既定種別を含め本体と同じフラグでビルドする
bmi.o: vendor/bmi.f90
	$(FRT) -c $(FFLAGS) -o $@ $<

# m_main の .mod を参照するため -I$(SRCDIR)
bmi_encflow.o: bmi_encflow.f90 bmi.o $(LIB)
	$(FRT) -c $(FFLAGS) -I$(SRCDIR) $<

test_bmi.o: test_bmi.f90 bmi_encflow.o
	$(FRT) -c $(FFLAGS) $<

clean:
	rm -f *.o *.mod *.smod $(TARGET)

.PHONY: all clean
