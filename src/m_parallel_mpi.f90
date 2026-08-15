module m_parallel
!=====================================================================
! 並列層: MPI 版
!   m_parallel_serial.f90 と同一のインターフェースを提供する。
!   両ファイルの公開手続きは常に一致させて保守すること。
!
! メッセージ出力の使い分け:
!   par_info(msg)  進捗・情報。ランク0のみ標準出力に表示
!   par_warn(msg)  局所的な警告。検出したランクがランク番号付きで
!                  標準エラーに表示(停止しない)
!   par_stop(msg)  決定的エラー(設定不正など全ランクが同時に検出
!                  するもの)。必ず全ランクが揃って呼ぶこと
!                  (collective)。ランク0が表示して正常経路で全体停止
!   par_abort(msg) 局所的な致命的エラー。検出したランクだけが呼んで
!                  よい。ランク番号付きで表示して即時に全体強制終了
!
! 領域分割情報 dcp:
!   - par_decomp_init(nx, ny, jw1, jw2[, rowwork]) で設定する(格子サイズ
!     確定後、m_geoinfo_init の直後に呼ぶこと)。rowwork(行ごとの有効
!     セル数)を渡すと帯幅を負荷が均等になるよう調整する(重み付き分割)
!   - 各モジュールは use m_parallel, only: dcp で直接参照してよい
!     (protected 属性により変更は本モジュール内に限定される)
!   - 計算カーネルには dcp を見せず、範囲(js, je 等)を引数で渡す
!     (dcp の直接参照はフェーズの入口まで)
!   - js/je は「計算範囲(全域窓∩自ランク担当帯)」、jsh/jeh は
!     「配列確保範囲(担当帯+ハロ。現段階は全域 1..ny)」、jw1/jw2 は
!     全域の有効窓。全域窓の端で1行縮めるループは
!       do j = max(dcp%js, dcp%jw1+1), min(dcp%je, dcp%jw2-1)
!     と書くこと(dcp%js+1 と書くと分割後にランク境界まで縮んでしまう)
!
! 注意:
!   - 既定 real のサイズはビルド時の PREC(make.inc)で変わるため、
!     MPI データ型は MPI_REAL/MPI_REAL8 を直接書かず必ず MPI_WP を使う。
!     MPI_WP は par_init が storage_size(1.0) から実行時に確定する
!     (MPI_REAL は MPI ライブラリの構成次第で -r8 昇格と食い違い、
!      エラーにならず値が化けるため使用禁止)。
!     例外: バッファが real(real64) 明示の手続き(par_sum_rows)は
!     MPI_REAL8 固定でよい(バッファ型と常に一致するため)。
!   - OpenMP 併用のため MPI_Init_thread で FUNNELED を要求する。
!     (MPI 呼び出しはマスタースレッドのみ、が前提)
!   - エラー・警告を error_unit に出すのは意図的(tee で作る
!     Log.txt =回帰テストの比較対象= に混入させないため)
!=====================================================================
   use mpi_f08
   use, intrinsic :: iso_fortran_env, only: output_unit, error_unit, real64, int64
   implicit none
   private
   public :: par_init, par_finalize
   public :: par_decomp_init
   public :: par_info, par_warn, par_stop, par_abort
   public :: par_barrier
   public :: par_allreduce_min
   public :: par_halo_cell, par_halo_edge, par_edge_merge
   public :: par_allreduce_max, par_allreduce_sumi, par_allreduce_maxi
   public :: par_allreduce_sumr
   public :: par_sum_rows
   public :: par_gather_to, par_gather_to_i, par_gather_edge_to
   public :: par_scatter_cell, par_scatter_cell_i, par_scatter_edge
   public :: par_reduce_points
   public :: par_bcast_cell, par_bcast_cell_i, par_bcast_edge
   public :: nrank, nproc, is_root
   public :: t_decomp, dcp
   public :: MPI_WP

   integer, protected, save :: nrank  = 0
   integer, protected, save :: nproc  = 1
   logical, protected, save :: is_root = .true.

   ! 領域分割情報(j方向分割。ブロック分割に拡張する場合は
   ! i方向成分を追加し、serial 版と同時に改定すること)
   type :: t_decomp
      integer :: nx_g = 0        ! 全領域サイズ x(参考保持)
      integer :: ny_g = 0        ! 全領域サイズ y(参考保持)
      integer :: jw1 = 1         ! 全域の有効窓の開始 j(= g%wy(1))
      integer :: jw2 = 0         ! 全域の有効窓の終了 j(= g%wy(2))
      integer :: js = 1          ! 自ランク計算範囲の開始 j(全域窓∩担当帯)
      integer :: je = 0          ! 自ランク計算範囲の終了 j
      integer :: jsh = 1         ! 配列確保範囲の開始 j(担当帯+ハロ。現段階は全域)
      integer :: jeh = 0         ! 配列確保範囲の終了 j
      integer :: rank_n = -1     ! j+側の隣接ランク(なければ負)
      integer :: rank_s = -1     ! j-側の隣接ランク(なければ負)
      integer :: nhalo = 2       ! ハロ幅(セル行。移流項のステンシル幅2による)
   end type t_decomp

   type(t_decomp), protected, save :: dcp

   ! 全ランク分の帯境界表(par_decomp_init が構築し band_range が引く。
   ! 全ランクが同一の表を持つ)
   integer, allocatable, save :: js_tab(:), je_tab(:)

   ! 実数通信用データ型(par_init が既定 real の実サイズから確定する)
   type(MPI_Datatype), protected, save :: MPI_WP = MPI_DATATYPE_NULL

