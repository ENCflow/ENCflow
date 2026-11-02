# ENCflow/examples/karst/Makefile
#   make        ../../bin/ の実行ファイルへのリンクと入力(make_terrain.py が z.txt・sol.txt を作る)
#   make run    主ケース(param.txt)を計算する(約 1 時間。4 スレッド)
#   make supp   補足の 2 ケース(側方溶食 param_lat.txt、+ 崩落 param_rock.txt)を計算する(各約 1 時間)
#   make clean  リンクと生成物を削除する
#   画面出力は Screen.log / Screen_lat.log / Screen_rock.log(plot_results.py が湛水の時系列と台帳を読む)

TOPDIR	= ../..
BINDIR	= $(TOPDIR)/bin
SRCDIR	= $(TOPDIR)/src

all: links inputs

links:
	@if [ ! -e $(BINDIR)/encflow ] && [ ! -e $(BINDIR)/encflow_mpi ]; then \
	    $(MAKE) -C $(SRCDIR) install; \
	fi
	@for b in encflow encflow_mpi; do \
	    if [ -e $(BINDIR)/$$b ]; then ln -sf $(BINDIR)/$$b $$b; \
	    else rm -f $$b; fi; \
	done

inputs: z.txt

z.txt: make_terrain.py
	python3 make_terrain.py

run: all
	./encflow param.txt | tee Screen.log

supp: all
	./encflow param_lat.txt | tee Screen_lat.log
	./encflow param_rock.txt | tee Screen_rock.log

install: all

clean:
	rm -rf result result_* save save_*
	rm -f encflow encflow_mpi a.out Screen.log Screen*.log analysis*.txt z.txt sol.txt

.PHONY: all links inputs run supp install clean
