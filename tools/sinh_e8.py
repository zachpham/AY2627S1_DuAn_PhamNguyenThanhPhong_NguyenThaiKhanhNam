# -*- coding: utf-8 -*-
"""Sinh ba bien the nguon cho thi nghiem E8 - doi thu tu ap dung chien luoc tia.

E8 tra loi cau hoi cua thay: "thu doi thu tu ap dung cac chien luoc tia".
Trong AlgoPHMN.phm(), moi cap (X, Y) di qua hai bo loc noi tiep nhau roi moi
den construct(). Vi hai bo loc la mot phep HOI (conjunction) nen tap cap bi
loai KHONG phu thuoc thu tu -> so ung vien phai y het nhau giua cac bien the.
Do la phep kiem tinh dung. Thoi gian thi khac nhau, vi bo loc nao loai duoc
nhieu hon ma dat truoc thi bo loc sau duoc bo qua nhieu hon.

Ba bien the:
  e8_a  thu tu goc cua ban cai dat: EUCP -> ESCP
  e8_b  dao lai:                    ESCP -> EUCP
  e8_c  giu thu tu goc nhung NHAC hai tra cuu mapEUCS.get(X.item) va
        mapESCS.get(X.item) ra NGOAI vong lap j. Hai tra cuu nay khong
        phu thuoc j nhung ban goc thuc hien lai chung o moi vong lap.

Ca ba bien the dung chung hai sua doi nua, de so sanh cong bang:
  - bo dong System.out.println(xx) trong vong lap nong (gay nhieu thoi gian)
  - them bo dem de biet tung chien luoc loai duoc bao nhieu cap

Chay:  python -I tools/sinh_e8.py
"""

import io
import os
import shutil

GOC = 'src/patched/ca/pfv/spmf/algorithms/frequentpatterns/phmn_plus'
PKG = 'ca/pfv/spmf/algorithms/frequentpatterns/phmn_plus'


# ---------------------------------------------------------------- cac mieng va

# step: doan nong trong phm(), nguyen van ban goc. Moi bien the thay doan nay.
KHOI_GOC = """					for(int j=i+1; j < ULs.size(); j++){
						UtilityListPHMN Y = ULs.get(j);

						// ======================== NEW OPTIMIZATION USED IN FHM
						if(ENABLE_EUCP){
							Map<Integer, Long> mapTWUF = mapEUCS.get(X.item);
							if(mapTWUF != null) {
								Long twuF = mapTWUF.get(Y.item);
								if(twuF == null || twuF < minUtility) {
									continue;
								}
							}
						}
						// =========================== END OF NEW OPTIMIZATION
						// ======================== NEW OPTIMIZATION USED IN PHM
						if(ENABLE_ESCP){
							Map<Integer, Long> mapSUPF = mapESCS.get(X.item);
							if(mapSUPF != null) {
								Long supportF = mapSUPF.get(Y.item);
								if(supportF != null && supportF < supportPruningThreshold) {
									continue;
								}
							}
						}
						// =========================== END OF NEW OPTIMIZATION
"""

LOC_EUCP = """						if(ENABLE_EUCP){
							Map<Integer, Long> mapTWUF = mapEUCS.get(X.item);
							if(mapTWUF != null) {
								Long twuF = mapTWUF.get(Y.item);
								if(twuF == null || twuF < minUtility) {
									rejEUCP++;
									continue;
								}
							}
						}
"""

LOC_ESCP = """						if(ENABLE_ESCP){
							Map<Integer, Long> mapSUPF = mapESCS.get(X.item);
							if(mapSUPF != null) {
								Long supportF = mapSUPF.get(Y.item);
								if(supportF != null && supportF < supportPruningThreshold) {
									rejESCP++;
									continue;
								}
							}
						}
"""

MO_VONG = """					for(int j=i+1; j < ULs.size(); j++){
						UtilityListPHMN Y = ULs.get(j);
						pairsConsidered++;
"""

