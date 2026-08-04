module m_gwflow
  ! ================= 地下水プロセスモジュール(切替器) =================
  ! 複数の地下水モデル(バケツ / Boussinesq / RRI 型 / 鉛直浸透重視型 …)
  ! を排他切替で使う。m_swflow の enc/stg 切替と同じ構造:
  !   - 有効化は fn_gwflow の指定の有無(未指定なら完全に不活性)
  !   - モデル選択は fn_gwflow 内の &list_gwflow の f_gwmodel
  !     (0 なら fn を書いたまま一時無効化できる)
  !   - 束縛は t_gwflow の手続きポインタ成分(abstract interface + nopass)
  !   - 各モデルの固有設定・内部状態・リスタスタート保存はモデル私有
  !     (実装の契約は m_gwflow_bucket のヘッダを参照)
  ! 呼び出し順: swflow(流れ)→ gwflow(水収支)→ geomorph(地形)
  ! ====================================================================
  use m_sysparam, only : t_sysparam
  use m_geoinfo, only : t_geoinfo
  use m_state, only : t_state
  use list_gwflow, only : t_list_gwflow, list_gwflow_read
  use m_gwflow_bucket, only : gwflow_bucket_init, gwflow_bucket_calc, gwflow_bucket_dispose
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

    subroutine procedure_gwflow_calc(p, g, s, it)
      import :: t_sysparam, t_geoinfo, t_state
      type(t_sysparam), intent(in) :: p
      type(t_geoinfo), intent(in) :: g
      type(t_state), intent(inout) :: s
      integer, intent(in) :: it
    end subroutine

    subroutine procedure_gwflow_dispose(p)
      import :: t_sysparam
      type(t_sysparam), intent(in) :: p
    end subroutine
  end interface
  !-------------------------------------------


  type t_gwflow
    ! init に早期 return 経路があるため全成分デフォルト初期化必須(§13)
    procedure(procedure_gwflow_init),    pointer, nopass :: init    => null()
    procedure(procedure_gwflow_calc),    pointer, nopass :: calc    => null()
    procedure(procedure_gwflow_dispose), pointer, nopass :: dispose => null()
    logical :: enabled = .false.     ! fn_gwflow の有無と f_gwmodel で決まる
    integer :: idt_gwflow = 1        ! 更新間隔(ステップ数)
    logical :: initialized = .false.
  end type

contains


!----------------------------------------------------------------------
! 地下水モジュールを初期化する
!   fn_gwflow 未指定 or f_gwmodel=0 なら何もしない(enabled = .false.)
!----------------------------------------------------------------------
subroutine m_gwflow_init(gw, p, g, s)
  type(t_gwflow), intent(out) :: gw
  type(t_sysparam), intent(in) :: p
  type(t_geoinfo), intent(in) :: g
  type(t_state), intent(inout) :: s
  type(t_list_gwflow) :: list

  if (len_trim(p%fn_gwflow) == 0) return

  call list_gwflow_read(p, list)

  if (list%f_gwmodel == 0) return    ! fn を書いたまま一時無効化する経路

  ! --- モデルの束縛(新モデルの追加はここに case を足す) ---
  select case (list%f_gwmodel)
    case (1)
      gw%init    => gwflow_bucket_init
      gw%calc    => gwflow_bucket_calc
      gw%dispose => gwflow_bucket_dispose
    case default
      call par_stop("list_gwflow: f_gwmodel must be 0(none) or 1(bucket): " &
                    // itoa(list%f_gwmodel))
  end select

  ! --- 共通制御の解釈 ---
  if (list%dt_gwflow > 0.0) then
    gw%idt_gwflow = nint(list%dt_gwflow / p%dt)
    if (gw%idt_gwflow <= 0) call par_stop("list_gwflow: dt_gwflow must be >= dt")
  else
    gw%idt_gwflow = 1
  end if

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
  call gw%calc(p, g, s, it)
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
