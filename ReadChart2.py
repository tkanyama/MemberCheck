# from pdfminer.layout import LAParams, LTLine, LTTextBoxHorizontal
from pdfminer.layout import LAParams, LTTextContainer, LTContainer, LTTextBoxHorizontal, LTTextLine, LTChar,LTLine,LTRect
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.pdfpage import PDFPage
from io import StringIO
import numpy as np
import sys,csv,os
# pip install reportlab
from reportlab.pdfgen import canvas
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm

cc = 25.4/72.0

def Read_Elements_from_pdf(pdf_path):
    laparams = LAParams()
    
    # PDFMinerのツールの準備
    resourceManager = PDFResourceManager()
    outfp = StringIO()
    # PDFから単語を取得するためのデバイス
    # device = PDFPageAggregator(resourceManager, laparams=LAParams())
    # PDFから１文字ずつを取得するためのデバイス
    device2 = PDFPageAggregator(resourceManager)

    # interpreter = PDFPageInterpreter(resourceManager, device)
    interpreter2 = PDFPageInterpreter(resourceManager, device2)
    
    fp = open(pdf_path, 'rb')
    ElementData= {}
    PageKind = ["構造計算書","断面リスト"]
    # EKnd = ["壁"]
    # EKnd = ["小梁","壁"]
    # EKnd = ["【大梁】","【基礎大梁】","【柱】","【片持梁】","【小梁】","【基礎小梁】","【壁】"]
    EKnd = ["【大梁】","【基礎大梁】","【柱】"]
    # EKnd = ["大梁","柱"]
    for EK in EKnd:
        ElementData[EK] = {}
    #next
    # Elements= {}
    pageN = 0
    CR = ChartReader()
    stopFlag = False
    for page in PDFPage.get_pages(fp):
        pageN += 1
        print ("page={}:".format(pageN),end="")
        # interpreter.process_page(page)
        # interpreter2.process_page(page)
        
        dflag, element = CR.ChartDevider(interpreter2 ,device2 ,page,PageKind,EKnd)
        if dflag :
            for EK in EKnd:
                if len(element[EK])>0:
                    ElementData[EK]= ElementData[EK] | element[EK]
                #end if
            #next
            if not stopFlag :
                stopFlag = True
            #enf if
        else:
            if stopFlag:
                break
            #end if
        #en if
        # else:
        #     print("")
        # #end if
    #next
    # ElementData[EK] = Elements
    fp.close()

    return ElementData
#end def

