module m_geomorph
  ! ================= 地形変化プロセスモジュール =================
  ! 河道床の浸食・堆積、badland の浸食、斜面クリープなど、複数の
  ! 地形変化モデルを「重ね合わせ可能なプロセス」として実装する場所。
  !
  ! 設計方針:
  !   - 有効化は list_sysparam の fn_geomorph 指定の有無で決まる
  !     (precip/record と同じ流儀。未指定なら本モジュールは完全に不活性)
  !   - プロセスは排他選択でなく独立フラグの重ね合わせ(演算子分割)。
  !     新モデルの追加 = 「フラグ+パラメータ+サブルーチン1本」で閉じ、
  !     既存プロセスには触れない
  !   - 更新は dt_geomorph 間隔の間欠実行(流れと地形の時定数分離)
  !
  ! MPI 規約(developer.md §11):
  !   - s%z の更新は自帯 js..je のみ(owner-compute)
  !   - calc の末尾で s%z のハロ交換を行う(次回の自プロセスの近傍参照と、
  !     流れの重力項の近傍参照の両方がこれで賄われる)
  !   - enabled / idt の実行判定は全ランクで同一(collective 安全)
  !   - s%z を更新したら s%e の整合を必ず回復する(河床が変化しても
  !     水面 e でなく水深 h を保存する、が本モジュールの契約)
  ! ==============================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use list_geomorph, only : t_list_geomorph, list_geomorph_read
  use m_parallel, only : par_info, par_stop, dcp, par_halo_cell
  implicit none
  private
  public :: t_geomorph
  public :: m_geomorph_init
  public :: m_geomorph_calc
  public :: m_geomorph_dispose

  type t_geomorph
    ! init に早期 return 経路があるため全成分デフォルト初期化必須(§13)
    logical :: enabled = .false.     ! fn_geomorph 指定の有無で決まる
    integer :: idt_geomorph = 1      ! 更新間隔(ステップ数)
    integer :: f_creep = 0           ! 斜面クリープ(0:無効, 1:有効)
    real :: creep_d = 0.0            ! クリープ拡散係数 (m2/s)
    logical :: initialized = .false.
  end type

contains


!----------------------------------------------------------------------
! 地形変化モジュールを初期化する
!   fn_geomorph が未指定なら何もしない(enabled = .false. のまま)
!----------------------------------------------------------------------
subroutine m_geomorph_init(gm, p, g)
  type(t_geomorph), intent(out) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_list_geomorph) :: list

  if (g%initialized) continue  ! 引数未使用の警告を抑制(帯確保後の g を将来使う)

  ! 設定ファイル未指定 = 地形変化なし(デフォルトの enabled = .false.)
  if (len_trim(p%fn_geomorph) == 0) return

  call list_geomorph_read(p, list)

  ! --- 解釈と検証(設定ファイル由来の決定的エラーは par_stop で即停止) ---
  if (list%dt_geomorph > 0.0) then
    gm%idt_geomorph = nint(list%dt_geomorph / p%dt)
    if (gm%idt_geomorph <= 0) then
      call par_stop("list_geomorph: dt_geomorph must be >= dt")
    end if
  else
    gm%idt_geomorph = 1                          ! 毎ステップ更新
  end if

  gm%f_creep = list%f_creep
  if (gm%f_creep > 0) then
    if (list%creep_d <= 0.0) then
      call par_stop("list_geomorph: f_creep requires creep_d > 0")
    end if
    gm%creep_d = list%creep_d
  end if

  ! (将来のプロセスの検証をここに追加する)

  gm%enabled = .true.
  gm%initialized = .true.
end subroutine


!----------------------------------------------------------------------
! 地形変化を計算する(dt_geomorph 間隔で run_main から毎ステップ呼ばれる)
!   有効なプロセスを順に適用して s%z を更新する(演算子分割)。
!   注意: 冒頭の return 判定はすべて全ランクで同一(collective 安全)
!----------------------------------------------------------------------
subroutine m_geomorph_calc(gm, p, g, s, it)
  type(t_geomorph), intent(in) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it
  integer :: i, j

  if (.not. gm%enabled) return
  if (mod(it, gm%idt_geomorph) /= 0) return

  ! --- 有効なプロセスを順に適用(それぞれ自帯 js..je の s%z を更新) ---
  if (gm%f_creep > 0) call calc_creep(gm, p, g, s)
  ! (将来のプロセスの適用をここに追加する)

  ! --- s%e の整合を回復する(本モジュールは水深 h を保存する契約) ---
  !$omp parallel do schedule(static) private(i, j)
  do j = dcp%js, dcp%je
    do i = g%wx(1,j), g%wx(2,j)
      if (g%x(i,j) <= 0) cycle
      s%e(i,j) = s%z(i,j) + s%h(i,j)
    end do
  end do
  !$omp end parallel do

  ! --- s%z のハロ交換 ---
  ! 自プロセスの次回の近傍参照(クリープの ±1)と、流れの重力項の
  ! 近傍参照の両方が、この1回の交換で賄われる(developer.md §11)
  call par_halo_cell(s%z)

end subroutine


!----------------------------------------------------------------------
! 斜面クリープ(線形拡散 dz/dt = D * div(grad z))
!   TODO: 実装。骨格の契約:
!     - 読み: s%z の自セルと ±1 近傍(ハロは前回 calc 末尾の交換で有効)
!     - 書き: 自帯 js..je のみ。全域窓の端は ±1 縮小規則でクリップ
!       (do j = max(dcp%js, dcp%jw1+1), min(dcp%je, dcp%jw2-1) の定型)
!     - 更新前の z を読みながら更新する競合を避けるため、二重バッファか
!       Δz ワーク配列を使うこと(mn1 方式と同じ理由)
!     - 検証: 解析解(ガウス丘の拡散)とのベンチマークケースを新設する
!----------------------------------------------------------------------
subroutine calc_creep(gm, p, g, s)
  type(t_geomorph), intent(in) :: gm
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s

  if (p%initialized) continue  ! 引数未使用の警告を抑制
  if (g%initialized) continue  ! 引数未使用の警告を抑制
  if (s%initialized) continue  ! 引数未使用の警告を抑制
  if (gm%creep_d > 0.0) continue

  call par_stop("m_geomorph: f_creep is not implemented yet")

end subroutine


!----------------------------------------------------------------------
! 地形変化モジュールを破棄する
!----------------------------------------------------------------------
subroutine m_geomorph_dispose(gm)
  type(t_geomorph), intent(inout) :: gm
  gm%enabled = .false.
  gm%initialized = .false.
end subroutine

end module
