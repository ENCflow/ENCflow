module m_parallel
!=====================================================================
! 並列層: 逐次(OpenMP)版スタブ
!   m_parallel_mpi.f90 と同一のインターフェースを提供する。
!   両ファイルの公開手続きは常に一致させて保守すること。
!
! メッセージ出力の使い分け(MPI 版と共通のルール):
!   par_info(msg)  進捗・情報。標準出力に表示
!   par_warn(msg)  局所的な警告。標準エラーに表示(停止しない)
!   par_stop(msg)  決定的エラー(設定不正など)。表示して停止
!   par_abort(msg) 局所的な致命的エラー。表示して即時停止
!
! 領域分割情報 dcp(MPI 版と共通のルール):
!   - par_decomp_init(nx, ny, jw1, jw2) で設定する(格子サイズ確定後、
!     m_geoinfo_init の直後に呼ぶこと)。逐次では常に全域を担当する。
!   - 各モジュールは use m_parallel, only: dcp で直接参照してよい
!     (protected 属性により変更は本モジュール内に限定される)
!   - 計算カーネルには dcp を見せず、範囲(js, je 等)を引数で渡す
!   - js/je は「計算範囲(全域窓∩自ランク担当帯)」、jsh/jeh は
!     「配列確保範囲(担当帯+ハロ。現段階は全域 1..ny)」、jw1/jw2 は
!     全域の有効窓。全域窓の端で1行縮めるループは
!       do j = max(dcp%js, dcp%jw1+1), min(dcp%je, dcp%jw2-1)
!     と書くこと(dcp%js+1 と書くと分割後にランク境界まで縮んでしまう)
!=====================================================================
   use, intrinsic :: iso_fortran_env, only: output_unit, error_unit, real64
   implicit none
   private
   public :: par_init, par_finalize
   public :: par_decomp_init
   public :: par_info, par_warn, par_stop, par_abort
   public :: par_barrier
   public :: par_allreduce_min
   public :: par_halo_cell, par_halo_edge, par_edge_merge
   public :: par_allreduce_max, par_allreduce_sumi, par_allreduce_maxi
   public :: par_sum_rows
   public :: par_gather_to, par_gather_to_i, par_gather_edge_to
   public :: par_reduce_points
   public :: par_bcast_cell, par_bcast_edge
   public :: nrank, nproc, is_root
   public :: t_decomp, dcp

   integer, protected, save :: nrank  = 0        ! 自ランク番号(逐次では常に0)
   integer, protected, save :: nproc  = 1        ! 総ランク数(逐次では常に1)
   logical, protected, save :: is_root = .true.  ! 入出力担当ランクか

   ! 領域分割情報(逐次では常に全域。型定義は MPI 版と一致させること)
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

