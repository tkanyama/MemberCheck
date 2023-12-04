# pip install tabula-py
# pip install jpype1

import pandas as pd
import tabula


# lattice=Trueでテーブルの軸線でセルを判定
dfs = tabula.read_pdf("構造計算図書の部材表.pdf", lattice=False, pages = '26')

for df in dfs:
    print(df)

# csv/Excelとして保存(今回はdfs[0]のみ)
df = dfs[0] #.rename(columns={'高ストレ\rス者数': '高ストレス者数', '高ストレス\r者の割合': '高ストレス者の割合'})
df.to_csv("PDFの表1.csv", index=None) # csv
df.to_excel("PDFの表1.xlsx", index=None) # Excel

dfs2 = tabula.read_pdf("01(仮称)阿倍野区三明町2丁目マンション新築工事_構造図.pdf", lattice=False, pages = '27')
df2 = dfs2[0] #.rename(columns={'高ストレ\rス者数': '高ストレス者数', '高ストレス\r者の割合': '高ストレス者の割合'})
df2.to_csv("PDFの表2.csv", index=None) # csv
df2.to_excel("PDFの表2.xlsx", index=None) # Excel