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
!   - par_decomp_init(nx, ny, jw1, jw2) で設定する(格子サイズ確定後、
!     m_geoinfo_init の直後に呼ぶこと)
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
!   - 本プロジェクトは -r8 等で既定 real を8バイトに昇格している
!     ため、MPI データ型は MPI_REAL でなく必ず MPI_REAL8 を使う。
!     (通信を書くときは下の MPI_WP を使うこと)
!   - OpenMP 併用のため MPI_Init_thread で FUNNELED を要求する。
!     (MPI 呼び出しはマスタースレッドのみ、が前提)
!   - エラー・警告を error_unit に出すのは意図的(tee で作る
!     Log.txt =回帰テストの比較対象= に混入させないため)
!=====================================================================
   use mpi_f08
   use, intrinsic :: iso_fortran_env, only: output_unit, error_unit
   implicit none
   private
   public :: par_init, par_finalize
   public :: par_decomp_init
   public :: par_info, par_warn, par_stop, par_abort
   public :: par_barrier
   public :: par_allreduce_min
   public :: par_halo_cell, par_halo_edge, par_edge_merge
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

   ! 実数通信用データ型(既定 real = 8バイト前提)
   type(MPI_Datatype), parameter :: MPI_WP = MPI_REAL8

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
   end subroutine par_init

   subroutine par_decomp_init(nx, ny, jw1, jw2)
      ! 領域分割の決定。格子サイズと有効窓の確定後
      ! (m_geoinfo_init の直後)に全ランクが揃って呼ぶこと(collective)。
      ! 全域窓 [jw1, jw2] をランク数で行分割し、自ランクの帯を決める。
      ! 第一段: 配列は全域確保のまま(jsh/jeh は 1..ny。第二段で
      !         js-nhalo..je+nhalo へ縮小する)
      integer, intent(in) :: nx, ny
      integer, intent(in) :: jw1, jw2   ! 全域の有効窓(= g%wy(1:2))
      integer :: nrows, base, rem
      character(len=1024) :: buf
      dcp%nx_g = nx
      dcp%ny_g = ny
      dcp%jw1 = jw1
      dcp%jw2 = jw2
      nrows = jw2 - jw1 + 1
      ! 各帯は最低2行必要(ハロ交換が隣の隣を参照しない前提のため)
      if (nrows < 2 * nproc) then
         write(buf,'(a,i0,a,i0,a)') 'domain too small for ', nproc, &
            ' ranks: window has ', nrows, ' rows (need >= 2 rows per rank)'
         call par_stop(trim(buf))       ! 全ランク同一の判定なので collective 安全
      end if
      base = nrows / nproc
      rem  = mod(nrows, nproc)
      dcp%js = jw1 + nrank * base + min(nrank, rem)
      dcp%je = dcp%js + base - 1
      if (nrank < rem) dcp%je = dcp%je + 1
      dcp%jsh = 1
      dcp%jeh = ny
      dcp%rank_s = nrank - 1                            ! nrank=0 では -1(隣なし)
      dcp%rank_n = merge(nrank + 1, -1, nrank < nproc - 1)
   end subroutine par_decomp_init

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
