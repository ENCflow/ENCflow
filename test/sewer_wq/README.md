# sewer_wq — 回帰テスト(下水噴出の衛生リスク = 水質×管路連続体層)

examples/sewer_hybrid のラン D(幹線1本+枝管網・セル別 sy/slot_sy)を
短縮・自己完結化した回帰テスト。降雨 100 mm/h × 30 min(計 51.7 mm)が
管内貯留(~16 mm)を超えてサーチャージ・噴出を起こし、噴出・吐口水を
「下水 10⁶ CFU/100mL」(単位読み替え g = 10⁶ CFU → wq_gwc_conc = 1e4)
として大腸菌の拡散・死滅(T90 = 1 日)を追う。§30 の供給側固定濃度
近似と §46.5 (4) サブサイクリング(dt = 0.1 s → N = 3)・(5) セル別
sy/slot_sy を同時に検査する。**実務手順の正本は users_guide/wq.md
「下水噴出の衛生リスク評価」**。

## 実行方法

```
make            # ../../bin/ の実行ファイルへのリンクを張る
./Run.sh        # 逐次 + reference 比較(~10 秒。1 時間の計算)
./Run_MPI.sh 2  # MPI(np=2)+ 逐次 reference と ULP=0 比較
```

比較対象は Log.txt(水収支)と wq.csv(物質収支。管路連携の
in_gwc_g / to_gwc_g 列を含む)。data_sewer/ は静的データとして
コミット済み(生成の記録は examples/sewer_hybrid/gen_data.py)。

## 検証結果(2026-08-24。reference 作成時)

- 噴出が発生: in_gwc = 2.001e7(単位)、枡再取込 to_gwc = 5.13e4
- wq.csv の質量収支が機械精度で閉合:
  in_gwc − to_gwc − decay(1.118e6) − 地表残存(1.884e7) = 0
  (表示 8 桁で残差ゼロ、相対 ~1e-8 = 表示丸め)
- 水収支: S_total(終了時) = 積算雨量 51.67 mm(閉境界)
- サブサイクリング N = 3(dt 上限 3.72e-2 s に対し dts = 0.1 s)
