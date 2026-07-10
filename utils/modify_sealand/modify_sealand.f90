!
! 海陸マスクを修正
!
!   流出河川のない大きな湖沼の中に海域を設定することで排水する
!
program modify_sealand
  implicit none
  integer, parameter :: nx = 6080
  integer, parameter :: ny = 8960
  integer :: sw(1:nx,1:ny)    ! 河道マスク
  integer :: ix, iy

  ! 修正前の海陸マスクの読み込み
  open(1, file="SeaLand250_20251123.bil", form='unformatted', status='old', access='stream')
  read(1) sw
  close(1)

  ! 阿寒湖
  ix = 5292
  iy = 1161
  sw(ix,iy) = 1
  ix = 5297
  iy = 1167
  sw(ix,iy) = 1

  ! キンムトー(湯沼)
  ix = 5251
  iy = 1154
  sw(ix,iy) = 1

  ! パンケトー
  ix = 5180
  iy = 1210
  sw(ix,iy) = 1

  ! 倶多楽湖
  ix = 4219
  iy = 1680
  sw(ix,iy) = 1

  ! 田沢湖
  ix = 4052
  iy = 3012
  sw(ix,iy) = 1

  ! 三宅島
  ix = 3689
  iy = 5718
  sw(ix,iy) = 1

  ! 刈込湖・切込湖
  ix = 3660
  iy = 4405
  sw(ix,iy) = 1
  ix = 3665
  iy = 4408
  sw(ix,iy) = 1

  ! 五色沼
  ix = 3643
  iy = 4416
  sw(ix,iy) = 1

  ix = 3665
  ! 精進湖
  ix = 3396
  iy = 5047
  sw(ix,iy) = 1

  ! 本栖湖
  ix = 3388
  iy = 5058
  sw(ix,iy) = 1

  ! 修正済みの河道マスクの書き込み
  open(1, file="SeaLand250_20251127.bil", form='unformatted', status='replace', access='stream')
  write(1) sw
  close(1)

end program
