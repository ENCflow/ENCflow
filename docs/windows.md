# Windows での使い方(Unix がはじめての方へ)

ENCflow は Linux 系の環境で動きます。Windows しか使ったことがなくても
大丈夫です — 次の順路がおすすめです。

## ① まずはインストールなしで試す(5分)

ブラウザだけで ENCflow をビルド・実行・可視化できる Colab ノートブックを
用意しています。管理者権限も設定も不要です。

**[→ Colab で ENCflow を動かす](https://colab.research.google.com/github/ENCflow/ENCflow/blob/main/docs/colab_quickstart.ipynb)**

ノートブックのセルに書かれている `git clone` や `make` は、そのまま
下記 WSL でも使う実物の Unix コマンドです。まずここで一度動かして
おくと、以降の説明がすべて「見たことがあるもの」になります。

## ② 続けるなら WSL(Windows 標準の Linux 環境)

WSL は Microsoft 公式の機能で、Windows の中に Ubuntu(Linux)を
入れられます。インストールは PowerShell(管理者)で 1 コマンドです:

```powershell
wsl --install
```

再起動後、スタートメニューから Ubuntu を開き、ユーザー名とパスワードを
決めたら、あとは [インストールガイド](install.md) の手順どおりです:

```bash
sudo apt update && sudo apt install -y gfortran make git
git clone https://github.com/ENCflow/ENCflow.git
cd ENCflow/src && make install
cd ../test/wave && ./Run.sh
```

詰まったら Microsoft の
[WSL インストールガイド](https://learn.microsoft.com/ja-jp/windows/wsl/install)
を参照してください。

## 使うコマンドはこれだけ(早見表)

ENCflow の利用で日常的に使う Unix コマンドは 10 個程度です。
これ以上の予習は要りません。

| コマンド | 意味 | 例 |
|---|---|---|
| `cd 場所` | フォルダを移動する | `cd ENCflow/test/wave` |
| `cd ..` | ひとつ上のフォルダへ | |
| `ls` | いまの場所のファイル一覧 | |
| `pwd` | いまどこにいるか表示 | |
| `make install` | ビルド(コンパイル) | src/ で実行 |
| `./Run.sh` | 実行スクリプトを走らせる | 各 test/ ケースで |
| `./encflow param.txt` | ENCflow を直接実行 | |
| `cat ファイル` / `less ファイル` | テキストを表示(less は `q` で終了) | `less result/Log.txt` |
| `cp 元 先` | ファイルをコピー | `cp param.txt param2.txt` |
| `Tab` キー | ファイル名を途中まで打って補完 | 必須テクニック |
| `↑` キー | 前に打ったコマンドを呼び出す | 必須テクニック |

## Windows 側とのファイルのやりとり

- エクスプローラーのアドレス欄に `\\wsl$` と打つと、WSL の中の
  ファイルが**ふつうのフォルダとして**見えます。パラメータファイルの
  編集はメモ帳や VS Code で、結果のテキスト・CSV は Excel で、
  GeoTIFF は GIS ソフトでそのまま開けます。
- 本格的に使うなら [VS Code](https://code.visualstudio.com/) +
  「WSL」拡張機能が快適です(編集・ターミナル・ファイル閲覧が
  1 画面にまとまります)。

## ③ WSL が使えない環境では

学校の PC などで WSL を有効化できない場合も、①の Colab はブラウザ
だけで動きます。ネイティブ Windows 用の環境(MSYS2 等)でも動く
見込みですが、現時点では動作確認が済んでいないため、WSL を推奨します。