class ChartReader:
    def __init__(self):

        self.MemberPosition = {}    # 部材符号と諸元データの辞書
        self.memberData = {}
        self.memberName = []
        self.makePattern()
        # 源真ゴシック等幅フォント
        # GEN_SHIN_GOTHIC_MEDIUM_TTF = "/Library/Fonts/GenShinGothic-Monospace-Medium.ttf"
        GEN_SHIN_GOTHIC_MEDIUM_TTF = "./Fonts/GenShinGothic-Monospace-Medium.ttf"
        self.fontname1 = 'GenShinGothic'
        # IPAexゴシックフォント
        # IPAEXG_TTF = "/Library/Fonts/ipaexg.ttf"
        IPAEXG_TTF = "./Fonts/ipaexg.ttf"
        self.fontname2 = 'ipaexg'
        
        # フォント登録
        pdfmetrics.registerFont(TTFont(self.fontname1, GEN_SHIN_GOTHIC_MEDIUM_TTF))
        pdfmetrics.registerFont(TTFont(self.fontname2, IPAEXG_TTF))
    #end def

    def ChartDevider(self,interpreter2 ,device2 ,page,PageKind,EKind2):
        """
        ・すべての水平線および垂直線のデータを辞書にしてリストを作成
        ・その際、それらの太線のみのリストも作成
        ・すべての横書きテキストのデータを辞書にしてリストを作成
        ・以下の方法で1ページに含まれる表の数を調べる。
            ・最上部から2本ずつ水平線を選び、すべての垂直線のy0とy1が2本の水平線の区間にあるかどうかを調べる。
            ・2本の区間に垂直線のy0とy1がない場合はその区間が表の境目であると判断する。
            ・各表の最上部と最下部のy座標のリスト（cymax、cymin）を作成
        ・すべての水平線、垂直線および横書きテキストを各表毎にグループ分けする。
        ・各表毎に以下の操作を行う。
            ・表の左端より右側にある最初の太線を表の項目欄とデータ欄の境界線と判断する。
            ・境界線より左側にy0がある線のみを表の罫線を判断し、残りの水平線は破棄
            ・境界線より右側にある垂直線でy0およびy1が表の最上部と最下部の内側にあるものは破棄
        """

        EKElement = {}
        for EK in EKind2:
            EKElement[EK] = {}
        #next

        # interpreter.process_page(page)
        # layout = device.get_result()
        interpreter2.process_page(page)
        layout2 = device2.get_result()

        LineText , CharData, LineData =  self.MakeChar(page, interpreter2, device2)
        if len(CharData)<10:
            print("")
            return False,{}
        
        DataFlag1 = []
        for Pkind in PageKind:
            DataFlag = False
            for Line in LineText:
                if Pkind in Line :
                    DataFlag = True
                    break
                #end if
            #next 
            DataFlag1.append(DataFlag)
        #next
        DataFlag2 = True
        for f in DataFlag1:
            DataFlag2 = DataFlag2 and f
        #next
        if not DataFlag2 or len(LineData)==0:
            print("")
            return False,{}

        HLineData = []      # すべての水平線の辞書のリスト
        HLineX0 = []        # すべての水平線のx0のリスト
        HLineY1 = []        # すべての水平線のy1のリスト
        HBoldLineData = []  # 太線の水平線の辞書のリスト
        VLineData = []      # すべての垂直線の辞書のリスト
        VLineY1 = []        # すべての垂直線のy1のリスト
        # VLineHeight = []
        VBoldLineData = []  # 太線の垂直線の辞書のリスト

        thinMin = 1000
        thinMax = 0
        cc = 0
        thin = []
        for Line in LineData:
            t1 = Line["linewidth"]
            if not t1 in thin:
                thin.append(t1)
            #en if
            if t1 < thinMin:
                thinMin = Line["linewidth"] 
            #end if
            if t1 > thinMax:
                thinMax = Line["linewidth"] 
            #end if
            # cc += 1
            # if cc > 100:
            #     break
            #end if
        #next
        a=0
        for Line in LineData:
            if Line["angle"] == "V":    # 水平線の辞書のリスト
                VLineData.append(Line)
                VLineY1.append(Line["y1"])
                # VLineHeight.append(Line["height"])
                if Line["linewidth"] == thinMax:     # 太線の水平線の辞書のリスト
                    VBoldLineData.append(Line)
                #end if
            else:                       # 垂直線の辞書のリスト
                HLineData.append(Line)
                HLineX0.append(Line["x0"])
                HLineY1.append(Line["y1"])
                if Line["linewidth"] == thinMax:     # 太線の垂直線の辞書のリスト
                    HBoldLineData.append(Line)
                #end if
            #end if
        #next

        # WordData = []           # 横書きテキストの辞書のリスト
        # for lt in layout:
        #     if isinstance(lt, LTTextBoxHorizontal):  # レイアウトデータうち、LTLineのみを取得
        #         a = lt.get_text()
        #         a = a.replace("\n","")
        #         WordDic = {}
        #         WordDic["index"] = lt.index
        #         WordDic["text"] = a
        #         WordDic["x0"] = lt.x0
        #         WordDic["x1"] = lt.x1
        #         WordDic["y0"] = lt.y0
        #         WordDic["y1"] = lt.y1
        #         WordDic["height"] = lt.height
        #         WordDic["width"] = lt.width
        #         WordData.append(WordDic)
        #     #end if
            
        # #next
        # a = 0
        
        # 水平線をy0が高い順に並び替え
        HLineArray = np.array(HLineY1)      # リストをNumpyの配列に変換
        index1 = np.argsort(-HLineArray)    # 縦の線をHeightの値で降順にソートするインデックスを取得
        HLineData2 = []                     # 高順位並び替えたLineデータ
        for i in range(len(index1)):
            HLineData2.append(HLineData[index1[i]])
        #next
        HLineData = HLineData2

        # 垂直線をy1が高い順に並び替え
        VLineArray = np.array(VLineY1)      # リストをNumpyの配列に変換
        index1 = np.argsort(-VLineArray)    # 縦の線をHeightの値で降順にソートするインデックスを取得
        VLineData2 = []                     # 高順位並び替えたLineデータ
        for i in range(len(index1)):
            VLineData2.append(VLineData[index1[i]])
        #next
        VLineData = VLineData2


        # 2本の水平線を跨ぐ垂直線の数をカウントし、カウントが0の区間が表の区切りと判断する。
        cymax = []
        cymin = []
        # cymax及びcyminのデータ数が表の数
        Hy1 = HLineData[0]["y1"]
        cymax.append(Hy1)
        
        for i in range(1,len(HLineData)):
            
            ccount = 0
            if HLineData[i]["y1"] < Hy1:
                Hy0 = HLineData[i]["y0"]
                
                # print(Hy0,Hy1)
                # 2本の水平線を跨ぐ垂直線の数をカウント
                for j in range(len(VLineData)):
                    Vy0 = VLineData[j]["y0"]
                    Vy1 = VLineData[j]["y1"]
                    # print(Hy0,Hy1,Vy0,Vy1)
                    if Vy1 >= Hy1 and Vy0 <= Hy0 :
                        ccount += 1
                    #end if
                #next

                if ccount == 0 :
                    cymin.append(Hy1)
                    cymax.append(Hy0)

                #end if

                # rows.append(row)
                
                Hy1 = HLineData[i]["y1"]
            #end if
        #next
        # 1番下側の水平線の高さを最後の表の下限とする。
        cymin.append(HLineData[len(HLineData)-1]["y0"])

        if len(cymax) != len(cymin):# 数が異なる場合は終了する。
            print("終了します。")
            sys.exit()
        #end if


        # 表毎に水平線と垂直線をグループ分けする。
        chartN = len(cymax)
        ChartVLine = []
        ChartHLine = []
        ChartVBoldLine = []
        ChartHBoldLine = []
        ChartWords = []
        ChartChar = []
        for i in range(chartN):
            ymin = cymin[i]
            ymax = cymax[i]
            HLine = []
            for H in HLineData:
                if H["y0"] >= ymin and H["y0"] <= ymax:
                    HLine.append(H)
                #end if
            #next
            ChartHLine.append(HLine)
            HBLine = []
            for H in HBoldLineData:
                if H["y0"] >= ymin and H["y0"] <= ymax:
                    HBLine.append(H)
                #end if
            #next
            ChartHBoldLine.append(HBLine)
            VLine = []
            for V in VLineData:
                if V["y0"] >= ymin and V["y1"] <= ymax:
                    VLine.append(V)
                #end if
            #next
            ChartVLine.append(VLine)
            VBLine = []
            for V in VBoldLineData:
                if V["y0"] >= ymin and V["y1"] <= ymax:
                    VBLine.append(V)
                #end if
            #next
            ChartVBoldLine.append(VBLine)
            # Words = []
            # for W in WordData:
            #     if W["y0"] >= ymin and W["y1"] <= ymax:
            #         Words.append(W)
            #     #end if
            # #next
            # ChartWords.append(Words)

            Char = []
            for C in CharData:
                if C[0][3] >= ymin and C[0][4]<= ymax:
                    Char.append(C)
                #end if
            #next
            ChartChar.append(Char)
        #next
        # ChartVLine = []
        # ChartHLine = []
        # ChartVBoldLine = []
        # ChartHBoldLine = []
        # ChartWords = []

        # ElementData = {}

        for i in range(chartN):
            ElementData = {}
            HLine = ChartHLine[i]
            VLine = ChartVLine[i]
            HBLine = ChartHBoldLine[i]
            VBLine = ChartVBoldLine[i]
            Char = ChartChar[i]
            ChartXmin = HLine[0]["x0"]
            for L in HLine:
                if L["x0"] < ChartXmin:
                    ChartXmin = L["x0"]
                #end if
            #next
            ChartXmax = HLine[0]["x1"]
            for L in HLine:
                if L["x1"] > ChartXmax:
                    ChartXmax = L["x1"]
                #end if
            #next
            ChartYmin = HLine[0]["y0"]
            for L in VLine:
                if L["y0"] < ChartYmin:
                    ChartYmin = L["y0"]
                #end if
            #next
            ChartYmax = HLine[0]["y1"]
            for L in VLine:
                if L["y1"] > ChartYmax:
                    ChartYmax = L["y1"]
                #end if
            #next

            # ChartYmaxのすぐ上のテキストを検索
            
            for j  in range(len(CharData)):
                if CharData[j][0][3] <= ChartYmax:
                    break
                #end if
            #next
            Char2 = CharData[j-1]
            text1 = ""
            for Ct in Char2:
                text1 += Ct[0]
            #next 
            # print(text1)
            EKFlag = False
            EKind = ""
            for EK in EKind2:
                if EK in text1:
                    EKFlag = True
                    EKind = EK
                #end if
            #next
            if EKFlag:
                print(text1)
                # print(ChartXmin*cc,ChartXmax*cc,ChartYmin*cc,ChartYmax*cc)

                # 表の行のヘッダーとデータの境界線を探す
                Xpoint = ChartXmin
                for L in VBLine:
                    if L["x0"]>ChartXmin:
                        Xpoint = L["x0"]
                        break
                    #end if
                #next
                # print(Xpoint*cc)
                
                # x0が境界線より左側にあるまたは接している水平線のみ抽出
                HLine2 = []
                HLine2Y1 = []
                for L in HLine:
                    if L["x0"] <= Xpoint:
                        HLine2.append(L)
                        HLine2Y1.append(L["y1"])
                    #end if
                #next

                # 水平線をy1が高い順に並び替え
                HLineArray = np.array(HLine2Y1)      # リストをNumpyの配列に変換
                index1 = np.argsort(-HLineArray)    # 縦の線をHeightの値で降順にソートするインデックスを取得
                HLine22 = []                     # 高順位並び替えたLineデータ
                for j in range(len(index1)):
                    HLine22.append(HLine2[index1[j]])
                #next
                HLine2 = HLine22

                # 抽出した水平線からy1が異なるものを抽出（表の水平罫線と判断）
                HLinePoint = []
                y01 = HLine2[0]["y1"]
                Hxmax = HLine2[0]["x1"]
                Hxmin = HLine2[0]["x0"]
                HLinePoint.append(y01)
                HLineTerminal = []
                for L in HLine2:
                    if L["y1"]<y01:
                        HLineTerminal.append([Hxmin ,Hxmax])
                        # print(y01*cc ,Hxmin*cc ,Hxmax*cc)
                        y01 = L["y1"]
                        HLinePoint.append(y01)
                        Hxmin = L["x0"]
                        # Hxmax = L["x1"]
                        Hxmax = ChartXmax
                    else:
                        if L["x0"] < Hxmin:
                            Hxmin = L["x0"]
                        #end if
                        # if L["x1"] > Hxmax:
                        #     Hxmax = L["x1"]
                        # #end if
                    #end if
                #next
                if HLine2[len(HLine2)-1]["y1"]<=y01:
                    HLineTerminal.append([HLine2[len(HLine2)-1]["x0"],HLine2[len(HLine2)-1]["x1"]])
                #end if

                MadeHLine = []
                for y in HLinePoint:
                    xmin1 = +10000.0
                    xmax1 = -10000.0
                    for H in HLine:
                        if y == H["y0"]:
                            if xmin1>H["x0"]:
                                xmin1=H["x0"]
                            #end if
                            if xmax1<H["x1"]:
                                xmax1=H["x1"]
                            #end if
                        #end if
                    #next
                    MadeHLine.append({"x0":xmin1,"x1":xmax1,"y0":y,"y1":y})
                #next
                a=0


                # x0が境界線より左側にあるまたは接している太線水平線のみ抽出
                HBLine2 = []
                HBLine2Y1 = []
                for L in HBLine:
                    if L["x0"] <= Xpoint:
                        HBLine2.append(L)
                        HBLine2Y1.append(L["y1"])
                    #end if
                #next

                # 水平線をy1が高い順に並び替え
                HLineArray = np.array(HBLine2Y1)      # リストをNumpyの配列に変換
                index1 = np.argsort(-HLineArray)    # 縦の線をHeightの値で降順にソートするインデックスを取得
                HBLine22 = []                     # 高順位並び替えたLineデータ
                for j in range(len(index1)):
                    HBLine22.append(HBLine2[index1[j]])
                #next
                HBLine2 = HBLine22

                # 抽出した太線水平線からy1が異なるものを抽出（表の太線水平罫線と判断）
                HBLinePoint = []
                y01 = HBLine2[0]["y1"]
                HBLinePoint.append(y01)
                for L in HBLine2:
                    if L["y1"]<y01:
                        y01 = L["y1"]
                        HBLinePoint.append(y01)
                    #end if
                #next
                Ypoint = HBLinePoint[1]     # コラムのヘッダーとデータの境界のY座標
                # print(Ypoint*cc)

                VLine2 = []
                VLine2X0 = []
                for j in range(len(HLine2)-1):
                    y1 = HLine2[j]["y1"]
                    y0 = HLine2[j+1]["y1"]
                    for L in VLine:
                        if L["y0"]==y0 or L["y1"]== y1 :
                            VLine2.append(L)
                            VLine2X0.append(L["x0"])
                        #end if
                    #next
                #next

                # 垂直線をx0が小さい順に並び替え
                HLineArray = np.array(VLine2X0)      # リストをNumpyの配列に変換
                index1 = np.argsort(HLineArray)    # 縦の線をHeightの値で降順にソートするインデックスを取得
                VLine22 = []                     # 高順位並び替えたLineデータ
                for j in range(len(index1)):
                    VLine22.append(VLine2[index1[j]])
                #next
                VLine2 = VLine22

                # 抽出した垂直線からx0が異なるものを抽出（表の垂直罫線と判断）
                VLinePoint = []
                VLinePoint.append(ChartXmin)
                x01 = ChartXmin
                for L in VLine2:
                    if L["x0"]>x01:
                        x01 = L["x0"]
                        VLinePoint.append(x01)
                    #end if
                #next
                VLinePoint.append(ChartXmax)

                ColumnsN = len(VLinePoint) - 1
                RowsN = len(HLinePoint) - 1
                Celly0y1 = []
                DataStartRn = 0     # データがスタートする行番号
                for j in range(RowsN):
                    Celly0y1.append([HLinePoint[j+1] ,HLinePoint[j]])
                    if HLinePoint[j] == Ypoint:
                        DataStartRn = j
                    #end if
                #next
                Cellx0x1 = []
                DataStartCn = 0    # データがスタートする列番号
                for j in range(ColumnsN):
                    Cellx0x1.append([VLinePoint[j] ,VLinePoint[j+1]])
                    if VLinePoint[j] == Xpoint:
                        DataStartCn = j
                    #end if
                #next

                MadeVLine = []
                for x in VLinePoint:
                    L1 = []
                    L2 = []
                    for L in VLine:
                        if L["x0"]==x:
                            L1.append(L)
                            L2.append(L["y1"])
                        #end if
                    #next
                    
                    if len(L1)>0:
                        VArray = np.array(L2)      # リストをNumpyの配列に変換
                        index1 = np.argsort(-VArray)    # 縦の線をHeightの値で降順にソートするインデックスを取得
                        L22 = []                     # 高順位並び替えたLineデータ
                        for j in range(len(index1)):
                            L22.append(L1[index1[j]])
                        #next
                        L1 = L22
                        ymax1 = L1[0]["y1"]
                        ymin1 = L1[0]["y0"]
                        for L in L1:
                            if L["y1"] < ymin1:
                                MadeVLine.append({"x0":x,"x1":x,"y0":ymin1,"y1":ymax1})
                                ymax1 = L["y1"]
                                ymin1 = L["y0"]
                            else:
                                ymin1 = L["y0"]
                            #end if
                        #next
                        MadeVLine.append({"x0":x,"x1":x,"y0":ymin1,"y1":ymax1})
                    #end if
                #next
                a=0

                    #end if



                # words = ChartWords[i]
                # wordCell = []
                # for w in words:
                #     wx0 = w["x0"]
                #     wx1 = w["x1"]
                #     wy0 = w["y0"]
                #     wy1 = w["y1"]
                #     t1 = w["text"]
                #     index1 = w["index"]
                #     # cellX = []
                #     # cellY = []
                #     for j in range(ColumnsN):
                #         [x0,x1] = Cellx0x1[j]
                #         if wx0>=x0 and wx0<=x1 :
                #             cellX=j
                #         #end if
                #     #next
                #     for j in range(RowsN):
                #         [y0,y1] = Celly0y1[j]
                #         if wy0>=y0 and wx0<=y1 :
                #             cellY=j
                #         #end if
                #     #next
                #     wordCell.append([t1,index1,cellX,cellY])
                # #next
                
                ChartData = []
                ChartDataWithOrigin = []
                for j in range(RowsN):
                    CCell = []
                    CCell2 = []
                    for k in range(ColumnsN):
                        CCell.append("")
                        CCell2.append([])
                    #next
                    ChartData.append(CCell)
                    ChartDataWithOrigin.append(CCell2)
                #next

                for CLine in Char:
                    for C in CLine:
                        t = C[0]
                        Cx0 = C[1]
                        Cx1 = C[2]
                        Cy0 = C[3]
                        Cy1 = C[4]
                        cellX = -1
                        cellY = -1
                        for j in range(ColumnsN):
                            [x0,x1] = Cellx0x1[j]
                            if Cx0>=x0 and Cx0<=x1 :
                                cellX=j
                            #end if
                        #next
                        for j in range(RowsN):
                            [y0,y1] = Celly0y1[j]
                            if Cy1>=y0 and Cy1<=y1 :
                                cellY=j
                            #end if
                        #next
                        if cellX>-1 and cellY>-1:
                            ChartData[cellY][cellX] += t
                            # C2 = ChartDataWithOrigin[cellY][cellX]
                            # C2.append(C)
                            # ChartDataWithOrigin[cellY][cellX] = C2
                            ChartDataWithOrigin[cellY][cellX].append(C)
                        #end if
                    #next
                #next
                
                # セル毎に罫線の有無を調べる。
                LineExist = []
                CellFlag = []
                for j in range(RowsN):
                    List = []
                    FlagLine = []
                    for k in range(ColumnsN):
                        LineE = {}
                        LineE["Upper"] = False
                        LineE["Lower"] = False
                        LineE["Left"] = False
                        LineE["Right"] = False
                        List.append(LineE)
                        FlagLine.append([-1,-1])
                    #next
                    LineExist.append(List)
                    CellFlag.append(FlagLine)
                #next

                for j in range(RowsN):
                    y0 = 0.0
                    y1 = 0.0
                    x0 = 0.0
                    x1 = 0.0
                    
                    [y0,y1] = Celly0y1[j]
                    for k in range(ColumnsN):
                        [x0,x1] = Cellx0x1[k]
                        flag = False
                        # for L in HLine2:
                        if j==9 and k==3:
                            a=0
                        # for L in HLine:
                        for L in MadeHLine:
                            Cy0 = L["y0"]
                            Cy1 = L["y1"]
                            Cx0 = L["x0"]
                            Cx1 = L["x1"]
                            if y1 == Cy1 :
                                if x0>=Cx0 and x1<=Cx1 :
                                    LineExist[j][k]["Upper"] = True
                                #end if
                            #end if
                            if y0 == Cy0 :
                                if x0>=Cx0 and x1<=Cx1 :
                                    LineExist[j][k]["Lower"] = True
                                #end if
                            #end if
                        #next
                        # for L in VLine2:
                        # for L in VLine:
                        for L in MadeVLine:
                            Cy0 = L["y0"]
                            Cy1 = L["y1"]
                            Cx0 = L["x0"]
                            Cx1 = L["x1"]
                            if x0 == Cx0 :
                                if y1<=Cy1 and y0 >= Cy0:
                                    LineExist[j][k]["Left"] = True
                                #end if
                            else:
                                if x0 == ChartXmin :
                                    LineExist[j][k]["Left"] = True
                                #end if
                            #end if
                            if x1 == Cx1 :
                                if y1<=Cy1 and y0 >= Cy0 :
                                    LineExist[j][k]["Right"] = True
                                #end if
                            else:
                                if x1 == ChartXmax :
                                    LineExist[j][k]["Right"] = True
                                #end if
                            #end if
                        #next
                    #next
                #next
                a=0

                CellInfo = []
                CellNo = []
                CellD = ""
                for j in range(RowsN):
                    for k in range(ColumnsN):
                        if CellFlag[j][k] == [-1,-1]:
                            CellFlag[j][k] = [j,k]
                            CellNo.append([j,k])
                            if ChartData[j][k] != "":
                                CellD = ChartData[j][k]
                            #end if
                            cFlag = True
                            l = 0
                            while True:
                                l += 1
                                if k + l < ColumnsN:
                                    if LineExist[j][k + l]["Left"] :
                                        cFlag = True
                                        break
                                    else:
                                        if CellFlag[j][k + l] == [-1,-1]:
                                            CellFlag[j][k + l] = [j,k]
                                            CellNo.append([j,k + l])
                                            if ChartData[j][k + l] != "":
                                                CellD += ChartData[j][k + l]
                                            #end if
                                        #end if
                                    #end if
                                else:
                                    if len(CellNo)>0 :
                                        CellInfo.append([CellNo,CellD.replace(" ","")])
                                    #end if
                                    CellNo = []
                                    CellD = ""
                                    cFlag = False
                                    break
                                #end if
                            #end while
                            # if len(CellNo)>0 :
                            #     CellInfo.append([CellNo,CellD])
                            # #end if
                            # CellNo = []
                            # CellD = ""

                            if cFlag:
                                m = 0
                                while True:
                                    m += 1
                                    if j + m < RowsN:
                                        if LineExist[j + m][k]["Upper"]:
                                            if len(CellNo)>0 :
                                                CellInfo.append([CellNo,CellD.replace(" ","")])
                                            #end if
                                            CellNo = []
                                            CellD = ""
                                            break
                                        #end if
                                        for l1 in range(l):
                                            if CellFlag[j + m ][k + l1] == [-1,-1]:
                                                CellFlag[j + m ][k + l1] = [j,k]
                                                CellNo.append([j + m ,k + l1])
                                                if ChartData[j + m][k + l1] != "":
                                                    CellD += ChartData[j + m][k + l1]
                                                #end if
                                            #end if
                                        #next
                                        # l = 0
                                    else:
                                        if len(CellNo)>0 :
                                            CellInfo.append([CellNo,CellD.replace(" ","")])
                                        #end if
                                        CellNo = []
                                        CellD = ""
                                        break
                                        
                                    #end if
                                #end while
                                if len(CellNo)>0 :
                                    CellInfo.append([CellNo,CellD.replace(" ","")])
                                #end if
                                CellNo = []
                                CellD = ""
                            #end if
                        # #end if
                        # CellNo = []
                        # CellD = ""
                    #next
                #next

                ChartData2 = []
                for j in range(RowsN):
                    CCell = []
                    for k in range(ColumnsN):
                        CCell.append("")
                    #next
                    ChartData2.append(CCell)
                #next
                # ChartData2 = ChartData.copy()
                for CellInfoD in CellInfo:
                    [CellNo2, D2 ] = CellInfoD
                    for C in CellNo2:
                        ChartData2[C[0]][C[1]]=D2
                    #next
                #next


                a=0

                if EKind == "【大梁】" or EKind == "【基礎大梁】"or EKind == "【柱】":
                    FloorN = 0
                    FloorDataStartRn = []
                    FloorDataEndRn = []
                    FloorDataPos = []
                    pos = []
                    for j in range(RowsN):
                        if ChartData2[j][1] == "符号名":
                            FloorN +=1
                            FloorDataStartRn.append(j)
                            if FloorN > 1:
                                FloorDataEndRn.append(j-1)
                            #end if
                            if len(pos)>0:
                                FloorDataPos.append(pos)
                            #end if
                            pos = []
                            pos.append(j)
                        else:
                            if j>=DataStartRn:
                                pos.append(j)
                            #end if
                        #end if
                    #next
                    FloorDataEndRn.append(RowsN-1)
                    if len(pos)>0:
                        FloorDataPos.append(pos)
                    #end if
                elif EKind == "【片持梁】" or EKind == "【小梁】" or EKind == "【基礎小梁】":
                    FloorN = 1
                    FloorDataStartRn = [2]
                    FloorDataEndRn = [3]
                    FloorDataPos = [[2,3]]
                elif EKind == "【壁】" :
                    FloorN = 1
                    FloorDataStartRn = [1]
                    FloorDataEndRn = [9]
                    FloorDataPos = [[1,2,3,4,5,6,7,8,9]]
                #end if

                a=0

                ElementN = ColumnsN - DataStartCn
                ElementCommmonName = []
                ElementSectionName = []
                ElementPos = []
                if EKind == "【大梁】" or EKind == "【基礎大梁】":
                    for j in range(ElementN):
                        ElementCommmonName.append(ChartData2[0][DataStartCn + j])
                        ElementSectionName.append(ChartData2[1][DataStartCn + j])
                        ElementPos.append(DataStartCn + j)
                    #next
                elif EKind == "【柱】":
                    for j in range(ElementN):
                        ElementCommmonName.append(ChartData2[0][DataStartCn + j])
                        ElementPos.append(DataStartCn + j)
                    #next
                elif EKind == "【片持梁】" or EKind == "【小梁】" or EKind == "【基礎小梁】":
                    for j in range(ElementN):
                        ElementCommmonName.append(ChartData2[0][DataStartCn + j])
                        ElementSectionName.append(ChartData2[1][DataStartCn + j])
                        ElementPos.append(DataStartCn + j)
                    #next
                elif EKind == "【壁】" :
                    for j in range(ElementN):
                        ElementCommmonName.append(ChartData2[0][DataStartCn + j])
                        ElementPos.append(DataStartCn + j)
                    #next
                #end if
