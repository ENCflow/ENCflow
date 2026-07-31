# ENCflow 作業引き継ぎメモ(チャット移行用)

設計・規約・実バグの記録の正本は developer.md(§1〜§14)。
このメモは「現在進行中・未完了の項目」だけを書く。完了したら消してよい。

## 現在の到達点(要約)

- MPI 化は完了・検証済み: 帯分割+ハロ交換(案A)、確保縮小(第二段)、
  静的データの帯化(方式a・2点縮小)、m_record の点集約、決定的リダクション。
  検証の柱 =「np=1,2,4 が逐次 reference に ULP=0」+「-fcheck np>=2 を先に回す」。
- s%z(計算標高の動的状態化)導入済み。g%z = 入力地形(rank0 のみ全域保持)。
- 新モジュール: m_geomorph(重ね合わせ方式・calc_creep は未実装 par_stop)、
  m_gwflow(enc/stg 型の排他切替・バケツモデル実装済み)。
- m_output 分離、m_swflow の手続きポインタ成分化、list=読み込み専念の層契約。

## 未完了・検証待ち

1. **gwflow 導入コミットの検証(直近の宿題)**
   - fn_gwflow 未指定で全ケース既存 reference とビット一致(逐次・np=1,2,4)
   - バケツ疎通: wave 系 + f_gwmodel=1 で S_total が14桁不動、np=1,2,4 ULP=0
   - -fcheck np=2、リスタート往復(save/restore 6成分化の確認)
2. **developer.md への gwflow/geomorph の項の追記**(検証完了後)
   - 切替器 vs 重ね合わせの使い分け原則、s%hg 柱状換算契約、S 台帳、
     モデル実装5箇条(m_gwflow_bucket ヘッダが正本)
3. developer.md の日付プレースホルダ(2026-xx)の実日付化(残があれば)
4. **save/restore 再編(dir_save + save_info.txt)の検証(直近の宿題)**
   - 保存→復元の往復で状態がビット一致(逐次・np=1,2,4)
   - save_info.txt の版・格子・精度・成分数の不一致で par_stop すること
     (旧 save_state.dat 形式は読めなくなった=版エラーで停止が正)
   - swflow_enc.dat 欠如時に par_stop すること
   - PREC=single での保存→single 復元、および double 保存→single 復元の停止確認
   - state.dat 4成分化(u,v除外・2026-07-31版)後の往復ビット一致の再確認
   - STG(f_gridsystem=1)+ f_state_restore で par_stop すること
   - RLE 圧縮(2026-07-31b 版)後の往復ビット一致(海域・乾燥域を含む chichibu で)
   - RLE の両極端: ゼロなし成分(z)と全ゼロ成分(rsh 未使用時)が正しく往復すること
   - 単精度(PREC=single)ビルドでの RLE 往復(ビット判定の int32 経路)

## 中期の道標(着手順は実測次第)

- 全国データでの実測(メモリ RES、ランク別時間)→ セル数均等分割の要否判断
  (band_range 差し替えのみ。検証はランク数不変ビット一致がそのまま使える)
- geomorph: calc_creep 実装(ガウス丘の解析解ベンチマークを先に作る)。
  浸食有効化時は par_halo_cell(s%z) をステップ頭へ(§11 の TODO 参照)
- gwflow: RRI 型・鉛直浸透重視型の追加(m_gwflow_bucket を複製して契約に従う)
- NEC SDK 実機検証(mpinfort -show の可否確認 → スタンプ機構の対応判断)
- 初期化の一過性メモリピーク対策(単一ノード全国初期化が OOM したら)

## 作業の流儀(新チャットでも同じ)

- 作業対象の**現行ファイルを都度アップロード**(AI 側のファイルは残らない)
- 等価リファクタ=逐次ビット一致、機能追加=無効時ビット一致、が合否判定
- 等価変換とバグ修正・挙動変更はコミットを分ける
- 確保範囲を変える変更は、最適化ビルドより先に -fcheck np>=2
- 過去の議論の詳細は「以前のチャットで◯◯をどう決めたか検索して」と
  頼めば AI が過去会話から掘り返せる