contains

   subroutine par_init()
      ! 何もしない
   end subroutine par_init

   subroutine par_decomp_init(nx, ny, jw1, jw2)
      ! 領域分割の決定。格子サイズと有効窓の確定後
      ! (m_geoinfo_init の直後)に呼ぶこと。
      ! 逐次では計算範囲=全域窓、確保範囲=全域。
      integer, intent(in) :: nx, ny
      integer, intent(in) :: jw1, jw2   ! 全域の有効窓(= g%wy(1:2))
      dcp%nx_g = nx
      dcp%ny_g = ny
      dcp%jw1 = jw1
      dcp%jw2 = jw2
      dcp%js  = jw1
      dcp%je  = jw2
      dcp%jsh = 1
      dcp%jeh = ny
      dcp%rank_n = -1
      dcp%rank_s = -1
   end subroutine par_decomp_init

   subroutine par_halo_cell(a)
      ! セル配列の行ハロ交換。逐次では何もしない。
      real, intent(inout) :: a(1:, dcp%jsh:)
      if (size(a) > 0) continue
   end subroutine par_halo_cell

   subroutine par_halo_edge(a)
      ! エッジ配列の行ハロ交換。逐次では何もしない。
      real, intent(inout) :: a(1:, 0:, dcp%jsh-1:)
      if (size(a) > 0) continue
   end subroutine par_halo_edge

   subroutine par_edge_merge(a, take_s, take_n)
      ! 界面エッジ行の成分補完。逐次では何もしない。
      real, intent(inout) :: a(1:, 0:, dcp%jsh-1:)
      logical, intent(in) :: take_s(:)
      logical, intent(in) :: take_n(:)
      if (size(a) > 0 .and. size(take_s) > 0 .and. size(take_n) > 0) continue
   end subroutine par_edge_merge

   subroutine par_allreduce_max(vals)
      ! 全ランク最大値。逐次では何もしない。
      real, intent(inout) :: vals(:)
      if (size(vals) > 0) continue
   end subroutine par_allreduce_max

   subroutine par_allreduce_sumi(ivals)
      ! 全ランク合計。逐次では何もしない。
      integer, intent(inout) :: ivals(:)
      if (size(ivals) > 0) continue
   end subroutine par_allreduce_sumi

   subroutine par_allreduce_maxi(ival)
      ! 全ランク最大値。逐次では何もしない。
      integer, intent(inout) :: ival
      if (ival == 0) continue
   end subroutine par_allreduce_maxi

   subroutine par_sum_rows(rowsum, total)
      ! 行部分和の総和。逐次では従来どおり一括総和する
      ! (MPI 版も rank0 が同じ「全窓行の一括総和」を行う)。
      ! 引数は PREC によらず real64 固定(診断集約の桁落ち防止。
      ! 倍精度ビルドでは real64=既定 real なので単一実装で済む。§1)
      real(real64), intent(in) :: rowsum(dcp%js:)
      real(real64), intent(out) :: total
      total = sum(rowsum)
   end subroutine par_sum_rows

   subroutine par_gather_to(buf, a)
      ! 全域バッファへの集約。逐次では帯(=全域窓)の行を複写する。
      real, intent(inout) :: buf(1:, 1:)
      real, intent(in) :: a(1:, dcp%jsh:)
      buf(:, dcp%js:dcp%je) = a(:, dcp%js:dcp%je)
   end subroutine par_gather_to

   subroutine par_gather_to_i(buf, a)
      ! 全域バッファへの集約(整数版)
      integer, intent(inout) :: buf(1:, 1:)
      integer, intent(in) :: a(1:, dcp%jsh:)
      buf(:, dcp%js:dcp%je) = a(:, dcp%js:dcp%je)
   end subroutine par_gather_to_i

   subroutine par_gather_edge_to(buf, a)
      ! エッジ配列の全域バッファへの集約(js-1 行を含めて複写)
      real, intent(inout) :: buf(1:, 0:, 0:)
      real, intent(in) :: a(1:, 0:, dcp%jsh-1:)
      buf(:, :, dcp%js-1:dcp%je) = a(:, :, dcp%js-1:dcp%je)
   end subroutine par_gather_edge_to

   subroutine par_reduce_points(vals)
      ! 点計測値の rank0 集約。逐次では何もしない
      ! (所有判定 js<=iy<=je は逐次で常に真なので、vals には全点の値が
      !  そのまま入っている)。
      real, intent(inout) :: vals(:, :)
      if (size(vals) > 0) continue
   end subroutine par_reduce_points

   subroutine par_bcast_cell(a)
      ! rank0 からの配布。逐次では何もしない。
      ! (全ランク同形の全域一時配列にのみ使うこと)
      real, intent(inout) :: a(1:, 1:)
      if (size(a) > 0) continue
   end subroutine par_bcast_cell

   subroutine par_bcast_edge(a)
      ! rank0 からの配布。逐次では何もしない。
      ! (全ランク同形の全域一時配列にのみ使うこと)
      real, intent(inout) :: a(1:, 0:, 0:)
      if (size(a) > 0) continue
   end subroutine par_bcast_edge

   subroutine par_finalize()
      ! 何もしない
   end subroutine par_finalize

   subroutine par_info(msg)
      ! 進捗・情報メッセージ: 標準出力に表示
      character(*), intent(in) :: msg
      write(output_unit,'(a)') trim(msg)
      flush(output_unit)
   end subroutine par_info

   subroutine par_warn(msg)
      ! 局所的な警告: 標準エラーに表示(停止しない)
      character(*), intent(in) :: msg
      write(error_unit,'(2a)') 'WARNING: ', trim(msg)
      flush(error_unit)
   end subroutine par_warn

   subroutine par_stop(msg)
      ! 決定的エラー用: 表示して終了コード1で停止
      character(*), intent(in) :: msg
      write(error_unit,'(2a)') 'ERROR: ', trim(msg)
      flush(error_unit)
      stop 1
   end subroutine par_stop

   subroutine par_abort(msg)
      ! 局所エラー用: 表示して即時停止
      character(*), intent(in) :: msg
      write(error_unit,'(2a)') 'ABORT: ', trim(msg)
      flush(error_unit)
      error stop 1
   end subroutine par_abort

   subroutine par_barrier()
      ! 全ランク同期。逐次では何もしない。
   end subroutine par_barrier

   subroutine par_allreduce_min(val)
      ! 全ランク最小値(CFL の Δt 決定用)。逐次では何もしない。
      real, intent(inout) :: val
      if (val > 0.0) continue    ! 未使用引数警告の抑制
   end subroutine par_allreduce_min

end module m_parallel