# "片持梁","小梁"
                # ElementData = {}
                for j in range(FloorN):
                    RowPos = FloorDataPos[j]
                    m = -1
                    for ep in ElementPos:
                        m += 1
                        Element = {}
                        # ename = ChartData2[RowPos[0]][ep]
                        # Element["符号名"] = ename

                        if EKind == "【大梁】" or EKind == "【基礎大梁】":
                            ename = ChartData2[RowPos[0]][ep]
                            FloorName = ChartData2[RowPos[0]][0]
                            Element["符号名"] = ename
                            Element["共通符号名"] = ElementCommmonName[m]
                            Element["階数"] = FloorName
                            Element["断面位置"] = ElementSectionName[m]
                            ename2 = ename+":" + ElementSectionName[m]
                        elif EKind == "【柱】":
                            ename = ChartData2[RowPos[0]][ep]
                            FloorName = ChartData2[RowPos[0]][0]
                            Element["符号名"] = ename
                            Element["共通符号名"] = ElementCommmonName[m]
                            Element["階数"] = FloorName
                            ename2 = ename
                        elif EKind == "【片持梁】" or EKind == "【小梁】" or EKind == "【基礎小梁】":
                            ename = ElementCommmonName[m]
                            Element["符号名"] = ename
                            Element["断面位置"] = ElementSectionName[m]
                            ename2 = ename+":" + ElementSectionName[m]
                        elif EKind == "【壁】" :
                            ename = ElementCommmonName[m]
                            Element["符号名"] = ename
                            ename2 = ename
                        #end if
                        # ename2 = ename+":" + ElementSectionName[m]
                        # ChartData2[FloorDataStartRn[j]][ep]
                        for rp in RowPos:
                            pname=[]
                            for k in range(1,DataStartCn):
                                pname.append(ChartData2[rp][k])
                            #next
                            pname2 = pname[0]
                            pp1 = pname[0]
                            for pn in pname:
                                if pn != pp1:
                                    pname2 += ":" + pn
                                    pp1 = pn
                                #end if
                            #next
                            a=0
                            Element[pname2] = ChartData2[rp][ep]
                        #next
                        if "," in ename :
                            enamed = ename.split(",")
                            for name in enamed:
                                Element["符号名"] = name
                                if ":" in ename2 :
                                    ename2 = name + ":"+Element["断面位置"]
                                else:
                                    ename2 = name
                                #end if
                                ElementData[ename2] = Element
                            #next
                        else:
                            ElementData[ename2] = Element
                        #end if
                    #next

                EKElement[EKind] = EKElement[EKind] | ElementData
            #end if

        #next
        a=0
        # key = ElementData.keys()
        # return EKind, ElementData
        if len(EKElement)>0 :
            return True, EKElement
        else:
            return False, EKElement



    #end def


    def ReadHeader(self, page, interpreter, device):

        interpreter.process_page(page)
        # １文字ずつのレイアウトデータを取得
        layout = device.get_result()

        LineData = []
        CCount = 0
        for lt in layout:
            if isinstance(lt, LTTextBoxHorizontal):  # レイアウトデータうち、LTCharのみを取得
                char1 = lt.get_text()   # レイアウトデータに含まれる全文字を取得
                char1 = char1.replace(" ","")
                LineData.append(char1)
                CCount += 1
                if CCount > 5:
                    break
            #end if
        #next
        return LineData



