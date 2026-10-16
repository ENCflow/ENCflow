!======================================================================
! m_restart — save/restore の集約・配布と RLE 入出力を束ねる(developer.md §83)
!
!   各モジュールは帯配列(セル a(ish:, jsh:)、エッジ a(1:, ish-1:, jsh-1:))を
!   そのまま渡す。rank0 は窓形の一時(セル (ish:ieh, jw1:jw2)、エッジ
!   (:, ish-1:ieh, jw1-1:jw2)。復元側は行が jwh1..jwh2)だけを持ち、全域の
!   RLE ストリームは窓形から直接符号化・復号する(m_fileio の *_rle_win)。
!   ファイル形式(全域の要素数・run 表)は旧 save と不変。
!
!   すべて collective(全ランクが同じ順序で呼ぶ)。装置番号 un は rank0 で
!   だけ有効(他ランクの値は参照しない)。
!   fill は save 時の窓外の値(既定 0。旧実装が全域バッファを 1.0 で初期化
!   していた表(fwd, cwxd/cwyd)は 1.0 を与えるとバイト互換。fill が非ゼロの
!   場はリテラルが全域ぶんになる = ファイルと同じ O(N) の一時)
!======================================================================
module m_restart
  use, intrinsic :: iso_fortran_env, only : int64
  use m_parallel
  use m_fileio, only : fileio_write_rle_win, fileio_read_rle_win, &
                       fileio_write_rle_zero, fileio_skip_rle
  implicit none
  private
  public :: restart_write_cell, restart_read_cell
  public :: restart_write_edge, restart_read_edge
  public :: restart_write_zero, restart_skip

contains

!----------------------------------------------------------------------
! セル配列を書く(窓形へ gather → RLE)
!----------------------------------------------------------------------
subroutine restart_write_cell(un, a, fill)
  integer, intent(in) :: un
  real, intent(in) :: a(dcp%ish:, dcp%jsh:)
  real, intent(in), optional :: fill
  real, allocatable :: w(:,:)
  if (is_root) then
    allocate(w(dcp%ish:dcp%ieh, dcp%jw1:dcp%jw2))
  else
    allocate(w(1, 1))                  ! 参照されないダミー
  end if
  call par_gather_win(w, a)
  if (is_root) call fileio_write_rle_win(un, w, dcp%nx_g, dcp%ny_g, dcp%ish, dcp%jw1, fill)
end subroutine


!----------------------------------------------------------------------
! セル配列を読む(RLE → 窓形(行は窓±ハロ)→ scatter で帯+ハロへ)
!----------------------------------------------------------------------
subroutine restart_read_cell(un, a)
  integer, intent(in) :: un
  real, intent(inout) :: a(dcp%ish:, dcp%jsh:)
  real, allocatable :: w(:,:)
  if (is_root) then
    allocate(w(dcp%ish:dcp%ieh, dcp%jwh1:dcp%jwh2))
    call fileio_read_rle_win(un, w, dcp%nx_g, dcp%ny_g, dcp%ish, dcp%jwh1)
  else
    allocate(w(1, 1))
  end if
  call par_scatter_win(w, a)
end subroutine


!----------------------------------------------------------------------
! エッジ配列 (k, i, j) を書く。全域の形は (nk, 0:nx, 0:ny) = フラット次元
! (nk, nx+1, ny+1)。窓 (:, ish-1:ieh, jw1-1:jw2) のフラット位置は (ish, jw1)
!----------------------------------------------------------------------
subroutine restart_write_edge(un, a, fill)
  integer, intent(in) :: un
  real, intent(in) :: a(1:, dcp%ish-1:, dcp%jsh-1:)
  real, intent(in), optional :: fill
  real, allocatable :: w(:,:,:)
  if (is_root) then
    allocate(w(size(a, 1), dcp%ish-1:dcp%ieh, dcp%jw1-1:dcp%jw2))
  else
    allocate(w(1, 1, 1))
  end if
  call par_gather_edge_win(w, a)
  if (is_root) call fileio_write_rle_win(un, w, size(a, 1), dcp%nx_g + 1, dcp%ny_g + 1, &
                                         dcp%ish, dcp%jw1, fill)
end subroutine


!----------------------------------------------------------------------
! エッジ配列を読む(窓 (:, ish-1:ieh, jwh1-1:jwh2) → scatter)
!----------------------------------------------------------------------
subroutine restart_read_edge(un, a)
  integer, intent(in) :: un
  real, intent(inout) :: a(1:, dcp%ish-1:, dcp%jsh-1:)
  real, allocatable :: w(:,:,:)
  if (is_root) then
    allocate(w(size(a, 1), dcp%ish-1:dcp%ieh, dcp%jwh1-1:dcp%jwh2))
    call fileio_read_rle_win(un, w, size(a, 1), dcp%nx_g + 1, dcp%ny_g + 1, dcp%ish, dcp%jwh1)
  else
    allocate(w(1, 1, 1))
  end if
  call par_scatter_edge_win(w, a)
end subroutine


!----------------------------------------------------------------------
! 全域ゼロのセル場を書く(未使用成分の形式固定用)
!----------------------------------------------------------------------
subroutine restart_write_zero(un)
  integer, intent(in) :: un
  if (is_root) call fileio_write_rle_zero(un, int(dcp%nx_g, int64) * dcp%ny_g)
end subroutine


!----------------------------------------------------------------------
! 1 配列ぶんを読み飛ばす(復元側で使わない成分)
!----------------------------------------------------------------------
subroutine restart_skip(un)
  integer, intent(in) :: un
  if (is_root) call fileio_skip_rle(un)
end subroutine

end module