contains

   subroutine par_init()
      integer :: iprov
      call MPI_Init_thread(MPI_THREAD_FUNNELED, iprov)
      if (iprov < MPI_THREAD_FUNNELED) then
         write(error_unit,'(a,i0)') &
            'ERROR: MPI thread support insufficient: ', iprov
         flush(error_unit)
         call MPI_Abort(MPI_COMM_WORLD, 1)
      end if
      call MPI_Comm_rank(MPI_COMM_WORLD, nrank)
      call MPI_Comm_size(MPI_COMM_WORLD, nproc)
      is_root = (nrank == 0)

      ! 実数通信用データ型を既定 real の実サイズ(PREC 依存)から確定する
      if (storage_size(1.0) == 64) then
         MPI_WP = MPI_REAL8
      else
         MPI_WP = MPI_REAL4
      end if

      ! 起動側との整合検証: Run スクリプトが期待ランク数を環境変数で渡す。
      ! PMI 不整合によるシングルトン化(全プロセスが nproc=1 で独立起動し、
      ! 結果は壊れないまま並列だけが静かに死ぬ事故。ビルドと異なる MPI の
      ! mpirun 使用や、Ubuntu 24.04 の mpich パッケージバグ(hydra が PMIx
      ! 非対応。Debian #1066735)で実発生)を起動直後に検出する。
      ! 環境変数が未設定なら検査しない(手動実行に影響なし)。
      check_np: block
         character(len=32) :: env
         integer :: np_expect, istat
         call get_environment_variable("ENCFLOW_EXPECT_NP", env, status=istat)
         if (istat == 0) then
            read(env, *, iostat=istat) np_expect
            if (istat == 0 .and. np_expect /= nproc) then
               write(error_unit,'(a,i0,a,i0,a)') &
                  'ERROR: expected ', np_expect, ' ranks but MPI initialized with ', &
                  nproc, ' (PMI mismatch / singleton launch?)'
               flush(error_unit)
               call MPI_Abort(MPI_COMM_WORLD, 1)
            end if
         end if
      end block check_np
   end subroutine par_init

   subroutine par_decomp_init(nx, ny, jw1, jw2, rowwork)
      ! 領域分割の決定。格子サイズと有効窓の確定後
      ! (m_geoinfo_init の直後)に全ランクが揃って呼ぶこと(collective)。
      ! 全域窓 [jw1, jw2] をランク数で行分割し、自ランクの帯を決める。
      ! rowwork(行ごとの有効セル数。サイズ ny)を渡すと、重みの累積和を
      ! 等分する位置に帯境界を置く(重み付き分割。列島形状の行間偏りに
      ! よるランク間不均衡の対策)。省略時・総重みゼロ時は行数の均等分割。
      ! 全ランクが同一の rowwork を渡すこと(全ランクが持つ全域マスク
      ! から数えれば自然に満たされる。表の構築に通信はしない)。
      ! 第一段: 配列は全域確保のまま(jsh/jeh は 1..ny。第二段で
      !         js-nhalo..je+nhalo へ縮小する)
      integer, intent(in) :: nx, ny
      integer, intent(in) :: jw1, jw2   ! 全域の有効窓(= g%wy(1:2))
      integer, intent(in), optional :: rowwork(:)   ! 行重み(有効セル数)
      integer :: nrows
      character(len=1024) :: buf
      dcp%nx_g = nx
      dcp%ny_g = ny
      dcp%jw1 = jw1
      dcp%jw2 = jw2
      nrows = jw2 - jw1 + 1
      ! 各帯は最低2行必要(ハロ交換が隣の隣を参照しない前提のため)
      if (nrows < 2 * nproc) then
         write(buf,'(a,i0,a,i0,a)') 'parallel: domain too small for ', nproc, &
            ' ranks: window has ', nrows, ' rows (need >= 2 rows per rank)'
         call par_stop(trim(buf))       ! 全ランク同一の判定なので collective 安全
      end if
      if (present(rowwork)) then
         if (size(rowwork) /= ny) then
            call par_stop('parallel: rowwork size does not match ny')
         end if
      end if
      call build_band_table(rowwork)
      call band_range(nrank, dcp%js, dcp%je)
      ! 第二段: 配列確保範囲 = 担当帯 ± ハロ幅(全域端でクリップ)
      call band_range_h(nrank, dcp%jsh, dcp%jeh)
      dcp%rank_s = nrank - 1                            ! nrank=0 では -1(隣なし)
      dcp%rank_n = merge(nrank + 1, -1, nrank < nproc - 1)
   end subroutine par_decomp_init

   subroutine build_band_table(rowwork)
      ! 全ランク分の帯境界表を構築する(分割規則の正本)。
      ! 重み付き分割は「累積重みが total*(r+1)/nproc に達する最小の行」に
      ! 境界 r|r+1 を置く。整数演算のみの決定的手順なので全ランクが
      ! 同一の表を得る。各帯最低2行の制約は目標位置より優先する
      ! (残りランクに2行ずつ残す上限 jmax で頭打ち。実行可能性は
      ! nrows >= 2*nproc の事前検査で保証済み)
      integer, intent(in), optional :: rowwork(:)
      integer(int64), allocatable :: cum(:)   ! cum(j) = 重みの累積和(jw1..j)
      integer(int64) :: total, target_r
      integer :: r, j, je, jmax, nrows, base, rem
      if (allocated(js_tab)) deallocate(js_tab)
      if (allocated(je_tab)) deallocate(je_tab)
      allocate(js_tab(0:nproc-1), je_tab(0:nproc-1))

      ! 既定: 行数の均等分割(余りは若いランクへ)
      nrows = dcp%jw2 - dcp%jw1 + 1
      base = nrows / nproc
      rem  = mod(nrows, nproc)
      do r = 0, nproc - 1
         js_tab(r) = dcp%jw1 + r * base + min(r, rem)
         je_tab(r) = js_tab(r) + base - 1
         if (r < rem) je_tab(r) = je_tab(r) + 1
      end do
      if (.not. present(rowwork)) return

      ! 重み付き分割(int64: 全国級の総セル数×ランク数は int32 を超える)
      allocate(cum(dcp%jw1-1:dcp%jw2))
      cum(dcp%jw1-1) = 0
      do j = dcp%jw1, dcp%jw2
         cum(j) = cum(j-1) + max(rowwork(j), 0)
      end do
      total = cum(dcp%jw2)
      if (total <= 0) return             ! 有効セルなし: 均等分割のまま

      j = dcp%jw1
      do r = 0, nproc - 1
         js_tab(r) = j
         if (r == nproc - 1) then
            je = dcp%jw2
         else
            jmax = dcp%jw2 - 2 * (nproc - 1 - r)  ! 残りランクに2行ずつ残す
            target_r = (total * (r + 1)) / nproc
            je = min(j + 1, jmax)                 ! 各帯最低2行
            do while (je < jmax .and. cum(je) < target_r)
               je = je + 1
            end do
         end if
         je_tab(r) = je
         j = je + 1
      end do

      ! 分割結果の要約(標準出力=Screen.log 行き。回帰比較対象の
      ! result/Log.txt には入らない)
      report: block
         character(len=256) :: msg
         integer(int64) :: wmin, wmax, w
         wmin = huge(wmin)
         wmax = 0
         do r = 0, nproc - 1
            w = cum(je_tab(r)) - cum(js_tab(r) - 1)
            wmin = min(wmin, w)
            wmax = max(wmax, w)
         end do
         write(msg,'(a,i0,a,i0,a,i0,a,i0)') &
            'parallel: weighted band decomposition, cells/rank min=', wmin, &
            ' max=', wmax, ', rows/rank min=', &
            minval(je_tab - js_tab) + 1, ' max=', maxval(je_tab - js_tab) + 1
         call par_info(trim(msg))
      end block report
   end subroutine build_band_table

   subroutine par_halo_cell(a)
      ! セル配列の行ハロ交換(幅 dcp%nhalo)。
      ! 自帯 js..je の値を正とし、js-w..js-1 を南から、je+1..je+w を
      ! 北から受け取る。ステップ頭に、前ステップ確定状態(h, u, v, vv)
      ! に対して呼ぶ。
      real, intent(inout) :: a(1:, dcp%jsh:)
      integer :: w, n1
      w  = dcp%nhalo
      n1 = size(a, 1)
      if (dcp%rank_s >= 0) then
         call MPI_Sendrecv(a(:, dcp%js:dcp%js+w-1),  n1*w, MPI_WP, dcp%rank_s, 11, &
                           a(:, dcp%js-w:dcp%js-1),  n1*w, MPI_WP, dcp%rank_s, 12, &
                           MPI_COMM_WORLD, MPI_STATUS_IGNORE)
      end if
      if (dcp%rank_n >= 0) then
         call MPI_Sendrecv(a(:, dcp%je-w+1:dcp%je),  n1*w, MPI_WP, dcp%rank_n, 12, &
                           a(:, dcp%je+1:dcp%je+w),  n1*w, MPI_WP, dcp%rank_n, 11, &
                           MPI_COMM_WORLD, MPI_STATUS_IGNORE)
      end if
   end subroutine par_halo_cell

   subroutine par_halo_edge(a)
      ! エッジ配列の行ハロ交換(幅1)。
      ! コミット済みの有効エッジ行は js-1..je(共有行 js-1 と je は
      ! 界面補完により南北で同値)。RK の参照のために js-2 を南から、
      ! je+1 を北から受け取る。送りは相手にとっての同位置
      ! (南へ js、北へ je-1)。
      real, intent(inout) :: a(1:, 0:, dcp%jsh-1:)
      integer :: n
      n = size(a, 1) * size(a, 2)
      if (dcp%rank_s >= 0) then
         call MPI_Sendrecv(a(:, :, dcp%js),   n, MPI_WP, dcp%rank_s, 13, &
                           a(:, :, dcp%js-2), n, MPI_WP, dcp%rank_s, 14, &
                           MPI_COMM_WORLD, MPI_STATUS_IGNORE)
      end if
      if (dcp%rank_n >= 0) then
         call MPI_Sendrecv(a(:, :, dcp%je-1), n, MPI_WP, dcp%rank_n, 14, &
                           a(:, :, dcp%je+1), n, MPI_WP, dcp%rank_n, 13, &
                           MPI_COMM_WORLD, MPI_STATUS_IGNORE)
      end if
   end subroutine par_halo_edge

   subroutine par_edge_merge(a, take_s, take_n)
      ! momentum 後の界面エッジ行の成分補完。
      ! 行 js-1 には自セル js が書いた成分と南隣セル js-1 が書いた成分が
      ! 同居するため、南の所有成分(take_s が真の k)を南の値で上書きする。
      ! 行 je も北と対称。同一エッジのフラックスを南北で共有することで
      ! 質量保存がビットレベルで厳密になる(developer.md §11)。
      ! マスクは格子実装側がエッジ格納規約(dje)から与える。
      real, intent(inout) :: a(1:, 0:, dcp%jsh-1:)
      logical, intent(in) :: take_s(:)
      logical, intent(in) :: take_n(:)
      real :: buf(size(a, 1), size(a, 2))
      integer :: n, k
      n = size(a, 1) * size(a, 2)
      if (dcp%rank_s >= 0) then
         call MPI_Sendrecv(a(:, :, dcp%js-1), n, MPI_WP, dcp%rank_s, 15, &
                           buf,               n, MPI_WP, dcp%rank_s, 16, &
                           MPI_COMM_WORLD, MPI_STATUS_IGNORE)
         do k = 1, size(a, 1)
            if (take_s(k)) a(k, :, dcp%js-1) = buf(k, :)
         end do
      end if
      if (dcp%rank_n >= 0) then
         call MPI_Sendrecv(a(:, :, dcp%je),   n, MPI_WP, dcp%rank_n, 16, &
                           buf,               n, MPI_WP, dcp%rank_n, 15, &
                           MPI_COMM_WORLD, MPI_STATUS_IGNORE)
         do k = 1, size(a, 1)
            if (take_n(k)) a(k, :, dcp%je) = buf(k, :)
         end do
      end if
   end subroutine par_edge_merge

   subroutine band_range(r, js_r, je_r)
      ! ランク r の担当帯を返す(境界表は par_decomp_init →
      ! build_band_table が構築する=分割規則の正本)。
      ! gather の counts/displs もここから導く。
      integer, intent(in) :: r
      integer, intent(out) :: js_r, je_r
      js_r = js_tab(r)
      je_r = je_tab(r)
   end subroutine band_range

   subroutine band_range_h(r, jsh_r, jeh_r)
      ! ランク r の配列確保範囲(担当帯±ハロ。全域端でクリップ)。
      ! par_decomp_init の jsh/jeh と scatter の送信範囲はここから導く
      ! (確保範囲の規則の正本)
      integer, intent(in) :: r
      integer, intent(out) :: jsh_r, jeh_r
      integer :: js_r, je_r
      call band_range(r, js_r, je_r)
      jsh_r = max(1, js_r - dcp%nhalo)
      jeh_r = min(dcp%ny_g, je_r + dcp%nhalo)
   end subroutine band_range_h

   subroutine par_allreduce_max(vals)
      ! 実数ベクトルの全ランク最大値。max は結合順に依存しない厳密演算
      ! なので、ランク数によらずビット同一の結果になる。
      real, intent(inout) :: vals(:)
      call MPI_Allreduce(MPI_IN_PLACE, vals, size(vals), MPI_WP, MPI_MAX, &
                         MPI_COMM_WORLD)
   end subroutine par_allreduce_max

   subroutine par_allreduce_sumi(ivals)
      ! 整数ベクトルの全ランク合計(事象カウント用。整数和は厳密)
      integer, intent(inout) :: ivals(:)
      call MPI_Allreduce(MPI_IN_PLACE, ivals, size(ivals), MPI_INTEGER, &
                         MPI_SUM, MPI_COMM_WORLD)
   end subroutine par_allreduce_sumi

   subroutine par_allreduce_maxi(ival)
      ! 整数スカラーの全ランク最大値(ierror の集約用)
      integer, intent(inout) :: ival
      call MPI_Allreduce(MPI_IN_PLACE, ival, 1, MPI_INTEGER, MPI_MAX, &
                         MPI_COMM_WORLD)
   end subroutine par_allreduce_maxi

   subroutine par_allreduce_sumr(vals)
      ! 実数ベクトルの全ランク合計。実数和の決定性規律(§11)があるため、
      ! 「各要素の寄与ランクがちょうど1つ(他ランクは 0)」の使い方に
      ! 限ること。x+0=x は浮動小数でも厳密なので、この使い方なら加算順に
      ! 依存せず、ランク数によらずビット同一になる(帯所有ランクだけが
      ! 埋めるゼロ初期化ベクトルの全ランク共有=allgather の代用)
      real, intent(inout) :: vals(:)
      call MPI_Allreduce(MPI_IN_PLACE, vals, size(vals), MPI_WP, MPI_SUM, &
                         MPI_COMM_WORLD)
   end subroutine par_allreduce_sumr

   subroutine par_sum_rows(rowsum, total)
      ! 行部分和のランク横断・決定的総和。
      ! rank0 が全域窓の行並び(j 昇順)に組み立ててから一括総和するため、
      ! 結果はランク数に依存しない(逐次版と同じ「全窓行の一括総和」)。
      ! 引数は PREC によらず real64 固定(診断集約の桁落ち防止。
      ! 倍精度ビルドでは real64=既定 real なので単一実装で済む。§1)。
      ! 通信型も MPI_WP でなく MPI_REAL8 固定。
      real(real64), intent(in) :: rowsum(dcp%js:)
      real(real64), intent(out) :: total
      real(real64) :: buf(dcp%jw1:dcp%jw2)
      integer :: counts(0:nproc-1), displs(0:nproc-1)
      integer :: r, js_r, je_r
      do r = 0, nproc - 1
         call band_range(r, js_r, je_r)
         counts(r) = je_r - js_r + 1
         displs(r) = js_r - dcp%jw1
      end do
      call MPI_Gatherv(rowsum, dcp%je - dcp%js + 1, MPI_REAL8, &
                       buf, counts, displs, MPI_REAL8, 0, MPI_COMM_WORLD)
      total = 0.0
      if (is_root) total = sum(buf)
      call MPI_Bcast(total, 1, MPI_REAL8, 0, MPI_COMM_WORLD)
   end subroutine par_sum_rows

   subroutine par_gather_to(buf, a)
      ! 各ランクの担当帯 js..je を rank0 の全域バッファ buf(1:nx,1:ny) へ
      ! 集約する(第二段: 帯確保の配列を出力するための経路)。
      ! buf の帯外の行は変更しない(呼び出し側でゼロ初期化しておくこと)。
      ! rank0 以外の buf は参照されないためサイズ1のダミーでよい。
      real, intent(inout) :: buf(1:, 1:)
      real, intent(in) :: a(1:, dcp%jsh:)
      integer :: counts(0:nproc-1), displs(0:nproc-1)
      integer :: r, js_r, je_r, n1
      n1 = size(a, 1)
      do r = 0, nproc - 1
         call band_range(r, js_r, je_r)
         counts(r) = n1 * (je_r - js_r + 1)
         displs(r) = n1 * (js_r - 1)
      end do
      call MPI_Gatherv(a(:, dcp%js:dcp%je), counts(nrank), MPI_WP, &
                       buf, counts, displs, MPI_WP, 0, MPI_COMM_WORLD)
   end subroutine par_gather_to

   subroutine par_gather_to_i(buf, a)
      ! par_gather_to の整数版(流下方向フラグ等)
      integer, intent(inout) :: buf(1:, 1:)
      integer, intent(in) :: a(1:, dcp%jsh:)
      integer :: counts(0:nproc-1), displs(0:nproc-1)
      integer :: r, js_r, je_r, n1
      n1 = size(a, 1)
      do r = 0, nproc - 1
         call band_range(r, js_r, je_r)
         counts(r) = n1 * (je_r - js_r + 1)
         displs(r) = n1 * (js_r - 1)
      end do
      call MPI_Gatherv(a(:, dcp%js:dcp%je), counts(nrank), MPI_INTEGER, &
                       buf, counts, displs, MPI_INTEGER, 0, MPI_COMM_WORLD)
   end subroutine par_gather_to_i

   subroutine par_gather_edge_to(buf, a)
      ! エッジ配列の rank0 集約(save 用)。エッジ行 js..je を各ランクが送り、
      ! 行 jw1-1 は rank0 が自前の値で埋める(共有行は南北同値)。
      ! buf は rank0 のみ全域 (1:4, 0:nx, 0:ny)。帯外は変更しない。
      real, intent(inout) :: buf(1:, 0:, 0:)
      real, intent(in) :: a(1:, 0:, dcp%jsh-1:)
      integer :: counts(0:nproc-1), displs(0:nproc-1)
      integer :: r, js_r, je_r, n12
      n12 = size(a, 1) * size(a, 2)
      do r = 0, nproc - 1
         call band_range(r, js_r, je_r)
         counts(r) = n12 * (je_r - js_r + 1)
         displs(r) = n12 * js_r
      end do
      call MPI_Gatherv(a(:, :, dcp%js:dcp%je), counts(nrank), MPI_WP, &
                       buf, counts, displs, MPI_WP, 0, MPI_COMM_WORLD)
      if (is_root) buf(:, :, dcp%js-1) = a(:, :, dcp%js-1)
   end subroutine par_gather_edge_to

   subroutine par_scatter_cell(buf, a)
      ! rank0 の全域バッファ buf(1:nx, 1:ny) を各ランクの帯+ハロ
      ! a(:, jsh:jeh) へ配布する(gather の逆向き。初期化・復元用)。
      ! 帯+ハロは隣接ランクと重なるため Scatterv は使えず、rank0 からの
      ! 個別送信で配る(初期化の1回きりで性能は問題にならない)。
      ! rank0 以外の buf は参照されないためサイズ1のダミーでよい。
      ! 受信側 a は確保範囲(jsh:jeh)ちょうどで確保しておくこと。
      real, intent(in) :: buf(1:, 1:)
      real, intent(inout) :: a(1:, dcp%jsh:)
      integer :: r, jsh_r, jeh_r, n1
      n1 = size(a, 1)
      if (is_root) then
         do r = 1, nproc - 1
            call band_range_h(r, jsh_r, jeh_r)
            call MPI_Send(buf(:, jsh_r:jeh_r), n1 * (jeh_r - jsh_r + 1), &
                          MPI_WP, r, 21, MPI_COMM_WORLD)
         end do
         a(:, dcp%jsh:dcp%jeh) = buf(:, dcp%jsh:dcp%jeh)
      else
         call MPI_Recv(a, size(a), MPI_WP, 0, 21, MPI_COMM_WORLD, &
                       MPI_STATUS_IGNORE)
      end if
   end subroutine par_scatter_cell

   subroutine par_scatter_cell_i(buf, a)
      ! par_scatter_cell の整数版(マスク・土地利用等)
      integer, intent(in) :: buf(1:, 1:)
      integer, intent(inout) :: a(1:, dcp%jsh:)
      integer :: r, jsh_r, jeh_r, n1
      n1 = size(a, 1)
      if (is_root) then
         do r = 1, nproc - 1
            call band_range_h(r, jsh_r, jeh_r)
            call MPI_Send(buf(:, jsh_r:jeh_r), n1 * (jeh_r - jsh_r + 1), &
                          MPI_INTEGER, r, 22, MPI_COMM_WORLD)
         end do
         a(:, dcp%jsh:dcp%jeh) = buf(:, dcp%jsh:dcp%jeh)
      else
         call MPI_Recv(a, size(a), MPI_INTEGER, 0, 22, MPI_COMM_WORLD, &
                       MPI_STATUS_IGNORE)
      end if
   end subroutine par_scatter_cell_i

   subroutine par_scatter_edge(buf, a)
      ! rank0 の全域エッジバッファ buf(1:4, 0:nx, 0:ny) を各ランクの
      ! エッジ確保範囲 a(:, :, jsh-1:jeh) へ配布する(restore 用。
      ! par_gather_edge_to の逆向き)。帯+ハロは隣接ランクと重なるため
      ! par_scatter_cell と同じく rank0 からの個別送信で配る。
      ! rank0 以外の buf は参照されないためサイズ1のダミーでよい。
      ! 受信側 a はエッジ確保範囲(jsh-1:jeh)ちょうどで確保しておくこと。
      real, intent(in) :: buf(1:, 0:, 0:)
      real, intent(inout) :: a(1:, 0:, dcp%jsh-1:)
      integer :: r, jsh_r, jeh_r, n12
      n12 = size(a, 1) * size(a, 2)
      if (is_root) then
         do r = 1, nproc - 1
            call band_range_h(r, jsh_r, jeh_r)
            call MPI_Send(buf(:, :, jsh_r-1:jeh_r), n12 * (jeh_r - jsh_r + 2), &
                          MPI_WP, r, 23, MPI_COMM_WORLD)
         end do
         a(:, :, dcp%jsh-1:dcp%jeh) = buf(:, :, dcp%jsh-1:dcp%jeh)
      else
         call MPI_Recv(a, size(a), MPI_WP, 0, 23, MPI_COMM_WORLD, &
                       MPI_STATUS_IGNORE)
      end if
   end subroutine par_scatter_edge

   subroutine par_reduce_points(vals)
      ! 点計測値の rank0 集約(m_record 用)。
      ! 各要素は「所有ランクがちょうど1つだけ値を格納し、他ランクは 0」の
      ! 規約で使う。総和 = 所有値 + 0 = 所有値そのもの(x+0 は IEEE で
      ! ビット厳密)なので、rank0 は逐次版と同一の値を同一の順で読める。
      real, intent(inout) :: vals(:, :)
      real :: dum(1, 1)
      if (is_root) then
         call MPI_Reduce(MPI_IN_PLACE, vals, size(vals), MPI_WP, MPI_SUM, &
                         0, MPI_COMM_WORLD)
      else
         call MPI_Reduce(vals, dum, size(vals), MPI_WP, MPI_SUM, &
                         0, MPI_COMM_WORLD)
      end if
   end subroutine par_reduce_points

   subroutine par_bcast_cell(a)
      ! rank0 の配列を全ランクへ配布(user フック後の再配布等)。
      ! 注意: 全ランク同形の配列(全域一時配列)にのみ使うこと。
      ! 帯確保の配列に使うとランク毎にサイズが異なり Bcast が破綻する。
      real, intent(inout) :: a(1:, 1:)
      call MPI_Bcast(a, size(a), MPI_WP, 0, MPI_COMM_WORLD)
   end subroutine par_bcast_cell

   subroutine par_bcast_cell_i(a)
      ! par_bcast_cell の整数版(user フック後のマスク類の再配布用)。
      ! 全ランク同形の配列にのみ使うこと。
      integer, intent(inout) :: a(1:, 1:)
      call MPI_Bcast(a, size(a), MPI_INTEGER, 0, MPI_COMM_WORLD)
   end subroutine par_bcast_cell_i

   subroutine par_bcast_edge(a)
      ! rank0 のエッジ配列を全ランクへ配布(現在未使用。restore は
      ! par_scatter_edge に移行済み。全ランク同形が必要な用途に残置)。
      ! 注意: 全ランク同形の配列(全域一時配列)にのみ使うこと。
      real, intent(inout) :: a(1:, 0:, 0:)
      call MPI_Bcast(a, size(a), MPI_WP, 0, MPI_COMM_WORLD)
   end subroutine par_bcast_edge

   subroutine par_finalize()
      call MPI_Finalize()
   end subroutine par_finalize

   subroutine par_info(msg)
      ! 進捗・情報メッセージ: ランク0のみ標準出力に表示
      character(*), intent(in) :: msg
      if (is_root) then
         write(output_unit,'(a)') trim(msg)
         flush(output_unit)
      end if
   end subroutine par_info

   subroutine par_warn(msg)
      ! 局所的な警告: 検出したランクがランク番号付きで表示(停止しない)
      character(*), intent(in) :: msg
      write(error_unit,'(a,i0,2a)') 'WARNING (rank ', nrank, '): ', trim(msg)
      flush(error_unit)
   end subroutine par_warn

   subroutine par_stop(msg)
      ! 決定的エラー用: 全ランクが同時に検出する種類のエラー(設定関連)。
      ! 必ず全ランクが揃って呼ぶこと(collective)。
      ! ランク0が表示し、finalize を通して終了コード1で停止する。
      character(*), intent(in) :: msg
      if (is_root) then
         write(error_unit,'(2a)') 'ERROR: ', trim(msg)
         flush(error_unit)
      end if
      call MPI_Barrier(MPI_COMM_WORLD)
      call MPI_Finalize()
      stop 1
   end subroutine par_stop

   subroutine par_abort(msg)
      ! 局所エラー用: 検出したランクだけが呼んでよい。
      ! ランク番号付きで表示して全ランクを即時強制終了する。
      character(*), intent(in) :: msg
      write(error_unit,'(a,i0,2a)') 'ABORT (rank ', nrank, '): ', trim(msg)
      flush(error_unit)
      call MPI_Abort(MPI_COMM_WORLD, 1)
   end subroutine par_abort

   subroutine par_barrier()
      ! 全ランク同期(通常の計算では不要。時間計測・デバッグ用)
      call MPI_Barrier(MPI_COMM_WORLD)
   end subroutine par_barrier

   subroutine par_allreduce_min(val)
      ! 全ランク最小値(CFL の Δt 決定用)
      real, intent(inout) :: val
      call MPI_Allreduce(MPI_IN_PLACE, val, 1, MPI_WP, MPI_MIN, &
                         MPI_COMM_WORLD)
   end subroutine par_allreduce_min

end module m_parallel