#==================================================================================
    #   各ページから１文字ずつの文字と座標データを抽出し、行毎の文字配列および座標配列を戻す関数
    #==================================================================================

    def MakeChar(self, page, interpreter, device):

        interpreter.process_page(page)
        # １文字ずつのレイアウトデータを取得
        layout = device.get_result()

        CharData = []
        for lt in layout:
            if isinstance(lt, LTChar):  # レイアウトデータうち、LTCharのみを取得
                char1 = lt.get_text()   # レイアウトデータに含まれる全文字を取得
                m1 = lt.matrix
                if m1[1] == 0.0 :  # 回転していない文字のみを抽出
                    CharData.append([char1, lt.x0, lt.x1, lt.y0, lt.y1,lt.matrix])
                #end if
            #end if
        #next


        LineData = []
        RectData = []
        for lt in layout:
            if isinstance(lt, LTLine):  # レイアウトデータうち、LTLineのみを取得
                lineDic = {}
                lineDic["x0"] = lt.x0
                lineDic["x1"] = lt.x1
                lineDic["y0"] = lt.y0
                lineDic["y1"] = lt.y1
                lineDic["height"] = lt.height
                lineDic["width"] = lt.width
                lineDic["linewidth"] = lt.linewidth
                lineDic["pts"] = lt.pts
                if lt.x0 == lt.x1 :
                    lineAngle = "V"
                else:
                    lineAngle = "H"
                #end if
                lineDic["angle"] = lineAngle
                LineData.append(lineDic)
            #end if
            if isinstance(lt, LTRect):
                RectDic = {}
                RectDic["x0"] = lt.x0
                RectDic["x1"] = lt.x1
                RectDic["y0"] = lt.y0
                RectDic["y1"] = lt.y1
                RectData.append(RectDic)
            #end if
        #next

        # その際、CharData2をY座標の高さ順に並び替えるためのリスト「CY」を作成
        CharData2=[]
        CY = []
        for cdata in CharData:
            char2 = cdata[0]
            x0 = cdata[1]
            x1 = cdata[2]
            y0 = cdata[3]
            y1 = cdata[4]
            
            CharData2.append(cdata)
            CY.append(int(y0))
        #next
        
        # リスト「CY」から降順の並び替えインデックッスを取得
        y=np.argsort(np.array(CY))[::-1]

        if len(CharData2) > 0:  # リストが空でない場合に処理を行う
            CharData3 = []
            # インデックスを用いて並べ替えた「CharData3」を作成
            for i in range(len(y)):
                CharData3.append(CharData2[y[i]])
            #next

            # 同じ高さのY座標毎にデータをまとめる２次元のリストを作成
            CharData4 = []
            i = 0
            dy = 0
            for f in CharData3:
                if i==0 :   # 最初の文字のY座標を基準値に採用し、仮のリストを初期化
                    Fline = []
                    Fline.append(f)
                    gy = int(f[3])
                else:
                    if int(f[3])>= gy-dy and int(f[3])<= gy+dy:   # 同じY座標の場合は、リストに文字を追加
                        Fline.append(f)
                    else:           # Y座標が異なる場合は、リストを「CharData4」を保存し、仮のリストを初期化
                        if len(Fline) >= 2:
                            CharData4.append(Fline)
                        gy = int(f[3])
                        Fline = []
                        Fline.append(f)
                    #end if
                #end if
                i += 1
            #next
            # 仮のリストが残っている場合は、リストを「CharData4」を保存
            if len(Fline) >= 4:
                CharData4.append(Fline)
            #end if

            # 次にX座標の順番にデータを並び替える（昇順）
            t1 = []
            CharData5 = []
            for F1 in CharData4:    # Y座標が同じデータを抜き出す。                        
                CX = []         # 各データのX座標のデータリストを作成
                for F2 in F1:
                    CX.append(F2[1])
                #next
                
                # リスト「CX」から降順の並び替えインデックッスを取得
                x=np.argsort(np.array(CX))
                
                # インデックスを用いて並べ替えた「F3」を作成
                F3 = []
                t2 = ""
                for i in range(len(x)):
                    F3.append(F1[x[i]])
                    t3 = F1[x[i]][0]
                    t2 += t3
                    # if t3 != " ":
                    #     t2 += t3
                    #end if
                #next
                # t1 += t2 + "\n"
                t1.append(t2)
                # print(t2,len(F3))
                CharData5.append(F3)
            #next
        #end if

        CharData2 = []
        for lt in layout:
            if isinstance(lt, LTChar):  # レイアウトデータうち、LTCharのみを取得
                char1 = lt.get_text()   # レイアウトデータに含まれる全文字を取得
                if lt.matrix[1] > 0.0 : # 正の回転している文字のみを抽出
                    CharData2.append([char1, lt.x0, lt.x1, lt.y0, lt.y1,lt.matrix])
                #end if
            #end if
        #nexr
        for lt in layout:
            if isinstance(lt, LTChar):  # レイアウトデータうち、LTCharのみを取得
                char1 = lt.get_text()   # レイアウトデータに含まれる全文字を取得
                if lt.matrix[1] < 0.0 : # 正の回転している文字のみを抽出
                    CharData2.append([char1, lt.x0, lt.x1, lt.y0, lt.y1,lt.matrix])
                #end if
            #end iuf
        #next
        
        fline = []
        Sflag = False
        tt2 = ""
        
        fline = []
        Sflag = False
        tt2 = ""
        for F1 in CharData2:
            if not Sflag:
                if F1[0] != " ":
                    fline.append(F1)
                    tt2 += F1[0]
                    Sflag = True
                #end if
            else:
                if F1[0] == " ":
                    CharData5.append(fline)
                    t1.append(tt2)
                    fline = []
                    tt2 = ""
                    Sflag = False
                else:
                    fline.append(F1)
                    tt2 += F1[0]
                #end if
            #end if
        #next

        if len(fline)>0:
            tt2=tt2.replace(" ","").replace("　","")
            CharData5.append(fline)
            t1.append(tt2)
        #end if

        return t1 , CharData5, LineData
    #end def
    #*********************************************************************************

    def makePattern(self):
        self.patternDic = {}
        # self.patternDic["符号名"]=['\S*\d+G\d+','B\d+','\S*RG\d+','\S*FG\d+','\d+C\d+','\d+P\d+']
        self.patternDic["符号名"]=['\S*\d{1,2}G\d{1,2}','\S*RG\d{1,2}','\S*FG\d{1,2}','\d{1,2}C\d{1,2}','\d{1,2}P\d{1,2}']
        # self.patternDic["断面寸法"]=['\d+\S?\d+','\d+×\d+']
        self.patternDic["断面寸法"]=['\d+×\d+']
        self.patternDic["コンクリート"]=['\(Fc\d+\)']
        # self.patternDic["配筋"]=['\d+/\d+-D\d+','\d+-D\d+','\d+/\d+/\d+-D\d+']
        self.patternDic["あばら筋"]=['\d{1}-\w+\d{2}@\d+']
        # self.patternDic["配筋"]=['\d{1}/\d{1}-D\d{2}','\d{1}-D\d{2}','\d{1}/\d{1}/\d{1}-D\d{2}']
        self.patternDic["配筋"]=['\d{1,2}/\d{1,2}-D\d{2}','\d{1,2}-D\d{2}','\d{1,2}/\d{1,2}/\d{1,2}-D\d{2}']
        self.patternDic["かぶり"]=['\d+\.\d+/\d+\.\d+','\d+/\d+\.\d+','\d+/\d+','\d{2}']
        self.patternDic["材料"]=['SD\d+\w*','SPR\d+\w*']
        self.patternDic["層"]=['\d+FL\Z','RFL\Z']
        self.patternDic["X通"]=['X\d+\Z']
        self.patternDic["Y通"]=['Y\d+\Z']
        
        self.PatternKeys = list(self.patternDic.keys())
    #end def