# step: bien the C nhac hai tra cuu ra ngoai, nen can khai bao truoc vong lap
HOIST = """					// E8-C: hai tra cuu duoi day khong phu thuoc j, nhac ra ngoai vong lap
					Map<Integer, Long> mapTWUF_X = ENABLE_EUCP ? mapEUCS.get(X.item) : null;
					Map<Integer, Long> mapSUPF_X = ENABLE_ESCP ? mapESCS.get(X.item) : null;
"""

LOC_EUCP_C = """						if(mapTWUF_X != null){
							Long twuF = mapTWUF_X.get(Y.item);
							if(twuF == null || twuF < minUtility) {
								rejEUCP++;
								continue;
							}
						}
"""

LOC_ESCP_C = """						if(mapSUPF_X != null){
							Long supportF = mapSUPF_X.get(Y.item);
							if(supportF != null && supportF < supportPruningThreshold) {
								rejESCP++;
								continue;
							}
						}
"""

KHOI_MOI = {
    'e8_a': MO_VONG + '\n\t\t\t\t\t\t// E8-A: thu tu goc - EUCP truoc, ESCP sau\n'
            + LOC_EUCP + LOC_ESCP,
    'e8_b': MO_VONG + '\n\t\t\t\t\t\t// E8-B: dao thu tu - ESCP truoc, EUCP sau\n'
            + LOC_ESCP + LOC_EUCP,
    'e8_c': HOIST + MO_VONG
            + '\n\t\t\t\t\t\t// E8-C: thu tu goc, tra cuu da nhac ra ngoai\n'
            + LOC_EUCP_C + LOC_ESCP_C,
}


# ------------------------------------------------------- cac sua doi dung chung

KHAI_BAO_GOC = '\tpublic int candidateCount =0;'

KHAI_BAO_MOI = """	public int candidateCount =0;

	// === E8: bo dem rieng cho tung chien luoc tia ===
	// Bat bien phai dung: pairsConsidered = rejEUCP + rejESCP + candidateCount
	public long pairsConsidered = 0;   // so cap (X,Y) buoc vao vong lap trong
	public long rejEUCP = 0;           // bi EUCP loai
	public long rejESCP = 0;           // bi ESCP loai
	public long constructNull = 0;     // qua ca hai bo loc nhung construct tra null
	public long rejLAutil = 0;         // trong do: LA-prune cat theo huu ich
	public long rejLAsup = 0;          // trong do: LA-prune cat theo support"""

DEM_GOC = """						candidateCount++;
						if (candidateCount%10000==0){
							System.out.println(xx);
							xx++;
						}
"""

DEM_MOI = """						candidateCount++;
"""

NULL_GOC = """						if (temp==null){
						if (improve){"""

NULL_MOI = """						if (temp==null){
							constructNull++;
						if (improve){"""

LA_UTIL_GOC = """					totalUtility -= (ex.putils+ex.rutils);        // PATCHED
					if(totalUtility < minUtility) {
						prune = true;
						return null;
					}"""

LA_UTIL_MOI = """					totalUtility -= (ex.putils+ex.rutils);        // PATCHED
					if(totalUtility < minUtility) {
						prune = true;
						rejLAutil++;
						return null;
					}"""

LA_SUP_GOC = """					if(totalSupport < supportPruningThreshold) {
						prune = true;
						return null;
					}"""

LA_SUP_MOI = """					if(totalSupport < supportPruningThreshold) {
						prune = true;
						rejLAsup++;
						return null;
					}"""

IN_GOC = ('\t\tSystem.out.println(" Candidate count : "'
          '             + candidateCount);')

