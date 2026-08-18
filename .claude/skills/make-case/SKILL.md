---
name: make-case
description: 現象の記述から ENCflow の実験ケース(パラメータ+データ)を作成し、実行・検証・図化まで行う。Create an experimental ENCflow case (parameters + data) from a phenomenon description, then run, verify, and visualize it. Use when the user describes a physical phenomenon or scenario they want to simulate (e.g. "融雪出水のケースを作って", "make a case for rain ponding").
---

# ENCflow の実験ケースを作る

引数(または直前の会話)で与えられた**現象の記述**から、動く実験
ケースを作成し、実行・検証・図化まで行う。作業は利用者としての
ケース作成であり、src/ のコード変更は行わない。

## 手順

1. **現象→機能の対応を引く**: docs/users_guide/usecases.md を読み、
   該当する現象の行から「使う機能」「設定の要点」「備考」を得る。
   該当行がなければ最も近い行と各章の説明から構成を判断する。
   ENCflow で原理的に扱えない現象(usecases 末尾の計画中テーブル・
   README の「できないこと」)なら、その旨を説明して代替を提案し、
   無理にケースを作らない。
2. **パラメータの書式を確認する**: 使う機能ごとに
   examples/List_samples/list_*.txt(注釈付き実例)と
   docs/users_guide/ の該当章を読む。書式・単位・必須項目は
   これらを正とし、記憶で書かない。似た構成の test/ ケース
   (wave, pump, frost, salt, conduit, debris 等)があれば param.txt を
   雛形にする。
3. **ケースを組み立てる**: `work/<短い英名>/` を作成し、
   - param.txt(全行に日本語コメント。ヘッダに現象・設計・期待される
     挙動を数行で書く)
   - 地形・マスク等のデータが要るなら Python で生成(生成スクリプトも
     同じディレクトリに残す)
   を置く。格子は最初は小さく(数十×数十)、計算時間は数分以内を
   目安にする。
4. **実行する**: bin/encflow が無い・古い場合は `cd src && make install`
   (コンテナや新環境では `make clean` から)。ケースのディレクトリで
   `../../bin/encflow param.txt` 相当を実行する。
5. **検証する**: 作って終わりにしない。
   - Log の S 列(水収支)が入力(降雨量・初期水量・取水量等)と
     整合するか概算で照合する
   - 出力場(H/E/Hg 等のテキスト行列)を読み、期待される挙動
     (手順3のヘッダに書いた内容)が出ているか確認する
   - 合わなければ原因を調べて直す(dt・安定条件・機能の選択ミス等)
6. **図化して報告する**: matplotlib があれば水深・水位等の分布図か
   時系列図を png で保存する(無ければ pip インストールを試み、
   できなければ数表で代替)。最後に、作成したファイル一覧・実行方法・
   検証結果(数字)・パラメータの変え方(感度実験の入口)を短く
   まとめて報告する。

## 禁止事項

- **test/*/reference の変更・`Run.sh -u` の実行は絶対にしない**
- test/・examples/ 内のファイルを上書きしない(雛形はコピーして使う)
- 頼まれていない src/ のコード変更をしない
- 実行せずに「できました」と報告しない(検証まで含めて完了)
