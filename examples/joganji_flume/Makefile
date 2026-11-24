# ENCflow/examples/joganji_flume/Makefile
#   make         ../../bin/ の実行ファイルへのリンクと入力(make_init.py が data_nilim/ から 10 cm 格子の入力を作る)
#   make spinup  助走計算(固定床、基底流量)と、その最終水深の初期水深 h_spinup.txt への写し
#   make run     ケース 2-1 の 240 分を混合粒径と単一粒径で計算する(順に。並べて回すなら README の手順)
#   make sub     感度の 2 構成(下層の組成を表層と同じ、下流端の延長を固定床高)の混合粒径の計算
#   make figs    図と数表(plot_results.py。日英)
#   make clean   リンクと生成物を削除する(data_nilim/ は残す)
# data_nilim/ は国総研の Excel から extract_nilim.py で抜き出したもの(openpyxl が要るのはその抜き出しだけ。README)

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src
INPUTS	= z.txt mask.txt rn.txt sd.txt fa1.txt fa2.txt fa3.txt geoinfo.txt geoinfo_outlet.txt z_outlet.txt boundary.txt boundary_single.txt \
	  boundary_spinup.txt inflow_cells.txt inflow_q.txt inflow_qbmix.txt inflow_qb.txt inflow_q_spinup.txt record.txt grid_info.txt

all: links inputs

inputs: $(INPUTS)

$(INPUTS): make_init.py data_nilim/grid.csv.gz data_nilim/gsd.csv.gz data_nilim/sections.csv data_nilim/banks.csv.gz data_nilim/bc_2-1.csv.gz data_nilim/wl_2-1.csv.gz
	python3 make_init.py

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

# 画面出力は Screen_<結果のディレクトリ>.log(plot_results.py が台帳を読む。警告は標準エラーに出るので
# 2>&1 で合わせて記録する)
spinup: all
	./encflow param_spinup.txt 2>&1 | tee Screen_result_spinup.log
	python3 make_init.py --spinup-h result_spinup

run: all
	./encflow param.txt 2>&1 | tee Screen_result.log
	./encflow param_single.txt 2>&1 | tee Screen_result_single.log

sub: all
	./encflow param_sub.txt 2>&1 | tee Screen_result_sub.log
	./encflow param_outlet.txt 2>&1 | tee Screen_result_outlet.log

figs:
	python3 plot_results.py
	python3 plot_results.py en

install: all

clean:
	rm -rf result result_* __pycache__
	rm -f encflow encflow_mpi Screen_*.log h_spinup.txt $(INPUTS)

.PHONY: all links inputs spinup run sub figs install clean
