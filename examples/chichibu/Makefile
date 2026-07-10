# ENCflow/examples/<case>/Makefile  (abukuma, chichibu 共通)
#
#   make        ../../bin/a.out がなければ src で make install を実行し、
#               ここに a.out のシンボリックリンクを作る
#               (../../bin/a.out が既にあれば新しさは問わない)
#   make clean  a.out(リンク)と ./result 以下をすべて削除する
#
#   実行は手動で:  ./a.out param_xxx.txt など

BIN	= ../../bin/a.out
SRCDIR	= ../../src

all: a.out

# シンボリックリンクの作成
#   a.out が既に存在すれば何もしない。リンク先が消えている
#   (dangling link)場合は存在しない扱いになり、作り直される。
a.out: $(BIN)
	ln -sf $(BIN) a.out

# ../../bin/a.out がないときだけ発動する(存在すれば更新しない)
$(BIN):
	$(MAKE) -C $(SRCDIR) install

clean:
	rm -f a.out
	rm -rf result

.PHONY: all clean