if __name__ == '__main__':
    
    # pdfname = "構造計算書の部材表.pdf"
    # pdfname = "01(2)Ⅲ構造計算書(2)一貫計算編電算出力.pdf"
    # pdfname = "03sawarabi 京都六角 計算書 (事前用).pdf"
    pdfname = "03構造計算書（部材リストのみ）.pdf"
    
    # pdfname = "02一貫計算書（一部）.pdf"
    ElementData = Read_Elements_from_pdf(pdfname)
    filename = os.path.splitext(pdfname)[0] + "_部材リスト" + ".csv"

    with open(filename, 'w') as f:
        writer = csv.writer(f)

        ElementKind = ElementData.keys()
        for Kind in ElementKind:
            Kind2 = []
            Kind2.append(Kind)  # 部材の種類
            writer.writerow(Kind2)

            Elements = ElementData[Kind]    # 同じ部材種類のデータ
            RowNames = list(Elements.keys())        # 符号名：断面位置
            Edata = Elements[RowNames[0]]
            ColumnNames =list(Edata.keys())
            cnames =["符号名：断面"] + ColumnNames
            writer.writerow(cnames)

            for RowName in RowNames:
                data = Elements[RowName]
                dlist = list(data.keys())
                cdata = [RowName]
                for ColumnName in ColumnNames:
                    if ColumnName in dlist:
                        cdata.append(data[ColumnName])
                    else:
                        cdata.append("")
                    #end if
                #next
                writer.writerow(cdata)
            #next
        #next
    #end with
    a=0
            


    # with open('data/temp/sample_writer_row.csv', 'a') as f:
        
    #     writer.writerow(['X', 'Y', 'Z'])