IN_MOI = """		System.out.println(" Candidate count : "             + candidateCount);
		// === E8: bao cao cong viec cua tung chien luoc tia ===
		System.out.println(" Pairs considered : "            + pairsConsidered);
		System.out.println(" Rejected by EUCP : "            + rejEUCP);
		System.out.println(" Rejected by ESCP : "            + rejESCP);
		System.out.println(" Construct returned null : "     + constructNull);
		System.out.println("   of which LA-prune utility : " + rejLAutil);
		System.out.println("   of which LA-prune support : " + rejLAsup);
		long tong = rejEUCP + rejESCP + candidateCount;
		System.out.println(" Invariant pairs == rejEUCP+rejESCP+candidates : "
				+ (tong == pairsConsidered ? "OK" : "SAI (" + tong + ")"));"""


def thay(ten_file, noi_dung, cu, moi, nhan):
    """Thay mot lan duy nhat; bao loi neu khong tim thay hoac tim thay nhieu.

    @param ten_file ten bien the, chi dung de ghi vao thong bao loi
    @param noi_dung van ban nguon hien tai
    @param cu doan can tim, phai xuat hien dung mot lan
    @param moi doan thay vao
    @param nhan ten cua phep sua, de doc duoc thong bao loi
    @return van ban nguon sau khi thay
    """
    n = noi_dung.count(cu)
    if n != 1:
        raise AssertionError('%s: moc "%s" xuat hien %d lan, mong doi 1'
                             % (ten_file, nhan, n))
    return noi_dung.replace(cu, moi)


def sinh(bien_the):
    """Sinh mot cay nguon cho mot bien the.

    @param bien_the mot trong 'e8_a', 'e8_b', 'e8_c'
    @return duong dan thu muc nguon da sinh
    """
    goc_bt = os.path.join('src', bien_the)
    dich = os.path.join(goc_bt, PKG)

    # step: xoa cay cu de khong con sot file cua lan sinh truoc
    if os.path.isdir(goc_bt):
        shutil.rmtree(goc_bt)
    os.makedirs(dich)

    # step: hai lop du lieu khong sua gi, copy nguyen ven
    for f in ('ElementPHMN.java', 'UtilityListPHMN.java'):
        shutil.copy(os.path.join(GOC, f), os.path.join(dich, f))

    s = io.open(os.path.join(GOC, 'AlgoPHMN.java'), encoding='utf-8').read()

    # step: nguon goc co nhung dong trong mang day tab o cuoi, ma trinh soan
    # thao nao cung cat di, nen cac moc ben tren khong khop duoc. Cat khoang
    # trang cuoi dong trong CA nguon truoc khi so khop. Java khong quan tam.
    s = '\n'.join(dong.rstrip() for dong in s.split('\n'))

    # step: sau sua doi dung chung cho ca ba bien the
    s = thay(bien_the, s, KHAI_BAO_GOC, KHAI_BAO_MOI, 'khai bao bo dem')
    s = thay(bien_the, s, DEM_GOC, DEM_MOI, 'bo println trong vong lap nong')
    s = thay(bien_the, s, NULL_GOC, NULL_MOI, 'dem construct tra null')
    s = thay(bien_the, s, LA_UTIL_GOC, LA_UTIL_MOI, 'dem LA-prune huu ich')
    s = thay(bien_the, s, LA_SUP_GOC, LA_SUP_MOI, 'dem LA-prune support')
    s = thay(bien_the, s, IN_GOC, IN_MOI, 'in bo dem')

    # step: sua rieng cua tung bien the - thu tu hai bo loc
    s = thay(bien_the, s, KHOI_GOC, KHOI_MOI[bien_the], 'khoi hai bo loc')

    # step: nhan phien ban, de khong bao gio lan log cua hai bien the voi nhau
    s = thay(bien_the, s, 'v2.38-PATCHED',
             'v2.38-' + bien_the.upper().replace('_', '-'), 'nhan phien ban')

    io.open(os.path.join(dich, 'AlgoPHMN.java'), 'w',
            encoding='utf-8', newline='\n').write(s)
    return dich


if __name__ == '__main__':
    for bt in ('e8_a', 'e8_b', 'e8_c'):
        print('da sinh %s' % sinh(bt))
