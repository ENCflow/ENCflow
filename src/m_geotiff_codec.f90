!======================================================================
! m_geotiff_codec: TIFF 復号コーデック(PackBits / LZW / predictor 復元)
!   m_geotiff の内部部品(docs/geotiff_plan.md §6.1)。
!   ENCflow 本体のどのモジュールにも依存しない。エラーは stat で返し、
!   メッセージ化・abort は上位(m_geotiff / m_fileio)が行う。
!   バッファはバイト列(int8)で受け渡す。int8 は符号付きなので、
!   数値として扱うときは u8()/u2b() で 0..255 と相互変換する。
!======================================================================
module m_geotiff_codec
  use, intrinsic :: iso_fortran_env, only : int8, int32, int64
  implicit none
  private

  public :: gtc_packbits_decode
  public :: gtc_lzw_decode
  public :: gtc_undo_predictor2
  public :: gtc_undo_predictor3

contains

!----------------------------------------------------------------------
! バイト値の符号なし解釈(0..255)とその逆
!----------------------------------------------------------------------
pure function u8(b) result(v)
  integer(int8), intent(in) :: b
  integer :: v
  v = iand(int(b, int32), 255)
end function

pure function u2b(v) result(b)
  integer, intent(in) :: v          ! 0..255
  integer(int8) :: b
  if (v > 127) then
    b = int(v - 256, int8)
  else
    b = int(v, int8)
  end if
end function


!----------------------------------------------------------------------
! PackBits(TIFF 6.0 §9)の復号
!   n = 0..127: 続く n+1 バイトをそのまま出力
!   n = -1..-127: 次の 1 バイトを 1-n 回繰り返す
!   n = -128: 何もしない
!   ubuf が過不足なく埋まらなければ stat=1(破損)
!----------------------------------------------------------------------
subroutine gtc_packbits_decode(cbuf, ubuf, stat)
  integer(int8), intent(in) :: cbuf(:)
  integer(int8), intent(out) :: ubuf(:)
  integer, intent(out) :: stat
  integer(int64) :: i, o, n, nc, nu
  integer :: c

  nc = size(cbuf, kind=int64)
  nu = size(ubuf, kind=int64)
  stat = 1
  i = 1
  o = 0
  do while (o < nu)
    if (i > nc) return
    c = cbuf(i)                            ! 符号付き -128..127
    i = i + 1
    if (c >= 0) then
      n = int(c, int64) + 1
      if (i + n - 1 > nc .or. o + n > nu) return
      ubuf(o+1:o+n) = cbuf(i:i+n-1)
      i = i + n
      o = o + n
    else if (c /= -128) then
      n = 1 - int(c, int64)
      if (i > nc .or. o + n > nu) return
      ubuf(o+1:o+n) = cbuf(i)
      i = i + 1
      o = o + n
    end if
  end do
  stat = 0
end subroutine


!----------------------------------------------------------------------
! TIFF 版 LZW(TIFF 6.0 §13)の復号
!   MSB-first のビット列。コード長 9→12 ビット可変で、テーブルが
!   2^n - 1 に達した時点で切り替える(libtiff と同じ early change)。
!   ClearCode=256, EOI=257, 新規エントリは 258 から。
!   ubuf が埋まるか EOI で終了。不整合は stat=1
!----------------------------------------------------------------------
subroutine gtc_lzw_decode(cbuf, ubuf, stat)
  integer(int8), intent(in) :: cbuf(:)
  integer(int8), intent(out) :: ubuf(:)
  integer, intent(out) :: stat
  integer, parameter :: c_clear = 256, c_eoi = 257, tabsize = 4096
  integer :: prefix(0:tabsize-1)           ! 直前部分列のコード
  integer(int8) :: suffix(0:tabsize-1)     ! 末尾 1 バイト
  integer(int8) :: firstb(0:tabsize-1)     ! 先頭 1 バイト
  integer(int8) :: stack(1:tabsize)
  integer :: sp, nbits, nextcode, code, oldcode, k
  integer(int8) :: fb
  integer(int64) :: nc, nu, o, bitpos

  nc = size(cbuf, kind=int64)
  nu = size(ubuf, kind=int64)
  stat = 1
  o = 0
  bitpos = 0
  nbits = 9
  nextcode = 258
  oldcode = -1

  do k = 0, 255
    firstb(k) = u2b(k)
    suffix(k) = u2b(k)
    prefix(k) = -1
  end do

  do while (o < nu)
    code = getbits(nbits)
    if (code < 0) return                   ! ビット列が尽きた(不足)
    if (code == c_eoi) return              ! 出力不足のまま EOI
    if (code == c_clear) then
      nbits = 9
      nextcode = 258
      oldcode = -1
      cycle
    end if

    if (oldcode == -1) then                ! Clear 直後はリテラルのみ
      if (code > 255) return
      o = o + 1
      ubuf(o) = u2b(code)
      oldcode = code
      cycle
    end if

    ! 現コードの文字列をスタックに展開(code==nextcode は KwKwK ケース)
    sp = 0
    k = code
    if (code >= nextcode) then
      if (code > nextcode) return          ! 破損
      sp = sp + 1
      stack(sp) = firstb(oldcode)
      k = oldcode
    end if
    do while (k > 255)
      if (sp >= tabsize) return
      sp = sp + 1
      stack(sp) = suffix(k)
      k = prefix(k)
    end do
    fb = u2b(k)                            ! 文字列の先頭バイト

    ! 出力(スタックは逆順に積んである)
    if (o + sp + 1 > nu) return
    o = o + 1
    ubuf(o) = fb
    do while (sp > 0)
      o = o + 1
      ubuf(o) = stack(sp)
      sp = sp - 1
    end do

    ! テーブルに「旧文字列 + 現先頭バイト」を登録
    if (nextcode < tabsize) then
      prefix(nextcode) = oldcode
      suffix(nextcode) = fb
      firstb(nextcode) = firstb(oldcode)
      nextcode = nextcode + 1
      if (nextcode == 2**nbits - 1 .and. nbits < 12) nbits = nbits + 1
    end if
    oldcode = code
  end do
  stat = 0

