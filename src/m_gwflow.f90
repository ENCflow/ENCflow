module m_gwflow
  ! ================= 地下水プロセスモジュール(切替器) =================
  ! 鉛直浸透・貯留(vertical)と側方流動(lateral)の2群を持ち、それぞれ
  ! 複数のモデルを排他切替で使う(handoff_gwflow_tani.md §2.2)。
  !   - 有効化は fn_gwflow の指定の有無(未指定なら完全に不活性)
  !   - 鉛直モデルは fn_gwflow 内 &list_gwflow の f_gwvertical で選択
  !     (0 なら fn を書いたまま一時無効化できる)
  !   - 側方モデルは同 f_gwlateral で選択。未指定(=0)なら鉛直のみで
  !     実行し、側方流動のための資源(束縛・配列・ハロ交換)は一切
  !     確保しない(現段階では 0 のみ受理。1以降は予約・未実装)
  !   - 束縛は t_gwflow の手続きポインタ成分(abstract interface + nopass)
  !   - 各モデルの固有設定・内部状態・リスタート保存はモデル私有
  !     (実装の契約は m_gwflow_bucket のヘッダを参照)
  !   - 土層厚 g%sd を要するモデルを選んだときは、モデル init より前に
  !     m_geoinfo_require_sd で帯配列を要求する(developer.md §16)
  ! 呼び出し順: swflow(流れ)→ gwflow(水収支)→ geomorph(地形)
  ! ====================================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo, m_geoinfo_require_sd
  use m_state, only : t_state
  use list_gwflow, only : t_list_gwflow, list_gwflow_read
  use m_gwflow_bucket, only : gwflow_bucket_init, gwflow_bucket_calc, gwflow_bucket_dispose
  use m_gwflow_greenampt, only : gwflow_greenampt_init, gwflow_greenampt_calc, &
                                 gwflow_greenampt_dispose
  use m_parallel, only : par_stop
  use m_util, only : itoa
  implicit none
  private
  public :: t_gwflow
  public :: m_gwflow_init
  public :: m_gwflow_calc
  public :: m_gwflow_dispose

  !-------------------------------------------
  ! 地下水モデルのインターフェース
  ! (型成分で参照するため、型定義より前に置くこと)
  !-------------------------------------------
  abstract interface
    subroutine procedure_gwflow_init(p, g, s)
      import :: t_sysparam, t_geoinfo, t_state
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(inout) :: s
    end subroutine

    subroutine procedure_gwflow_calc(p, g, s, it, dts)
      import :: t_sysparam, t_geoinfo, t_state
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(inout) :: s
      integer, intent(in) :: it
      real, intent(in) :: dts        ! 実効時間刻み(p%dt * idt_gwflow)(s)
    end subroutine

    subroutine procedure_gwflow_dispose(p)
      import :: t_sysparam
      type(t_sysparam), intent(in) :: p
    end subroutine
  end interface
  !-------------------------------------------


  type t_gwflow
    ! init に早期 return 経路があるため全成分デフォルト初期化必須(§13)
    ! 現在の init/calc/dispose は鉛直モデルの束縛。側方モデルの導入時は
    ! 側方用のポインタ束を並置する(f_gwlateral=0 なら null のまま)
    procedure(procedure_gwflow_init),    pointer, nopass :: init    => null()
    procedure(procedure_gwflow_calc),    pointer, nopass :: calc    => null()
    procedure(procedure_gwflow_dispose), pointer, nopass :: dispose => null()
    logical :: enabled = .false.     ! fn_gwflow の有無と f_gwvertical で決まる
    integer :: idt_gwflow = 1        ! 更新間隔(ステップ数)
    real :: dts = 0.0                ! 実効時間刻み(p%dt * idt_gwflow)(s)
    logical :: initialized = .false.
  end type

contains


!----------------------------------------------------------------------
! 地下水モジュールを初期化する
!   fn_gwflow 未指定 or f_gwvertical=0 なら何もしない(enabled = .false.)
!   g は m_geoinfo_require_sd(土層厚の遅延確保)のため inout
!----------------------------------------------------------------------
subroutine m_gwflow_init(gw, p, g, s)
  type(t_gwflow), intent(out) :: gw
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(inout) :: g
  type(t_state), intent(inout) :: s
  type(t_list_gwflow) :: list
  logical :: needs_sd

  if (len_trim(p%fn_gwflow) == 0) return

  call list_gwflow_read(p, list)

  ! 側方モデルは予約のみ(パラメータ体系を先に確定。実装は優先順位2)
  if (list%f_gwlateral /= 0) then
    call par_stop("list_gwflow: f_gwlateral is not implemented yet, must be 0: " &
                  // itoa(list%f_gwlateral))
  end if

  if (list%f_gwvertical == 0) return    ! fn を書いたまま一時無効化する経路

  ! --- 鉛直モデルの束縛(新モデルの追加はここに case を足す) ---
  needs_sd = .false.
  select case (list%f_gwvertical)
    case (1)
      gw%init    => gwflow_bucket_init
      gw%calc    => gwflow_bucket_calc
      gw%dispose => gwflow_bucket_dispose
    case (2)
      gw%init    => gwflow_greenampt_init
      gw%calc    => gwflow_greenampt_calc
      gw%dispose => gwflow_greenampt_dispose
      needs_sd = .true.
    case default
      call par_stop("list_gwflow: f_gwvertical must be 0(none), 1(bucket) or 2(greenampt): " &
                    // itoa(list%f_gwvertical))
  end select

  ! --- 共通制御の解釈 ---
  if (list%dt_gwflow > 0.0) then
    gw%idt_gwflow = nint(list%dt_gwflow / p%dt)
    if (gw%idt_gwflow <= 0) call par_stop("list_gwflow: dt_gwflow must be >= dt")
  else
    gw%idt_gwflow = 1
  end if
  gw%dts = p%dt * gw%idt_gwflow

  ! 土層厚を要するモデルの遅延確保口(モデル init より前に。§16)
  if (needs_sd) call m_geoinfo_require_sd(g)

  gw%enabled = .true.
  s%gw_active = .true.               ! 質量台帳(S_grnd/S_total)と Log 列の拡張を有効化
  call gw%init(p, g, s)
  gw%initialized = .true.
end subroutine


!----------------------------------------------------------------------
! 地下水を計算する(run_main から毎ステップ呼ばれる)
!   冒頭の return 判定は全ランクで同一(collective 安全)
!----------------------------------------------------------------------
subroutine m_gwflow_calc(gw, p, g, s, it)
  type(t_gwflow), intent(in) :: gw
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  integer, intent(in) :: it

  if (.not. gw%enabled) return
  if (mod(it, gw%idt_gwflow) /= 0) return
  call gw%calc(p, g, s, it, gw%dts)
end subroutine


!----------------------------------------------------------------------
! 地下水モジュールを破棄する
!----------------------------------------------------------------------
subroutine m_gwflow_dispose(gw, p)
  type(t_gwflow), intent(inout) :: gw
  type(t_sysparam), intent(in) :: p
  if (gw%enabled) call gw%dispose(p)
  gw%init    => null()
  gw%calc    => null()
  gw%dispose => null()
  gw%enabled = .false.
  gw%initialized = .false.
end subroutine

end module