contains

  ! MSB-first のビット読み出し(n <= 12)。尽きたら負値
  integer function getbits(n)
    integer, intent(in) :: n
    integer(int64) :: idx
    integer :: sh, w, b1, b2, b3
    if (bitpos + n > nc * 8) then
      getbits = -1
      return
    end if
    idx = bitpos / 8                       ! 0 始まりのバイト位置
    sh = int(mod(bitpos, 8_int64))
    b1 = u8(cbuf(idx+1))
    b2 = 0
    b3 = 0
    if (idx + 2 <= nc) b2 = u8(cbuf(idx+2))
    if (idx + 3 <= nc) b3 = u8(cbuf(idx+3))
    w = ior(ior(ishft(b1, 16), ishft(b2, 8)), b3)      ! 24 ビット窓
    getbits = ibits(w, 24 - sh - n, n)
    bitpos = bitpos + n
  end function

end subroutine


!----------------------------------------------------------------------
! predictor=2(水平差分)の復元
!   行ごとに、サンプル値(そのビット幅で 2^bits を法とする)を累積する。
!   buf のバイト並びは be(ビッグ/リトル)に従い、復元後も同じ並びで戻す
!----------------------------------------------------------------------
subroutine gtc_undo_predictor2(buf, w, rows, bpsamp, be)
  integer(int8), intent(inout) :: buf(:)
  integer, intent(in) :: w                 ! 行内サンプル数(ブロック幅)
  integer, intent(in) :: rows
  integer, intent(in) :: bpsamp            ! 1 サンプルのバイト数(1,2,4)
  logical, intent(in) :: be
  integer(int64) :: base, acc, v, mask
  integer :: r, c, k

  mask = ishft(1_int64, 8*bpsamp) - 1
  do r = 1, rows
    base = int(r-1, int64) * w * bpsamp
    acc = 0
    do c = 1, w
      v = 0
      if (be) then
        do k = 1, bpsamp
          v = ior(ishft(v, 8), int(u8(buf(base+(c-1)*bpsamp+k)), int64))
        end do
      else
        do k = bpsamp, 1, -1
          v = ior(ishft(v, 8), int(u8(buf(base+(c-1)*bpsamp+k)), int64))
        end do
      end if
      if (c == 1) then
        acc = v
      else
        acc = iand(acc + v, mask)
      end if
      v = acc
      if (be) then
        do k = bpsamp, 1, -1
          buf(base+(c-1)*bpsamp+k) = u2b(int(iand(v, 255_int64)))
          v = ishft(v, -8)
        end do
      else
        do k = 1, bpsamp
          buf(base+(c-1)*bpsamp+k) = u2b(int(iand(v, 255_int64)))
          v = ishft(v, -8)
        end do
      end if
    end do
  end do
end subroutine


!----------------------------------------------------------------------
! predictor=3(浮動小数点)の復元
!   行ごとに (1) バイト単位の水平差分を累積、(2) バイト面
!   [MSB面][…][LSB面] をサンプル順に並べ替える(libtiff の fpAcc と同じ)。
!   復元後の buf はファイルのバイト順によらず「ビッグエンディアン並びの
!   サンプル列」になるので、呼び出し側は be=.true. として解釈すること
!----------------------------------------------------------------------
subroutine gtc_undo_predictor3(buf, w, rows, bpsamp)
  integer(int8), intent(inout) :: buf(:)
  integer, intent(in) :: w, rows, bpsamp
  integer(int8) :: tmp(w*bpsamp)
  integer(int64) :: base
  integer :: r, i, p, rowbytes

  rowbytes = w * bpsamp
  do r = 1, rows
    base = int(r-1, int64) * rowbytes
    do i = 2, rowbytes
      buf(base+i) = u2b(iand(u8(buf(base+i)) + u8(buf(base+i-1)), 255))
    end do
    tmp(1:rowbytes) = buf(base+1:base+rowbytes)
    do i = 0, w - 1
      do p = 0, bpsamp - 1                 ! p=0 が MSB 面
        buf(base + int(i,int64)*bpsamp + p + 1) = tmp(p*w + i + 1)
      end do
    end do
  end do
end subroutine

end module
